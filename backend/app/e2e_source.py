"""e2e 在线推理：模型线预计算文本 + 冻结 CodeBERT 分类头（懒加载）。

输入文本来自模型线 `e2e/data/commit_text.csv`（与训练同一份），保证在线/离线一致；
模型目录 `e2e/models/codebert_e2e_v1`（HF 序列分类，num_labels=2）。首次调用才加载。
导入失败（未装 transformers）/ 文本不在表内 → 返回 None，由调用方给明确提示。
"""

from __future__ import annotations

import csv
import logging
import threading
from functools import lru_cache

from app import config
from app.services import text_inputs

logger = logging.getLogger("backend.e2e_source")

MAX_LEN = 512

# 预计算 commit_text.csv 未覆盖的新提交：在线构造 diff 文本后缓存在进程内
_computed: dict[str, str] = {}
_computed_lock = threading.Lock()


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
        # 交付模型目录是本地文件：禁止联网检查，离线/代理不稳时直接读盘
        tokenizer = AutoTokenizer.from_pretrained(str(_model_dir()), local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            str(_model_dir()), num_labels=2, local_files_only=True
        ).eval()
    except Exception:
        logger.exception("e2e model load failed: %s", _model_dir())
        return None
    return tokenizer, model


def available() -> bool:
    has_text = _texts() is not None or config.SOURCE_REPO is not None
    return has_text and _runtime() is not None


def _text_for(commit_hash: str) -> str | None:
    """先查预计算表，缺失时在线构造并缓存。"""
    key = commit_hash.lower()
    text = (_texts() or {}).get(key)
    if text is not None:
        return text
    with _computed_lock:
        text = _computed.get(key)
    if text is not None:
        return text
    text = text_inputs.commit_text(commit_hash)
    if text is None:
        return None
    with _computed_lock:
        _computed[key] = text
    return text


def predict_proba_text(text: str | None) -> float | None:
    """对给定变更文本直接前向；文本/编码器不可用 → None（不编造）。"""
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


def predict_proba(commit_hash: str) -> float | None:
    """返回缺陷概率；文本缺预计算时在线构造，仍不可用 → None（不编造）。"""
    return predict_proba_text(_text_for(commit_hash))
