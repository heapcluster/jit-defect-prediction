"""模型训练：三段切分、逐算法训练、指标与测试集产物。"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np

from app.constants import (
    ALGO_BY_NAME,
    ALGORITHMS,
    EXPERT_FEATURES,
    FEATURE_VERSION,
    SEMANTIC_FEATURES,
    TRAIN_ELIGIBLE_SOURCES,
)
from app.errors import AppError
from app.models import Dataset, User
from app.services import artifacts, datasets, uploads
from app.services.jobs import JobContext
from app.services.validation import expected_columns, parse_time
from app.utils import iso
from data_model import ml


def _algo_list(line: str) -> list[dict]:
    return [
        {"algo": item["algo"], "family": item["family"], "defaults": item["defaults"]}
        for item in ALGORITHMS
    ]


def _load_rows(user: User, source: dict, db) -> dict:
    kind = source.get("kind")
    if kind == "dataset":
        dataset = datasets.owned(db, user, source.get("id", ""))
        if dataset.source_type not in TRAIN_ELIGIBLE_SOURCES:
            raise AppError(40001, "该数据集来源不可用于训练")
        page = datasets.member_page(db, dataset, 1, max(dataset.sample_count, 1))
        columns = artifacts.read_json(artifacts.resolve(dataset.manifest_path))["columns"] if dataset.manifest_path else expected_columns(dataset.line)
        rows = page["items"]
        # 上传 / 清洗数据集没有仓库名，project 只能从来源保留；成员表缺失时用数据集名兜底，
        # 否则保存测试集时会因为 project 为空而失败。
        fallback_project = dataset.repo_name or dataset.name
        for row in rows:
            if not row.get("project"):
                row["project"] = fallback_project
        return {
            "columns": columns,
            "rows": rows,
            "line": dataset.line,
            "parent_dataset_id": dataset.dataset_id,
            "feature_version": dataset.feature_version or FEATURE_VERSION.get(dataset.line),
            "repo": {
                "repo_url": dataset.repo_url, "repo_name": dataset.repo_name, "platform": dataset.platform,
                "branch": dataset.branch, "head_hash": dataset.head_hash,
            },
            "dataset_name": dataset.name,
        }
    if kind == "file":
        meta, path = uploads.read_import(user.user_id, source.get("id", ""))
        if meta.get("role") != "data":
            raise AppError(40401, "导入文件不存在")
        columns, rows = artifacts.read_table(path)
        return {
            "columns": columns, "rows": rows, "line": meta.get("line") or "expert",
            "parent_dataset_id": None, "feature_version": FEATURE_VERSION.get(meta.get("line") or "expert"),
            "repo": {}, "dataset_name": meta.get("original_name") or "upload",
        }
    raise AppError(40001, "数据源类型非法")


def precheck(user: User, dataset_id: str, db) -> dict:
    dataset = datasets.owned(db, user, dataset_id)
    if dataset.source_type not in TRAIN_ELIGIBLE_SOURCES:
        raise AppError(40001, "该数据集来源不可用于训练")
    page = datasets.member_page(db, dataset, 1, max(dataset.sample_count, 1))
    rows = page["items"]
    if not rows or any("bug" not in row for row in rows):
        raise AppError(42201, "数据集缺少 bug 列")
    line = dataset.line or "expert"
    features = EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES
    if any(any(name not in row for name in features) for row in rows):
        raise AppError(42201, "数据集特征列不完整")
    return {
        "line": line,
        "sample_count": len(rows),
        "pos": sum(1 for row in rows if str(row.get("bug")) == "1"),
        "neg": sum(1 for row in rows if str(row.get("bug")) == "0"),
        "time_start": iso(dataset.time_start),
        "time_end": iso(dataset.time_end),
        "suggested_ratios": {"train": 70, "valid": 15, "test": 15},
        "algorithms": _algo_list(line),
    }


def _validate_algorithms(items: list[dict]) -> list[dict]:
    if not items:
        raise AppError(40001, "至少选择一个算法")
    names = [item.get("algo") for item in items]
    if len(set(names)) != len(names):
        raise AppError(40001, "算法不能重复")
    result = []
    for item in items:
        algo = item.get("algo")
        spec = ALGO_BY_NAME.get(algo)
        if spec is None:
            raise AppError(40001, f"未知算法：{algo}")
        params = dict(spec["defaults"])
        incoming = item.get("params") or {}
        unknown = set(incoming) - set(spec["defaults"])
        if unknown:
            raise AppError(40001, f"未知算法参数：{sorted(unknown)[0]}")
        for key, value in incoming.items():
            kind = spec["types"].get(key)
            if kind == "int" and (not isinstance(value, int) or isinstance(value, bool)):
                raise AppError(40001, f"参数类型不符：{algo}.{key}")
            if kind == "number" and not isinstance(value, (int, float)):
                raise AppError(40001, f"参数类型不符：{algo}.{key}")
            if kind == "int_list" and not (isinstance(value, list) and all(isinstance(v, int) for v in value)):
                raise AppError(40001, f"参数类型不符：{algo}.{key}")
            if kind and kind.startswith("choice:") and str(value) not in kind.split(":", 1)[1].split(","):
                raise AppError(40001, f"参数取值非法：{algo}.{key}")
        params.update(incoming)
        result.append({"algo": algo, "params": params, "family": spec["family"]})
    return result


def validate_split(split: dict) -> tuple[str, float, float, float]:
    mode = split.get("mode", "time")
    ratios = split.get("ratios") or {}
    try:
        train_pct = float(ratios.get("train"))
        valid_pct = float(ratios.get("valid"))
        test_pct = float(ratios.get("test"))
    except (TypeError, ValueError):
        raise AppError(40001, "切分比例非法")
    if min(train_pct, valid_pct, test_pct) <= 0 or abs(train_pct + valid_pct + test_pct - 100) > 1e-6:
        raise AppError(40001, "三段比例必须为正且合计 100")
    if mode not in ("time", "random"):
        raise AppError(40001, "切分方式非法")
    return mode, train_pct, valid_pct, test_pct


def _split_indices(rows: list[dict], split: dict) -> tuple[list[int], list[int], list[int]]:
    mode, train_pct, valid_pct, _ = validate_split(split)
    n = len(rows)
    if mode == "time":
        order = sorted(range(n), key=lambda index: (
            parse_time(rows[index].get("commit_time")) or datetime.min,
            str(rows[index].get("commit_id", "")),
        ))
    else:
        order = list(np.random.RandomState(42).permutation(n))
    train_n = int(math.floor(n * train_pct / 100))
    valid_n = int(math.floor(n * valid_pct / 100))
    train_idx = order[:train_n]
    valid_idx = order[train_n : train_n + valid_n]
    test_idx = order[train_n + valid_n :]
    return train_idx, valid_idx, test_idx


def _matrix(rows: list[dict], indices: list[int], line: str) -> tuple[np.ndarray, np.ndarray]:
    features = EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES
    X = np.array([[float(row.get(name, 0) or 0) for name in features] for row in rows], dtype=float)
    y = np.array([int(str(row.get("bug", 0)) or 0) for row in rows], dtype=int)
    return X[indices], y[indices]


def run_train(ctx: JobContext) -> None:
    from app.db import SessionLocal

    params = ctx.params
    with SessionLocal() as session:
        user = session.get(User, ctx.user_id)
        source = _load_rows(user, params.get("source") or {}, session)
    rows = source["rows"]
    line = source["line"]
    algorithms = _validate_algorithms(params.get("algorithms") or [])
    train_idx, valid_idx, test_idx = _split_indices(rows, params.get("split") or {})
    for name, indices in (("训练", train_idx), ("验证", valid_idx), ("测试", test_idx)):
        labels = {str(rows[i].get("bug")) for i in indices}
        if labels != {"0", "1"}:
            raise AppError(42201, f"{name}段缺少正样本或负样本")
    X_train, y_train = _matrix(rows, train_idx, line)
    X_valid, y_valid = _matrix(rows, valid_idx, line)
    X_test, y_test = _matrix(rows, test_idx, line)

    ctx.set_total(len(algorithms))
    ctx.update(force=True)
    out_dir = artifacts.output_dir(ctx.user_id, ctx.job_id)
    models_dir = out_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    suffix = ctx.job_id[4:12]
    models, failed = [], []
    for item in algorithms:
        ctx.check()
        ctx.set_stage(item["algo"])
        model_name = f"{line}-{item['algo']}-{suffix}"
        try:
            model, framework, fmt, metrics = ml.train_model(
                item["algo"], item["params"], X_train, y_train, X_valid, y_valid,
                line=line, feature_version=source["feature_version"] or FEATURE_VERSION[line],
                features=EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES,
            )
            path = models_dir / f"{model_name}.{fmt}"
            ml.save_model(model, path, framework)
            models.append({
                "model_name": model_name,
                "algo": item["algo"],
                "status": "success",
                "params": item["params"],
                "metrics": metrics,
                "framework": framework,
                "format": fmt,
                "file": {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": artifacts.file_sha256(path),
                    "path": artifacts.rel(path),
                },
            })
        except Exception as exc:  # noqa: BLE001
            failed.append({"algo": item["algo"], "reason": str(exc)[:500]})
        ctx.advance(1)
    if not models:
        raise AppError(40901, "全部算法训练失败")

    columns = source["columns"]
    test_rows = [rows[index] for index in test_idx]
    test_path = out_dir / "test.csv"
    artifacts.write_csv(test_path, columns, test_rows)
    test_pos = sum(1 for row in test_rows if str(row.get("bug")) == "1")
    test_name = f"{source['dataset_name']}-test-{suffix}"
    manifest = {
        "job_id": ctx.job_id,
        "kind": "train",
        "user_id": ctx.user_id,
        "created_at": iso(datetime.now()),
        "line": line,
        "columns": columns,
        "row_count": len(rows),
        "files": [
            {"name": item["file"]["name"], "size": item["file"]["size_bytes"], "sha256": item["file"]["sha256"]}
            for item in models
        ] + [{"name": "test.csv", "size": test_path.stat().st_size, "sha256": artifacts.file_sha256(test_path)}],
        "repo": source["repo"],
    }
    artifacts.write_manifest(out_dir / "manifest.json", manifest)
    ctx.set_output({
        "line": line,
        "feature_version": source["feature_version"] or FEATURE_VERSION[line],
        "parent_dataset_id": source["parent_dataset_id"],
        "repo": source["repo"],
        "split_counts": {"train": len(train_idx), "valid": len(valid_idx), "test": len(test_idx)},
        "models": models,
        "failed": failed,
        "columns": columns,
        "test_set": {
            "name": test_name,
            "rows": len(test_rows),
            "pos": test_pos,
            "neg": len(test_rows) - test_pos,
            "file": "test.csv",
            "path": artifacts.rel(test_path),
            "columns": columns,
        },
        "manifest": manifest,
    })


def public_result(ref: dict) -> dict:
    models = []
    for item in ref.get("models") or []:
        models.append({
            "model_name": item["model_name"], "algo": item["algo"], "status": item["status"],
            "params": item.get("params") or {}, "metrics": item.get("metrics") or {},
            "framework": item.get("framework"), "format": item.get("format"),
            "file": {k: item["file"].get(k) for k in ("name", "size_bytes", "sha256")},
        })
    return {
        "line": ref.get("line"),
        "split_counts": ref.get("split_counts") or {},
        "models": models,
        "failed": ref.get("failed") or [],
        "test_set": {k: (ref.get("test_set") or {}).get(k) for k in ("name", "rows", "pos", "neg", "file")},
    }
