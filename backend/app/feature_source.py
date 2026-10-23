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


def extract(commit_hash: str) -> dict:
    repo: Path | None = config.SOURCE_REPO
    if repo is None or not (repo / ".git").exists():
        raise RuntimeError("source repository unavailable")
    return _extractor()(repo, commit_hash)
