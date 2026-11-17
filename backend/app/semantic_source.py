"""语义特征来源（在线）：模型线预计算的 CodeBERT mean-pool embedding。

commit_hash → 768 维向量。semantic 模型输入即此向量；fused = Kamei 14 维 ⊕ 此向量。
懒加载（首次用到才读 npz）；MUST NOT 编造：提交不在表内返回 None。
"""

from __future__ import annotations

import logging
import threading
from functools import lru_cache

import numpy as np

from app import config
from app.services import text_inputs

logger = logging.getLogger("backend.semantic_source")

DIM = 768

# 预计算表未覆盖的新提交：在线编码后缓存在进程内（不重写 240MB 的 npz）
_incremental: dict[str, np.ndarray] = {}
_incremental_lock = threading.Lock()
_runtime_lock = threading.Lock()
_runtime_cache: tuple | None = None


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


def _runtime():
    """懒加载冻结 CodeBERT（与模型线 mean-pool 口径一致）；不可用 → None。"""
    global _runtime_cache
    with _runtime_lock:
        if _runtime_cache is not None:
            return _runtime_cache or None
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError:
            logger.error("transformers unavailable; on-demand semantic encoding disabled")
            _runtime_cache = ()
            return None
        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            # 模型已预下载到本机缓存：只用本地文件，避免每次加载都去 huggingface.co 做 HEAD 检查
            # （离线/代理不稳时每个文件等 10 秒，批量同步会被拖到分钟级）。
            tokenizer = AutoTokenizer.from_pretrained(
                config.SEMANTIC_TEXT_MODEL, local_files_only=True
            )
            encoder = (
                AutoModel.from_pretrained(config.SEMANTIC_TEXT_MODEL, local_files_only=True)
                .to(device)
                .eval()
            )
            for param in encoder.parameters():
                param.requires_grad_(False)
        except Exception:
            logger.exception("semantic text model load failed: %s", config.SEMANTIC_TEXT_MODEL)
            _runtime_cache = ()
            return None
        _runtime_cache = (tokenizer, encoder, device)
        return _runtime_cache


def _encode_text(text: str) -> np.ndarray | None:
    runtime = _runtime()
    if runtime is None:
        return None
    tokenizer, encoder, device = runtime
    import torch

    batch = tokenizer(
        [text],
        truncation=True,
        padding="max_length",
        max_length=config.SEMANTIC_MAX_LEN,
        return_tensors="pt",
    ).to(device)
    with torch.no_grad():
        hidden = encoder(**batch).last_hidden_state
        mask = batch["attention_mask"].unsqueeze(-1)
        pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
    return pooled[0].cpu().numpy().astype(np.float32)


def embedding_for(commit_hash: str) -> np.ndarray | None:
    """返回该提交的 768 维语义向量；缺预计算时在线编码，仍不可用 → None。"""
    table = _table()
    if table is not None:
        index, embeddings = table
        row = index.get(commit_hash.lower())
        if row is not None:
            return embeddings[row]
    key = commit_hash.lower()
    with _incremental_lock:
        cached = _incremental.get(key)
    if cached is not None:
        return cached
    text = text_inputs.commit_text(commit_hash)
    if text is None:
        return None
    vector = _encode_text(text)
    if vector is None:
        return None
    with _incremental_lock:
        _incremental[key] = vector
    return vector
