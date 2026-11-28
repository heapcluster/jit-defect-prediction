"""分类指标：阈值类 + 概率类。"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _safe(fn, default=None):
    try:
        value = fn()
        if value is None:
            return default
        return float(value)
    except Exception:  # noqa: BLE001
        return default


def binary_predictions(y_score: np.ndarray, threshold: float) -> np.ndarray:
    return (np.asarray(y_score, dtype=float) >= threshold).astype(int)


def compute_metrics(
    y_true, y_score, threshold: float = 0.5, metrics: list[str] | None = None
) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    pred = binary_predictions(y_score, threshold)
    selected = metrics or ["accuracy", "precision", "recall", "f1", "auc", "mcc"]
    single_class = len(set(y_true.tolist())) < 2
    result: dict[str, float | None] = {}
    for name in selected:
        if name == "accuracy":
            result[name] = _safe(lambda: accuracy_score(y_true, pred))
        elif name == "precision":
            result[name] = _safe(lambda: precision_score(y_true, pred, zero_division=0))
        elif name == "recall":
            result[name] = _safe(lambda: recall_score(y_true, pred, zero_division=0))
        elif name == "f1":
            result[name] = _safe(lambda: f1_score(y_true, pred, zero_division=0))
        elif name == "auc":
            result[name] = None if single_class else _safe(lambda: roc_auc_score(y_true, y_score))
        elif name == "ap":
            result[name] = None if single_class else _safe(lambda: average_precision_score(y_true, y_score))
        elif name == "mcc":
            result[name] = _safe(lambda: matthews_corrcoef(y_true, pred))
    return result


def confusion(y_true, y_score, threshold: float = 0.5) -> tuple[int, int, int, int]:
    y_true = np.asarray(y_true, dtype=int)
    pred = binary_predictions(y_score, threshold)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return int(tn), int(fp), int(fn), int(tp)
