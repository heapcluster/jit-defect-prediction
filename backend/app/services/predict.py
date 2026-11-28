"""模型预测：数据 / 模型加载、批量推理、结果与详情。"""

from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy import select

from app import config
from app.constants import (
    ALGO_BY_NAME,
    EXPERT_FEATURES,
    FEATURE_VERSION,
    PREDICTION_EXTRA_COLUMNS,
    PREDICTION_VIEW_COLUMNS,
    PREDICT_ELIGIBLE_SOURCES,
    SEMANTIC_FEATURES,
)
from app.errors import AppError
from app.models import Dataset, Model, ModelArtifact, Prediction, User
from app.services import artifacts, datasets, uploads
from app.services.jobs import JobContext
from app.services.validation import expected_columns, parse_time
from app.utils import iso, loads, new_id, now
from data_model import gitops, ml


def _features(line: str) -> list[str]:
    return EXPERT_FEATURES if line == "expert" else SEMANTIC_FEATURES


def _repo_available(dataset: Dataset) -> bool:
    if not dataset.repo_url:
        return False
    try:
        info = gitops.parse_repo_url(dataset.repo_url)
    except ValueError:
        return False
    return gitops.cache_dir(info).exists()


def precheck(user: User, dataset_id: str, db) -> dict:
    dataset = datasets.owned(db, user, dataset_id)
    if dataset.source_type == "prediction":
        raise AppError(40001, "预测结果数据集不能作为待预测数据")
    if dataset.source_type not in PREDICT_ELIGIBLE_SOURCES:
        raise AppError(40001, "该数据集来源不可用于预测")
    page = datasets.member_page(db, dataset, 1, max(dataset.sample_count, 1))
    rows = page["items"]
    if not rows:
        raise AppError(42201, "数据集为空")
    line = dataset.line or "expert"
    features = _features(line)
    if any(any(name not in row for name in features) for row in rows):
        raise AppError(42201, "数据集缺少特征列")
    has_label = all("bug" in row for row in rows)
    pos = sum(1 for row in rows if str(row.get("bug")) == "1") if has_label else None
    neg = sum(1 for row in rows if str(row.get("bug")) == "0") if has_label else None
    return {
        "line": line,
        "has_label": has_label,
        "sample_count": len(rows),
        "pos": pos,
        "neg": neg,
        "repo_available": _repo_available(dataset),
    }


def _load_source(user: User, source: dict, db) -> dict:
    kind = source.get("kind")
    if kind == "dataset":
        dataset = datasets.owned(db, user, source.get("id", ""))
        if dataset.source_type == "prediction":
            raise AppError(40001, "预测结果数据集不能作为待预测数据")
        page = datasets.member_page(db, dataset, 1, max(dataset.sample_count, 1))
        columns = artifacts.read_json(artifacts.resolve(dataset.manifest_path))["columns"] if dataset.manifest_path else expected_columns(dataset.line)
        has_bug = "bug" in columns
        return {
            "columns": columns,
            "rows": page["items"],
            "line": dataset.line,
            "has_label": has_bug,
            "parent_dataset_id": dataset.dataset_id,
            "feature_version": dataset.feature_version or FEATURE_VERSION.get(dataset.line),
            "repo": {
                "repo_url": dataset.repo_url, "repo_name": dataset.repo_name, "platform": dataset.platform,
                "branch": dataset.branch, "head_hash": dataset.head_hash,
            },
        }
    if kind == "file":
        meta, path = uploads.read_import(user.user_id, source.get("id", ""))
        if meta.get("role") != "data":
            raise AppError(40401, "导入文件不存在")
        columns, rows = artifacts.read_table(path)
        return {
            "columns": columns, "rows": rows, "line": meta.get("line") or "expert",
            "has_label": "bug" in columns, "parent_dataset_id": None,
            "feature_version": FEATURE_VERSION.get(meta.get("line") or "expert"), "repo": {},
        }
    raise AppError(40001, "数据源类型非法")


def _feature_count(model) -> int | None:
    if isinstance(model, ml.TorchModel):
        return model.input_dim
    return getattr(model, "n_features_in_", None)


def load_saved_model(db, user: User, model_name: str):
    model = db.get(Model, model_name)
    if model is None or model.owner_user_id != user.user_id:
        raise AppError(40401, "模型不存在")
    artifact = db.scalar(select(ModelArtifact).where(ModelArtifact.model_name == model_name))
    if artifact is None:
        raise AppError(40901, "模型文件缺失")
    if artifact.status != "available":
        raise AppError(40901, "模型文件缺失")
    path = artifacts.resolve(artifact.weight_path)
    if not path.is_file():
        artifact.status = "missing"
        db.commit()
        raise AppError(40901, "模型文件缺失")
    try:
        loaded = ml.load_model(path)
    except Exception as exc:  # noqa: BLE001
        raise AppError(50301, f"模型加载失败：{exc}") from exc
    return loaded, model, artifact


def _load_uploaded_model(user: User, model_ref: str, line: str, db):
    meta, path = uploads.read_model_import(user.user_id, model_ref)
    try:
        loaded = ml.load_model(path)
    except Exception as exc:  # noqa: BLE001
        raise AppError(42201, f"无法加载模型：{exc}") from exc
    if isinstance(loaded, ml.TorchModel):
        if loaded.line and loaded.line != line:
            raise AppError(40001, "模型文件声明的模型线与请求不一致")
        feature_version = loaded.feature_version
        algo = loaded.algo
        framework, fmt = "pytorch", "pt"
    else:
        feature_version = None
        algo = None
        framework, fmt = "sklearn", "pkl"
    return loaded, feature_version, algo, framework, fmt


def _validate_model_line(model, line: str) -> None:
    if isinstance(model, ml.TorchModel) and model.line and model.line != line:
        raise AppError(40001, "模型线与数据线不一致")


def preflight(db, user: User, params: dict) -> int:
    """启动前同步校验，返回待预测行数。"""
    source = _load_source(user, params.get("source") or {}, db)
    model_spec = params.get("model") or {}
    if model_spec.get("kind") == "saved":
        loaded, model_row, _ = load_saved_model(db, user, model_spec.get("name", ""))
        model_line = model_row.line
    elif model_spec.get("kind") == "uploaded":
        line = model_spec.get("line") or source["line"]
        loaded, _, _, _, _ = _load_uploaded_model(user, model_spec.get("model_ref", ""), line, db)
        model_line = line
    else:
        raise AppError(40001, "模型类型非法")
    if model_line and model_line != source["line"]:
        raise AppError(40001, "模型线与数据线不一致")
    expected_count = _feature_count(loaded)
    if expected_count is not None and expected_count != len(_features(source["line"])):
        raise AppError(42201, "模型特征数与数据列数不符")
    try:
        threshold = float(params.get("threshold", 0.5))
    except (TypeError, ValueError):
        raise AppError(40001, "阈值非法")
    if not 0 <= threshold <= 1:
        raise AppError(40001, "阈值必须位于 0–1")
    if not source["rows"]:
        raise AppError(40901, "待预测数据为空")
    return len(source["rows"])


def run_predict(ctx: JobContext) -> None:
    from app.db import SessionLocal

    params = ctx.params
    with SessionLocal() as session:
        user = session.get(User, ctx.user_id)
        source = _load_source(user, params.get("source") or {}, session)
        model_spec = params.get("model") or {}
        if model_spec.get("kind") == "saved":
            loaded, model_row, artifact = load_saved_model(session, user, model_spec.get("name", ""))
            model_name = model_row.model_name
            model_label = model_row.model_name
            feature_version = model_row.feature_version or source["feature_version"]
            model_line = model_row.line
        elif model_spec.get("kind") == "uploaded":
            line = model_spec.get("line") or source["line"]
            loaded, feature_version, algo, framework, fmt = _load_uploaded_model(user, model_spec.get("model_ref", ""), line, session)
            model_name = None
            model_label = model_spec.get("label") or model_spec.get("name") or "imported-model"
            model_line = line
        else:
            raise AppError(40001, "模型类型非法")
    line = source["line"]
    if model_line and model_line != line:
        raise AppError(40001, "模型线与数据线不一致")
    expected_count = _feature_count(loaded)
    features = _features(line)
    if expected_count is not None and expected_count != len(features):
        raise AppError(42201, "模型特征数与数据列数不符")
    try:
        threshold = float(params.get("threshold", 0.5))
    except (TypeError, ValueError):
        raise AppError(40001, "阈值非法")
    if not 0 <= threshold <= 1:
        raise AppError(40001, "阈值必须位于 0–1")
    rows = source["rows"]
    if not rows:
        raise AppError(40901, "待预测数据为空")
    ctx.set_total(len(rows))
    ctx.update(force=True)
    X = np.array([[float(row.get(name, 0) or 0) for name in features] for row in rows], dtype=float)
    try:
        scores = ml.predict_scores(loaded, X)
    except Exception as exc:  # noqa: BLE001
        raise AppError(50301, f"模型推理失败：{exc}") from exc
    output_rows = []
    columns = list(source["columns"]) + PREDICTION_EXTRA_COLUMNS
    step = max(1, len(rows) // 10)
    for index, row in enumerate(rows):
        score = float(scores[index])
        item = {name: row.get(name, "") for name in source["columns"]}
        item["risk_score"] = round(score, 5)
        item["predicted_label"] = 1 if score >= threshold else 0
        item["threshold"] = round(threshold, 3)
        output_rows.append(item)
        if (index + 1) % step == 0:
            ctx.set_done(index + 1)
    ctx.set_done(len(rows))
    out_dir = artifacts.output_dir(ctx.user_id, ctx.job_id)
    rows_path = out_dir / "predictions.csv"
    artifacts.write_csv(rows_path, columns, output_rows)
    manifest = {
        "job_id": ctx.job_id, "kind": "predict", "user_id": ctx.user_id,
        "created_at": iso(datetime.now()), "line": line, "columns": columns,
        "row_count": len(output_rows),
        "files": [{"name": "predictions.csv", "size": rows_path.stat().st_size, "sha256": artifacts.file_sha256(rows_path)}],
        "repo": source["repo"],
    }
    artifacts.write_manifest(out_dir / "manifest.json", manifest)
    pos = sum(1 for row in output_rows if row["predicted_label"] == 1)
    ctx.set_output({
        "rows_path": artifacts.rel(rows_path),
        "manifest_path": artifacts.rel(out_dir / "manifest.json"),
        "columns": columns,
        "original_columns": source["columns"],
        "has_label": source["has_label"],
        "row_count": len(output_rows),
        "line": line,
        "threshold": threshold,
        "model_name": model_name,
        "model_label": model_label,
        "feature_version": feature_version or source["feature_version"],
        "parent_dataset_id": source["parent_dataset_id"],
        "repo": source["repo"],
        "summary": {"total": len(output_rows), "pos": pos, "neg": len(output_rows) - pos},
        "manifest": manifest,
    })


def _find_saved_dataset(db, user: User, job_id: str) -> Dataset | None:    return db.scalar(
        select(Dataset).where(
            Dataset.owner_user_id == user.user_id,
            Dataset.job_id == job_id,
            Dataset.source_type == "prediction",
        )
    )


def resolve_rows(db, user: User, job_id: str) -> tuple[list[str], list[dict], dict]:
    from app.models import Job

    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    ref = loads(job.output_ref_json, {}) or {}
    if job.kind != "predict":
        raise AppError(40001, "任务类型不是预测")
    if ref.get("rows_path"):
        try:
            columns, rows = artifacts.read_table(artifacts.resolve(ref["rows_path"]))
            return columns, rows, ref
        except (FileNotFoundError, ValueError):
            pass
    dataset = _find_saved_dataset(db, user, job_id)
    if dataset is None:
        raise AppError(40901, "预测结果已失效")
    columns, rows = datasets.export_rows(db, dataset)
    ref = dict(ref)
    ref.setdefault("line", dataset.line)
    if "has_label" not in ref:
        ref["has_label"] = any(str(row.get("bug", "")) in ("0", "1") for row in rows)
    ref.setdefault("model_label", None)
    ref.setdefault("model_name", None)
    ref.setdefault("threshold", 0.5)
    ref.setdefault("repo", {"repo_url": dataset.repo_url, "repo_name": dataset.repo_name})
    ref["_dataset"] = dataset
    return columns, rows, ref


def public_row(row: dict) -> dict:
    return {
        "commit_hash": row.get("commit_id") or row.get("commit_hash") or "",
        "commit_message": row.get("commit_message") or "",
        "author_name": row.get("author_name") or "",
        "commit_time": row.get("commit_time") or None,
        "bug": int(row["bug"]) if str(row.get("bug", "")) in ("0", "1") else None,
        "risk_score": float(row.get("risk_score", 0) or 0),
        "predicted_label": int(float(row.get("predicted_label", 0) or 0)),
    }


def detail(db, user: User, job_id: str, commit_hash: str) -> dict:
    columns, rows, ref = resolve_rows(db, user, job_id)
    target = None
    for row in rows:
        if str(row.get("commit_id") or row.get("commit_hash") or "").lower() == commit_hash.lower():
            target = row
            break
    if target is None:
        raise AppError(40401, "提交不存在")
    repo = ref.get("repo") or {}
    repo_available = False
    if repo.get("repo_url"):
        try:
            info = gitops.parse_repo_url(repo["repo_url"])
            repo_available = gitops.cache_dir(info).exists()
        except ValueError:
            repo_available = False
    model_label = ref.get("model_label") or ref.get("model_name")
    if not model_label and ref.get("_dataset") is not None:
        row = db.scalar(
            select(Prediction).where(
                Prediction.dataset_id == ref["_dataset"].dataset_id,
                Prediction.commit_hash == commit_hash.lower(),
            )
        )
        if row is not None:
            model_label = row.model_label or row.model_name
    return {
        "commit_hash": (target.get("commit_id") or target.get("commit_hash") or "").lower(),
        "commit_message": target.get("commit_message") or "",
        "author_name": target.get("author_name") or "",
        "commit_time": target.get("commit_time") or None,
        "line": ref.get("line") or "expert",
        "model": model_label,
        "threshold": float(target.get("threshold", ref.get("threshold", 0.5)) or 0.5),
        "risk_score": float(target.get("risk_score", 0) or 0),
        "predicted_label": int(float(target.get("predicted_label", 0) or 0)),
        "actual_label": int(target["bug"]) if str(target.get("bug", "")) in ("0", "1") else None,
        "repo_available": repo_available,
    }


def feature_row(db, user: User, job_id: str, commit_hash: str, line: str) -> dict:
    columns, rows, ref = resolve_rows(db, user, job_id)
    for row in rows:
        if str(row.get("commit_id") or row.get("commit_hash") or "").lower() == commit_hash.lower():
            return row
    raise AppError(40401, "提交不存在")


def save_model(db, user: User, model_ref: str, name: str | None) -> str:
    meta, path = uploads.read_model_import(user.user_id, model_ref)
    try:
        loaded = ml.load_model(path)
    except Exception as exc:  # noqa: BLE001
        raise AppError(42201, f"无法加载模型：{exc}") from exc
    if isinstance(loaded, ml.TorchModel):
        line = loaded.line or "expert"
        algo = loaded.algo
        feature_version = loaded.feature_version
        framework, fmt = "pytorch", "pt"
    else:
        line = meta.get("line") or "expert"
        algo = None
        feature_version = FEATURE_VERSION.get(line)
        framework, fmt = "sklearn", "pkl"
    label = name or Path(meta.get("original_name") or "model").stem
    normalized = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5_-]+", "-", label).strip("-")[:40] or "model"
    model_name = f"{line}-{normalized}-{model_ref[-8:]}"
    existing = db.get(Model, model_name)
    if existing is not None:
        if existing.owner_user_id != user.user_id:
            raise AppError(40901, "模型名称冲突")
        return model_name
    target_dir = artifacts.model_dir(user.user_id, model_name)
    target = target_dir / f"{model_name}.{fmt}"
    artifacts.copy_asset(path, target)
    model = Model(
        model_name=model_name, owner_user_id=user.user_id, line=line, algo=algo,
        version_key=model_ref, trained_at=None, feature_version=feature_version,
        train_dataset_id=None, test_dataset_id=None, params_json=None, metrics_json=None,
    )
    artifact = ModelArtifact(
        artifact_id=new_id("artifact"), model_name=model_name, line=line, algo=algo,
        framework=framework, format=fmt, version_key=model_ref,
        weight_path=artifacts.rel(target), checksum_sha256=artifacts.file_sha256(target),
        size_bytes=target.stat().st_size, feature_version=feature_version,
        train_job_id=None, status="available", trained_at=None, created_at=now(),
    )
    db.add(model)
    db.add(artifact)
    db.commit()
    return model_name
