"""从配置的本地 Git 仓库现算单条 v1 特征；实现归模型线维护。"""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

from app import config
from app.services.git import is_ancestor


@lru_cache(maxsize=1)
def _extractor():
    # 插件化：FEATURE_EXTRACTOR_SCRIPT 覆盖默认抽取器（外部注册特征实现，零核心改动）
    script = (
        Path(config.FEATURE_EXTRACTOR_SCRIPT)
        if config.FEATURE_EXTRACTOR_SCRIPT
        else config.REPO_ROOT / "data_model" / "preparation" / "03_extract_features.py"
    )
    spec = importlib.util.spec_from_file_location("jit_extract_features", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("feature extractor unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract_single_commit


def extract(commit_hash: str, repo: Path | str | None = None) -> dict:
    """现算单条提交的 14 项特征。

    `repo` 默认取 `config.SOURCE_REPO`；批量同步（/api/sync）在远端 tip 不是
    SOURCE_REPO 当前 HEAD 祖先时，传入专用临时工作树路径（str），这里统一转 Path，
    避免调用方传字符串时在 `source / ".git"` 处炸出 `str / str`（2026-10-26 修复）。
    """
    source: Path | None = Path(repo) if repo is not None else config.SOURCE_REPO
    if source is None or not (source / ".git").exists():
        raise RuntimeError("source repository unavailable")
    # 快查可达性：不可达提交直接拒，避免 extract_single_commit 先扫全量历史
    # （8 万+ 提交的 git log --numstat）再判「目标不是当前 HEAD 可达的非合并提交」。
    if not is_ancestor(str(source), commit_hash):
        raise ValueError("目标不是当前 HEAD 可达的非合并提交")
    return _extractor()(source, commit_hash)
