"""产物目录、表格读写、manifest 与文件哈希。"""

from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import pandas as pd

from app import config
from app.utils import canonical_json, sha256_hex

REPO_ROOT = config.REPO_ROOT


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def resolve(relative: str) -> Path:
    path = (REPO_ROOT / relative).resolve()
    if not str(path).startswith(str(REPO_ROOT.resolve())):
        raise ValueError("非法路径")
    return path


def ensure_dirs() -> None:
    for path in (
        config.REPOS_DIR,
        config.UPLOADS_DIR,
        config.OUTPUTS_DIR,
        config.DATASETS_DIR,
        config.MODELS_DIR,
        config.EVALUATIONS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def output_dir(user_id: str, job_id: str) -> Path:
    path = config.OUTPUTS_DIR / user_id / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def dataset_dir(dataset_id: str) -> Path:
    path = config.DATASETS_DIR / dataset_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_dir(user_id: str, model_name: str) -> Path:
    path = config.MODELS_DIR / user_id / model_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def evaluation_dir(user_id: str, evaluation_id: str) -> Path:
    path = config.EVALUATIONS_DIR / user_id / evaluation_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def upload_dir(user_id: str, file_id: str) -> Path:
    path = config.UPLOADS_DIR / user_id / file_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def read_table(path: Path) -> tuple[list[str], list[dict]]:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    else:
        frame = pd.read_excel(path, dtype=str, keep_default_na=False)
    columns = [str(item) for item in frame.columns]
    rows = frame.fillna("").to_dict(orient="records")
    return columns, rows


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in columns})


def write_excel(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([{name: row.get(name, "") for name in columns} for row in rows], columns=columns)
    frame.to_excel(path, index=False, engine="openpyxl")


def table_bytes(columns: list[str], rows: list[dict], fmt: str) -> bytes:
    if fmt == "excel":
        buffer = io.BytesIO()
        frame = pd.DataFrame([{name: row.get(name, "") for name in columns} for row in rows], columns=columns)
        frame.to_excel(buffer, index=False, engine="openpyxl")
        return buffer.getvalue()
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in columns})
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def write_manifest(path: Path, payload: dict) -> None:
    write_json(path, payload)


def copy_asset(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def ops_hash(operations: list[dict]) -> str:
    from app.constants import CLEAN_DEFAULTS
    from app.utils import sha256_text

    normalized = []
    for item in sorted(operations, key=lambda op: op.get("op", "")):
        name = item.get("op")
        params = dict(CLEAN_DEFAULTS.get(name, {}))
        params.update({k: v for k, v in (item.get("params") or {}).items()})
        normalized.append({"op": name, "params": params})
    return sha256_text(canonical_json(normalized))


def dedupe_key(source: str) -> str:
    from app.utils import sha256_text

    return sha256_text(source)
