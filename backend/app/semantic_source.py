"""语义特征来源（在线）：模型线预计算的 CodeBERT mean-pool embedding。

commit_hash → 768 维向量。semantic 模型输入即此向量；fused = Kamei 14 维 ⊕ 此向量。
懒加载（首次用到才读 npz）；MUST NOT 编造：提交不在表内返回 None。
"""

from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np

from app import config

logger = logging.getLogger("backend.semantic_source")

DIM = 768


@lru_cache(maxsize=1)
def _table() -> tuple[dict[str, int], np.ndarray] | None:
    path = config.SEMANTIC_EMBEDDINGS
    try:
        data = np.load(path, allow_pickle=False)
        hashes = [str(h).lower() for h in data["commit_hash"]]
        embeddings = data["embeddings"].astype(np.float32)
    except (OSError, ValueError, KeyError):
        logger.exception("semantic embeddings unavailable: %s", path)
        return None
    if embeddings.ndim != 2 or embeddings.shape[1] != DIM or len(hashes) != len(embeddings):
        logger.error("semantic embeddings shape mismatch: %s", embeddings.shape)
        return None
    return {h: i for i, h in enumerate(hashes)}, embeddings


def embedding_for(commit_hash: str) -> np.ndarray | None:
    """返回该提交的 768 维语义向量；不在预计算表内 / 表不可用 → None。"""
    table = _table()
    if table is None:
        return None
    index, embeddings = table
    row = index.get(commit_hash.lower())
    if row is None:
        return None
    return embeddings[row]
