"""expert 线指标：Effort-unaware + Effort-aware（与 06_train_model.py 逐字同口径）。

Effort-aware 定义（复算说明，四条线一致）：
  · 模型排序：按 risk_score 降序（契约三当前口径）
  · 密度排序：按 risk_score/工作量 降序（Kamei 原文 R_d，对照）
  · 上界排序：按真实缺陷密度 y/e 降序（上帝视角）
  · 随机基线：种子 0 的 200 次排列取均值，P_norm 的 0 锚点 —— 面积必须落在 0.5 附近，
    否则面积算法有问题，其余数字都不能信。

── 文献口径对照（2026-10-16 核实，回应「补 CE@20% / Recall@20% / Popt / ALPA」）──
  · **Popt**：Mende & Koschke（CSMR 2010, pp. 107–116）提出，定义为 `Popt = 1 − Δopt`
    ——Δopt 是「最优排序（按缺陷**密度**降序）与模型排序」之间的面积差，并按「最优 − 随机」
    归一（综述见 Çarka, Esposito & Falessi, *On effort-aware metrics for defect prediction*,
    EMSE 27(152), 2022, DOI 10.1007/s10664-022-10186-7）。本模块的 `p_norm`
    = (A_model − A_random) / (A_optimal − A_random) **与该形式一致**，故 `popt` 作为其
    文献标准别名一并输出（原始论文的积分表达仍建议复核）。
  · **CE@20% / Recall@20%**：20% 工作量截断处的缺陷召回率（「20-80 原则」，见 Huang, Xia,
    Lo, *Revisiting supervised and unsupervised models for effort-aware JIT defect
    prediction*, EMSE 24(5), 2019）。本模块 `recall@20` 即该口径，`ce20` 为其别名。
  · **ALPA**：多轮检索未获可核验的原始定义出处，**本模块不实现**（不编造指标），
    登记为待补 —— 见 `docs/model/model-line-plan.md` §4.2 的口径对照表。
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

from . import config


def cumulative_area(order, effort, y) -> float:
    total_e, total_y = float(effort.sum()), float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    area, cum_e, cum_y, prev = 0.0, 0.0, 0.0, 0.0
    for i in order:
        cum_e += float(effort[i]); cum_y += float(y[i])
        recall = cum_y / total_y
        area += 0.5 * (prev + recall) * (float(effort[i]) / total_e)
        prev = recall
    return area


def cumulative_curve(order, effort, y):
    """累计 (工作量占比, 召回率) 点列 —— 供 report.py 画 effort 曲线。"""
    total_e, total_y = float(effort.sum()), float(y.sum())
    xs, ys, ce, cy = [0.0], [0.0], 0.0, 0.0
    for i in order:
        ce += float(effort[i]); cy += float(y[i])
        xs.append(ce / total_e); ys.append(cy / total_y)
    return np.array(xs), np.array(ys)


def recall_at_effort(order, effort, y, frac) -> float:
    total_e, total_y = float(effort.sum()), float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan")
    cum_e = cum_y = 0.0
    for i in order:
        cum_e += float(effort[i]); cum_y += float(y[i])
        if cum_e / total_e >= frac:
            break
    return cum_y / total_y


def effort_aware_metrics(proba, y, effort) -> dict:
    effort = np.maximum(np.asarray(effort, dtype=float), 1.0)  # 0 行防除零
    orders = {
        "model": np.argsort(-proba, kind="stable"),
        "density": np.argsort(-(proba / effort), kind="stable"),
        "optimal": np.argsort(-(y / effort), kind="stable"),
    }
    out = {k: {"area": cumulative_area(o, effort, y),
               "recall@20": recall_at_effort(o, effort, y, 0.20),
               "recall@50": recall_at_effort(o, effort, y, 0.50)}
           for k, o in orders.items()}
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    areas = [cumulative_area(rng.permutation(len(y)), effort, y)
             for _ in range(config.RANDOM_BASELINE_REPEATS)]
    baseline = float(np.mean(areas))
    out["random"] = {"area": baseline, "area_std": float(np.std(areas)),
                     "repeats": config.RANDOM_BASELINE_REPEATS,
                     "recall@20": float("nan"), "recall@50": float("nan")}
    denom = out["optimal"]["area"] - baseline
    for value in out.values():
        value["p_norm"] = ((value["area"] - baseline) / denom
                            if abs(denom) > 1e-12 else float("nan"))
        # 文献标准别名（同一数字的两种叫法，避免「自造口径」的误读）：
        #   popt = 1 − Δopt（Mende & Koschke, CSMR 2010；形式与本组 P_norm 一致）
        #   ce20 = CE@20%（20% 工作量处的缺陷召回率，20-80 原则）
        value["popt"] = value["p_norm"]
        value["ce20"] = value["recall@20"]
    return out


def effort_unaware(y, proba, threshold=None) -> dict:
    threshold = config.DECISION_THRESHOLD if threshold is None else threshold
    pred = (proba >= threshold).astype(int)
    return {"auc": float(roc_auc_score(y, proba)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "accuracy": float(accuracy_score(y, pred))}
