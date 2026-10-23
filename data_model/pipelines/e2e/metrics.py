"""e2e 线（CodeBERT 微调）的两类指标计算。

口径与 `data_model/06_train_model.py` 逐字对齐（effort-aware 的面积/归一算法、随机基线
种子与抽样次数都一致），保证 e2e 与 expert 两条线的数字可直接比较。

两类指标：
① Effort-unaware：AUC / F1 / Precision / Recall / Accuracy（只看预测对不对）
② Effort-aware：按风险排序后，前 20% 工作量能抓多少缺陷（评审预算有限）

依赖：numpy + scikit-learn（与 expert 线同一套，不额外引入 torch）。
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# 与 06_train_model.py 同源：随机基线抽样次数与种子固定，保证跨线可比
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
LATENCY_BUDGET_MS = 500.0
DECISION_THRESHOLD = 0.5


def cumulative_area(order: np.ndarray, effort: np.ndarray, y: np.ndarray) -> float:
    """按给定顺序累加，返回「累计召回率 ~ 累计工作量占比」曲线下面积（梯形法）。"""
    total_e = float(effort.sum())
    total_y = float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    area = 0.0
    cum_e = 0.0
    cum_y = 0.0
    prev_recall = 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        recall = cum_y / total_y
        area += 0.5 * (prev_recall + recall) * (float(effort[i]) / total_e)
        prev_recall = recall
    return area


def recall_at_effort(order: np.ndarray, effort: np.ndarray, y: np.ndarray,
                     frac: float) -> float:
    """按给定顺序审查，累计工作量达到 frac 时已抓到多少比例的缺陷。"""
    total_e = float(effort.sum())
    total_y = float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    cum_e = 0.0
    cum_y = 0.0
    for i in order:
        cum_e += float(effort[i])
        cum_y += float(y[i])
        if cum_e / total_e >= frac:
            break
    return cum_y / total_y


def effort_aware_metrics(proba: np.ndarray, y: np.ndarray,
                         effort: np.ndarray) -> dict:
    """对四种排序各算一次曲线下面积与截断召回（同 06，此处不复述公式）。

    四种排序：model（概率降序）/ density（概率/工作量降序）/ optimal（真实密度上界）/
    random（固定种子 0 的 200 次抽样均值，作为 P_norm 的 0 锚点）。
    """
    effort = np.maximum(effort.astype(float), 1.0)  # 0 行改动会让密度除零
    orders = {
        "model": np.argsort(-proba, kind="stable"),
        "density": np.argsort(-(proba / effort), kind="stable"),
        "optimal": np.argsort(-(y / effort), kind="stable"),
    }
    out: dict[str, dict] = {}
    for key, order in orders.items():
        out[key] = {
            "area": cumulative_area(order, effort, y),
            "recall@20": recall_at_effort(order, effort, y, 0.20),
            "recall@50": recall_at_effort(order, effort, y, 0.50),
        }

    rng = np.random.default_rng(RANDOM_BASELINE_SEED)
    areas = []
    for _ in range(RANDOM_BASELINE_REPEATS):
        perm = rng.permutation(len(y))
        areas.append(cumulative_area(perm, effort, y))
    baseline = float(np.mean(areas))
    out["random"] = {
        "area": baseline,
        "area_std": float(np.std(areas)),
        "repeats": RANDOM_BASELINE_REPEATS,
        "recall@20": float("nan"),
        "recall@50": float("nan"),
    }

    denom = out["optimal"]["area"] - baseline
    for value in out.values():
        value["p_norm"] = (
            (value["area"] - baseline) / denom if abs(denom) > 1e-12
            else float("nan"))
    return out


def effort_unaware(y: np.ndarray, proba: np.ndarray,
                   threshold: float = DECISION_THRESHOLD) -> dict:
    """Effort-unaware 五指标 + 阈值切分后的预测。"""
    pred = (proba >= threshold).astype(int)
    return {
        "auc": float(roc_auc_score(y, proba)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y, pred)),
        "proba": proba,
        "pred": pred,
    }
