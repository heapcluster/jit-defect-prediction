"""语义线：CodeBERT-base 编码 commit message + diff，mean pooling，768 维。"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

_CACHE: dict[tuple[str, int], tuple[object, object]] = {}


def _load(model_name: str, max_len: int):
    key = (model_name, max_len)
    if key in _CACHE:
        return _CACHE[key]
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    _CACHE[key] = (tokenizer, model)
    return tokenizer, model


def encode_texts(
    texts: list[str], model_name: str, max_len: int = 512, batch_size: int = 8
) -> np.ndarray:
    import torch

    tokenizer, model = _load(model_name, max_len)
    vectors: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = tokenizer(
                batch, truncation=True, max_length=max_len, padding=True, return_tensors="pt"
            )
            output = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1)
            summed = (output * mask).sum(dim=1)
            counts = mask.sum(dim=1).clamp(min=1)
            vectors.append((summed / counts).cpu().numpy())
    if not vectors:
        return np.zeros((0, 768), dtype=np.float32)
    return np.vstack(vectors)


def compose_text(message: str, patch: str, max_chars: int = 4000) -> str:
    patch = (patch or "")[:max_chars]
    return f"{message or ''}\n{patch}".strip()


def load_cached_embedding(commit_hash: str) -> np.ndarray | None:
    path = os.getenv("SEMANTIC_EMBEDDINGS", "").strip()
    if not path:
        return None
    file = Path(path)
    if not file.is_file():
        return None
    data = np.load(file, allow_pickle=True)
    if "commit_hash" in data and "vectors" in data:
        hashes = [str(item) for item in data["commit_hash"].tolist()]
        if commit_hash in hashes:
            return data["vectors"][hashes.index(commit_hash)]
    if commit_hash in data:
        return data[commit_hash]
    return None
