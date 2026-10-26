"""semantic 线指标：与 expert 线 / 06_train_model.py 逐字同口径（跨线可比的前提）。"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from . import config


def cumulative_area(order, effort, y) -> float:
    total_e, total_y = float(effort.sum()), float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    area, cum_e, cum_y, prev = 0.0, 0.0, 0.0, 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        recall = cum_y / total_y
        area += 0.5 * (prev + recall) * (float(effort[i]) / total_e)
        prev = recall
    return area


def cumulative_curve(order, effort, y):
    total_e, total_y = float(effort.sum()), float(y.sum())
    xs, ys, ce, cy = [0.0], [0.0], 0.0, 0.0
    for i in order:
        ce += float(effort[i])
        cy += float(y[i])
        xs.append(ce / total_e)
        ys.append(cy / total_y)
    return np.array(xs), np.array(ys)


def recall_at_effort(order, effort, y, frac) -> float:
    total_e, total_y = float(effort.sum()), float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    cum_e = cum_y = 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        if cum_e / total_e >= frac:
            break
    return cum_y / total_y


def effort_aware_metrics(proba, y, effort) -> dict:
    effort = np.maximum(np.asarray(effort, dtype=float), 1.0)
    orders = {
        "model": np.argsort(-proba, kind="stable"),
        "density": np.argsort(-(proba / effort), kind="stable"),
        "optimal": np.argsort(-(y / effort), kind="stable"),
    }
    out = {
        k: {
            "area": cumulative_area(o, effort, y),
            "recall@20": recall_at_effort(o, effort, y, 0.20),
            "recall@50": recall_at_effort(o, effort, y, 0.50),
        }
        for k, o in orders.items()
    }
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    areas = [
        cumulative_area(rng.permutation(len(y)), effort, y)
        for _ in range(config.RANDOM_BASELINE_REPEATS)
    ]
    baseline = float(np.mean(areas))
    out["random"] = {
        "area": baseline,
        "area_std": float(np.std(areas)),
        "repeats": config.RANDOM_BASELINE_REPEATS,
        "recall@20": float("nan"),
        "recall@50": float("nan"),
    }
    denom = out["optimal"]["area"] - baseline
    for value in out.values():
        value["p_norm"] = (value["area"] - baseline) / denom if abs(denom) > 1e-12 else float("nan")
    return out


def effort_unaware(y, proba, threshold=None) -> dict:
    threshold = config.DECISION_THRESHOLD if threshold is None else threshold
    pred = (proba >= threshold).astype(int)
    return {
        "auc": float(roc_auc_score(y, proba)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y, pred)),
    }
