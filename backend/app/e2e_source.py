"""e2e 在线推理：模型线预计算文本 + 冻结 CodeBERT 分类头（懒加载）。

输入文本来自模型线 `e2e/data/commit_text.csv`（与训练同一份），保证在线/离线一致；
模型目录 `e2e/models/codebert_e2e_v1`（HF 序列分类，num_labels=2）。首次调用才加载。
导入失败（未装 transformers）/ 文本不在表内 → 返回 None，由调用方给明确提示。
"""

from __future__ import annotations

import csv
import logging
from functools import lru_cache

from app import config

logger = logging.getLogger("backend.e2e_source")

MAX_LEN = 512


def _text_csv():
    return config.PIPELINES_DIR / "e2e" / "data" / "commit_text.csv"


def _model_dir():
    return config.PIPELINES_DIR / "e2e" / "models" / "codebert_e2e_v1"


@lru_cache(maxsize=1)
def _texts() -> dict[str, str] | None:
    try:
        with open(_text_csv(), encoding="utf-8", newline="") as fh:
            return {row["commit_hash"].lower(): row["text"] for row in csv.DictReader(fh)}
    except (OSError, KeyError, csv.Error):
        logger.exception("e2e commit text table unavailable: %s", _text_csv())
        return None


@lru_cache(maxsize=1)
def _runtime():
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        logger.error("transformers unavailable; e2e online inference disabled")
        return None
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(_model_dir()))
        model = AutoModelForSequenceClassification.from_pretrained(
            str(_model_dir()), num_labels=2
        ).eval()
    except Exception:
        logger.exception("e2e model load failed: %s", _model_dir())
        return None
    return tokenizer, model


def available() -> bool:
    return _texts() is not None and _runtime() is not None


def predict_proba(commit_hash: str) -> float | None:
    """返回缺陷概率；文本不在表内 / 编码器不可用 → None（不编造）。"""
    texts = _texts()
    if texts is None:
        return None
    text = texts.get(commit_hash.lower())
    if text is None:
        return None
    runtime = _runtime()
    if runtime is None:
        return None
    import torch
    import torch.nn.functional as functional

    tokenizer, model = runtime
    enc = tokenizer(text, truncation=True, max_length=MAX_LEN, return_tensors="pt")
    with torch.no_grad():
        logits = model(**enc).logits
    return float(functional.softmax(logits, dim=-1)[0, 1])
