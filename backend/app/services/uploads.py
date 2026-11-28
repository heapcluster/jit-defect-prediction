"""上传临时区：校验、登记 import.json、按页面 / 角色清理。"""

from __future__ import annotations

import shutil
from pathlib import Path

from app import config
from app.errors import AppError
from app.services import artifacts, validation
from app.utils import iso, new_id, now, sha256_hex


def _ext(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in (".csv", ".xlsx"):
        raise AppError(40001, "仅支持 .csv / .xlsx")
    return suffix


def _iter_imports(user_id: str):
    root = config.UPLOADS_DIR / user_id
    if not root.exists():
        return
    for folder in root.iterdir():
        meta_path = folder / "import.json"
        if meta_path.is_file():
            yield folder, artifacts.read_json(meta_path)


def _cleanup_role(user_id: str, page: str, role: str) -> None:
    for folder, meta in list(_iter_imports(user_id)):
        if meta.get("page") == page and meta.get("role") == role:
            shutil.rmtree(folder, ignore_errors=True)


def cleanup_page(user_id: str, page: str) -> None:
    for folder, meta in list(_iter_imports(user_id)):
        if meta.get("page") == page:
            shutil.rmtree(folder, ignore_errors=True)


def read_import(user_id: str, file_id: str) -> tuple[dict, Path]:
    folder = config.UPLOADS_DIR / user_id / file_id
    meta_path = folder / "import.json"
    if not meta_path.is_file():
        raise AppError(40401, "导入文件不存在")
    meta = artifacts.read_json(meta_path)
    if meta.get("user_id") != user_id:
        raise AppError(40401, "导入文件不存在")
    path = folder / meta["stored_name"]
    if not path.is_file():
        raise AppError(40401, "导入文件不存在")
    return meta, path


def save_data_upload(
    user_id: str,
    filename: str,
    payload: bytes,
    page: str,
    allow_missing_bug: bool = False,
    require_unique: bool = True,
) -> dict:
    if not payload:
        raise AppError(40001, "文件为空")
    if len(payload) > config.MAX_DATA_UPLOAD_BYTES:
        raise AppError(41301, "文件超过 100MB 上限")
    suffix = _ext(filename)
    _cleanup_role(user_id, page, "data")
    file_id = f"file_{new_id('artifact')[4:]}"
    folder = artifacts.upload_dir(user_id, file_id)
    stored = folder / f"source{suffix}"
    stored.write_bytes(payload)
    try:
        columns, rows = artifacts.read_table(stored)
        line = validation.validate_table(columns, rows, allow_missing_bug=allow_missing_bug, require_unique=require_unique)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    meta = {
        "file_id": file_id,
        "user_id": user_id,
        "page": page,
        "role": "data",
        "original_name": filename,
        "stored_name": stored.name,
        "size": len(payload),
        "sha256": sha256_hex(payload),
        "line": line,
        "columns": columns,
        "row_count": len(rows),
        "created_at": iso(now()),
    }
    artifacts.write_json(folder / "import.json", meta)
    return {"meta": meta, "columns": columns, "rows": rows, "path": stored}


def save_prediction_upload(user_id: str, filename: str, payload: bytes, label: str | None = None) -> dict:
    if not payload:
        raise AppError(40001, "未选择文件")
    if len(payload) > config.MAX_DATA_UPLOAD_BYTES:
        raise AppError(41301, "文件超过 100MB 上限")
    suffix = _ext(filename)
    _cleanup_role(user_id, "evaluate", "data")
    file_id = f"file_{new_id('artifact')[4:]}"
    folder = artifacts.upload_dir(user_id, file_id)
    stored = folder / f"source{suffix}"
    stored.write_bytes(payload)
    try:
        columns, rows = artifacts.read_table(stored)
        expected_tail = ["risk_score", "predicted_label", "threshold"]
        if len(columns) < 4 or columns[-3:] != expected_tail:
            raise AppError(42201, "表头必须为原始列 + risk_score / predicted_label / threshold",
                           {"mismatch": {"column_index": max(len(columns) - 2, 1),
                                         "expected": "risk_score", "actual": columns[-3] if len(columns) >= 3 else None}})
        base_columns = columns[:-3]
        line = validation.detect_line(base_columns)
        validation.validate_rows(rows, line, require_bug=True, require_unique=True)
        thresholds = set()
        for row in rows:
            value = str(row.get("threshold", "")).strip()
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise AppError(42201, "threshold 必须为数值")
            if not 0 <= number <= 1:
                raise AppError(42201, "threshold 越界")
            thresholds.add(round(number, 3))
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    threshold = thresholds.pop() if len(thresholds) == 1 else None
    meta = {
        "file_id": file_id,
        "user_id": user_id,
        "page": "evaluate",
        "role": "data",
        "original_name": filename,
        "stored_name": stored.name,
        "size": len(payload),
        "sha256": sha256_hex(payload),
        "line": line,
        "columns": columns,
        "row_count": len(rows),
        "threshold": threshold,
        "label": label or Path(filename).stem,
        "created_at": iso(now()),
    }
    artifacts.write_json(folder / "import.json", meta)
    pos = sum(1 for row in rows if str(row.get("bug")) == "1")
    return {"meta": meta, "line": line, "sample_count": len(rows), "pos": pos, "neg": len(rows) - pos,
            "threshold": threshold, "columns": columns, "rows": rows, "path": stored}


def save_model_upload(user_id: str, filename: str, payload: bytes, line: str | None = None) -> dict:
    if not payload:
        raise AppError(40001, "未选择模型文件")
    if len(payload) > config.MAX_MODEL_UPLOAD_BYTES:
        raise AppError(41301, "模型文件超过 200MB 上限")
    if Path(filename).suffix.lower() not in (".pkl", ".pt"):
        raise AppError(40001, "仅支持 .pkl / .pt 模型文件")
    _cleanup_role(user_id, "predict", "model")
    model_ref = f"mdl_{new_id('artifact')[4:]}"
    folder = artifacts.upload_dir(user_id, model_ref)
    stored = folder / f"source{Path(filename).suffix.lower()}"
    stored.write_bytes(payload)
    meta = {
        "file_id": model_ref,
        "user_id": user_id,
        "page": "predict",
        "role": "model",
        "original_name": filename,
        "stored_name": stored.name,
        "size": len(payload),
        "sha256": sha256_hex(payload),
        "line": line,
        "columns": [],
        "row_count": 0,
        "created_at": iso(now()),
    }
    artifacts.write_json(folder / "import.json", meta)
    return {"model_ref": model_ref, "path": stored, "meta": meta}


def read_model_import(user_id: str, model_ref: str) -> tuple[dict, Path]:
    meta, path = read_import(user_id, model_ref)
    if meta.get("role") != "model":
        raise AppError(40401, "模型文件不存在")
    return meta, path
