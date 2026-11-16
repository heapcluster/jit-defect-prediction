"""在线构造提交 diff 文本：semantic / e2e 缺预计算输入时的兜底。

口径与模型线共用 `data_model/pipelines/text_source.py`（同截断、同占位串），不另写一份。
只在提交不在预计算表内时调用；构造失败返回 None，由调用方给明确提示，不编造文本。
"""

from __future__ import annotations

import logging
import sys
import threading
from functools import lru_cache

from app import config

logger = logging.getLogger("backend.text_inputs")

_cache: dict[str, str] = {}
_lock = threading.Lock()


def _shared_text_source():
    root = str(config.REPO_ROOT / "data_model")
    if root not in sys.path:
        sys.path.insert(0, root)
    from pipelines import text_source  # noqa: PLC0415 —— 延迟导入，避免启动期加载 pandas

    return text_source


@lru_cache(maxsize=2)
def _repo(repo_path: str):
    from git import Repo  # noqa: PLC0415

    return Repo(repo_path)


def commit_text(commit_hash: str) -> str | None:
    """返回该提交的变更文本；提交不可读 / 未配置 SOURCE_REPO → None。"""
    key = commit_hash.lower()
    with _lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    repo_path = config.SOURCE_REPO
    if repo_path is None or not (repo_path / ".git").exists():
        return None
    try:
        text_source = _shared_text_source()
        commit = _repo(str(repo_path)).commit(commit_hash)
        has_parents = bool(commit.parents)
        diffs = commit.diff(commit.parents[0], create_patch=True, R=True) if has_parents else []
        assembled = text_source.assemble(diffs, config.TEXT_MAX_CHARS)
        text, _ = text_source.classify(has_parents, assembled)
    except Exception as exc:  # noqa: BLE001 —— 兜底失败按缺输入处理，不把 traceback 甩给请求
        logger.warning("commit text unavailable for %s: %s", commit_hash, exc)
        return None
    with _lock:
        _cache[key] = text
    return text
