"""通用工具：ID、时间、JSON、哈希。"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime

ID_PREFIX = {
    "user": "u_",
    "dataset": "ds_",
    "job": "job_",
    "evaluation": "eva_",
    "artifact": "art_",
    "figure": "fig_",
    "commit": "cmt_",
}


def new_id(kind: str) -> str:
    """类型前缀 + 32 位小写十六进制，总长 ≤ 36。"""
    return f"{ID_PREFIX[kind]}{secrets.token_hex(16)}"


def now() -> datetime:
    """本地时区（Asia/Shanghai 运行环境）的朴素时间，落库用。"""
    return datetime.now().replace(microsecond=0)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # 入库时间为本地朴素时间；astimezone() 会按本地时区补齐偏移。
        value = value.astimezone()
    return value.isoformat()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def loads(text: str | None, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def is_commit_hash(value: str | None) -> bool:
    return bool(value and _COMMIT_RE.match(value))


_NAME_RE = re.compile(r"^[A-Za-z0-9\u4e00-\u9fa5_\-]+$")


def valid_name(name: str | None) -> bool:
    return bool(name and 1 <= len(name) <= 128 and _NAME_RE.match(name))


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n\t]", "_", name).strip().strip(".")
    return cleaned[:120] or "export"
