"""数据清洗：五项确定性操作与逐步统计。"""

from __future__ import annotations

from datetime import datetime

from app.constants import (
    CLEAN_DEFAULTS,
    CLEAN_ELIGIBLE_SOURCES,
    CLEAN_OPS,
    EXPERT_FEATURES,
    FEATURE_VERSION,
    META_COLUMNS,
    SEMANTIC_FEATURES,
)
from app.errors import AppError
from app.models import Dataset, User
from app.services import artifacts, datasets, uploads
from app.services.jobs import JobContext
from app.services.validation import expected_columns
from app.utils import iso

NUMERIC_FEATURES = {
    "expert": EXPERT_FEATURES,
    "semantic": SEMANTIC_FEATURES,
}


def _allowed_clean_columns(line: str) -> list[str]:
    if line == "expert":
        return META_COLUMNS + EXPERT_FEATURES + ["bug"]
    return META_COLUMNS + ["bug"]


def _stats(rows: list[dict]) -> dict:
    pos = sum(1 for row in rows if str(row.get("bug")) == "1")
    return {"pos": pos, "neg": len(rows) - pos}


def _normalize_operations(operations: list[dict], line: str) -> list[dict]:
    if not operations:
        raise AppError(40001, "至少选择一个清洗操作")
    result = []
    allowed = set(_allowed_clean_columns(line))
    for item in operations:
        op = item.get("op")
        if op not in CLEAN_OPS:
            raise AppError(40001, f"未知清洗操作：{op}")
        params = dict(CLEAN_DEFAULTS[op])
        incoming = item.get("params") or {}
        unknown = set(incoming) - set(params)
        if unknown:
            raise AppError(40001, f"未知清洗参数：{sorted(unknown)[0]}")
        params.update(incoming)
        if op in ("missing", "outlier"):
            columns = params.get("columns") or []
            if not isinstance(columns, list):
                raise AppError(40001, "columns 必须是数组")
            for column in columns:
                if column not in allowed:
                    raise AppError(40001, f"目标列不可清洗：{column}")
            if line == "semantic" and any(col in SEMANTIC_FEATURES for col in columns):
                raise AppError(40001, "语义线向量列不可作为清洗目标")
        if op == "balance" and params.get("method") != "under":
            raise AppError(40001, "样本平衡只支持欠采样")
        if op == "dedup" and params.get("key") not in ("full", "commit_hash"):
            raise AppError(40001, "去重键非法")
        if op == "missing" and params.get("mode") not in ("drop", "mean", "mode"):
            raise AppError(40001, "缺失值方式非法")
        if op == "outlier" and params.get("method") not in ("iqr_clip", "iqr_drop"):
            raise AppError(40001, "异常值方式非法")
        result.append({"op": op, "params": params})
    return result


def _dedup(rows: list[dict], params: dict) -> list[dict]:
    seen = set()
    kept = []
    key = params.get("key", "full")
    for row in rows:
        token = tuple(row.items()) if key == "full" else str(row.get("commit_id", ""))
        if token in seen:
            continue
        seen.add(token)
        kept.append(row)
    return kept


def _to_float(value) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _missing(rows: list[dict], params: dict, line: str) -> list[dict]:
    columns = params.get("columns") or _allowed_clean_columns(line)
    mode = params.get("mode", "drop")
    if mode == "drop":
        return [row for row in rows if all(str(row.get(col, "")).strip() != "" for col in columns)]
    for column in columns:
        values = [row.get(column) for row in rows if str(row.get(column, "")).strip() != ""]
        if mode == "mean":
            numbers = [_to_float(value) for value in values]
            if any(number is None for number in numbers):
                raise AppError(40001, f"均值填充要求数值列：{column}")
            fill = sum(numbers) / len(numbers) if numbers else 0.0
            for row in rows:
                if str(row.get(column, "")).strip() == "":
                    row[column] = round(fill, 6)
        elif mode == "mode":
            if not values:
                continue
            fill = max(set(map(str, values)), key=lambda item: sum(1 for v in values if str(v) == item))
            for row in rows:
                if str(row.get(column, "")).strip() == "":
                    row[column] = fill
    return rows


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    pos = (len(sorted_values) - 1) * q
    low = int(pos)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (pos - low)


def _outlier(rows: list[dict], params: dict, line: str) -> list[dict]:
    if line == "semantic":
        return rows
    columns = params.get("columns") or EXPERT_FEATURES
    columns = [col for col in columns if col in NUMERIC_FEATURES["expert"]]
    method = params.get("method", "iqr_clip")
    factor = float(params.get("factor", 1.5))
    bounds = {}
    for column in columns:
        values = sorted(float(row[column]) for row in rows if _to_float(row.get(column)) is not None)
        if not values:
            continue
        q1, q3 = _quantile(values, 0.25), _quantile(values, 0.75)
        iqr = q3 - q1
        bounds[column] = (q1 - factor * iqr, q3 + factor * iqr)
    if method == "iqr_clip":
        for row in rows:
            for column, (low, high) in bounds.items():
                value = _to_float(row.get(column))
                if value is not None:
                    row[column] = round(min(max(value, low), high), 6)
        return rows
    return [
        row for row in rows
        if all(
            _to_float(row.get(column)) is None or low <= _to_float(row.get(column)) <= high
            for column, (low, high) in bounds.items()
        )
    ]


def _label(rows: list[dict]) -> list[dict]:
    return [row for row in rows if str(row.get("bug")) in ("0", "1")]


def _balance(rows: list[dict], params: dict) -> list[dict]:
    ratio = float(params.get("ratio", 1.0))
    if ratio < 1:
        raise AppError(40001, "欠采样比例必须 ≥ 1")
    positives = [row for row in rows if str(row.get("bug")) == "1"]
    negatives = [row for row in rows if str(row.get("bug")) == "0"]
    if not positives or not negatives:
        return rows
    minority, majority = (positives, negatives) if len(positives) <= len(negatives) else (negatives, positives)
    keep = int(len(minority) * ratio)
    if keep >= len(majority):
        return rows
    kept_majority = majority[:keep]
    keep_ids = {id(row) for row in minority} | {id(row) for row in kept_majority}
    return [row for row in rows if id(row) in keep_ids]


def _apply(rows: list[dict], op: dict, line: str) -> list[dict]:
    name = op["op"]
    params = op["params"]
    if name == "dedup":
        return _dedup(rows, params)
    if name == "missing":
        return _missing(rows, params, line)
    if name == "outlier":
        return _outlier(rows, params, line)
    if name == "label":
        return _label(rows)
    if name == "balance":
        return _balance(rows, params)
    return rows


def load_source(user: User, source: dict, db) -> dict:
    kind = source.get("kind")
    if kind == "dataset":
        dataset = datasets.owned(db, user, source.get("id", ""))
        if dataset.source_type not in CLEAN_ELIGIBLE_SOURCES:
            raise AppError(40001, "该数据集来源不可作为清洗输入")
        page = datasets.member_page(db, dataset, 1, max(dataset.sample_count, 1))
        columns = artifacts.read_json(artifacts.resolve(dataset.manifest_path))["columns"] if dataset.manifest_path else expected_columns(dataset.line)
        return {
            "columns": columns,
            "rows": page["items"],
            "line": dataset.line,
            "parent_dataset_id": dataset.dataset_id,
            "feature_version": dataset.feature_version or FEATURE_VERSION.get(dataset.line),
            "repo": {
                "repo_url": dataset.repo_url,
                "repo_name": dataset.repo_name,
                "platform": dataset.platform,
                "branch": dataset.branch,
                "head_hash": dataset.head_hash,
            },
            "file_sha256": None,
        }
    if kind == "file":
        meta, path = uploads.read_import(user.user_id, source.get("id", ""))
        if meta.get("role") != "data":
            raise AppError(40401, "导入文件不存在")
        columns, rows = artifacts.read_table(path)
        return {
            "columns": columns,
            "rows": rows,
            "line": meta.get("line") or "expert",
            "parent_dataset_id": None,
            "feature_version": FEATURE_VERSION.get(meta.get("line") or "expert"),
            "repo": {},
            "file_sha256": meta.get("sha256"),
        }
    raise AppError(40001, "数据源类型非法")


def run_clean(ctx: JobContext) -> None:
    from app.db import SessionLocal

    params = ctx.params
    with SessionLocal() as session:
        user = session.get(User, ctx.user_id)
        source = load_source(user, params.get("source") or {}, session)
    operations = _normalize_operations(params.get("operations") or [], source["line"])
    ctx.set_total(len(operations))
    ctx.update(force=True)
    rows = source["rows"]
    steps = []
    for item in operations:
        ctx.check()
        ctx.set_stage(f"{item['op']}")
        before = len(rows)
        rows = _apply(rows, item, source["line"])
        after = len(rows)
        steps.append({
            "op": item["op"],
            "before": before,
            "after": after,
            "changed": before - after,
            "stats": _stats(rows),
        })
        ctx.advance(1)
    if not rows:
        raise AppError(40901, "清洗结果为空")
    line = source["line"]
    columns = source["columns"]
    out_dir = artifacts.output_dir(ctx.user_id, ctx.job_id)
    data_path = out_dir / "data.csv"
    artifacts.write_csv(data_path, columns, rows)
    manifest = {
        "job_id": ctx.job_id,
        "kind": "clean",
        "user_id": ctx.user_id,
        "created_at": iso(datetime.now()),
        "line": line,
        "columns": columns,
        "row_count": len(rows),
        "files": [{"name": "data.csv", "size": data_path.stat().st_size, "sha256": artifacts.file_sha256(data_path)}],
        "repo": source["repo"],
    }
    artifacts.write_manifest(out_dir / "manifest.json", manifest)
    artifacts.write_json(out_dir / "steps.json", {"steps": steps})
    stats = _stats(rows)
    ctx.set_output({
        "data_path": artifacts.rel(data_path),
        "manifest_path": artifacts.rel(out_dir / "manifest.json"),
        "columns": columns,
        "row_count": len(rows),
        "line": line,
        "feature_version": source["feature_version"],
        "source_type": "clean" if source["parent_dataset_id"] else "upload",
        "parent_dataset_id": source["parent_dataset_id"],
        "file_sha256": source["file_sha256"],
        "ops_hash": artifacts.ops_hash(operations),
        "summary": {"total": len(rows), "pos": stats["pos"], "neg": stats["neg"]},
        "repo": source["repo"],
        "manifest": manifest,
    })
