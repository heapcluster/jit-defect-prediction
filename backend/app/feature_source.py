"""从配置的本地 Git 仓库现算单条 v1 特征；实现归模型线维护。"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

from app import config


@lru_cache(maxsize=1)
def _extractor():
    script = config.REPO_ROOT / "data_model" / "preparation" / "03_extract_features.py"
    spec = importlib.util.spec_from_file_location("jit_extract_features", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("feature extractor unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract_single_commit


def extract(commit_hash: str, repo: Path | None = None) -> dict:
    """现算单条提交的 14 项特征。

    `repo` 默认取 `config.SOURCE_REPO`；批量同步（/api/sync）在远端 tip 不是
    SOURCE_REPO 当前 HEAD 祖先时，传入专用临时工作树路径，避免改动用户的检出状态。
    """
    source: Path | None = repo if repo is not None else config.SOURCE_REPO
    if source is None or not (source / ".git").exists():
        raise RuntimeError("source repository unavailable")
    return _extractor()(source, commit_hash)
