"""W5 指标单一来源（契约命名 evaluation/metrics.py）。

公式与 expert 线 `pipelines/expert/metrics.py` **逐字同口径**（同一套 sklearn 调用、
同一套 effort-aware 数学），本文件自包含常量，不依赖 expert 线的配置模块 ——
expert/semantic/fused/e2e 四线与新 train CORE 一律从这里取公式，防止第二套口径漂移。
`safe_summary` 只是退化场景（空检验集 / 单类检验集）的包装，**不是第二套公式**：
非退化时直接返回 `effort_unaware` 的原样结果。

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
    该性能口径尚待模型负责人补充权威说明；缺口列于 `docs/common/pending.md`。
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# 与 expert/config.py 同值（单一来源常量；parity 测试钉死，不得漂移）
DECISION_THRESHOLD = 0.5
RANDOM_BASELINE_SEED = 0
RANDOM_BASELINE_REPEATS = 200


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
    """累计 (工作量占比, 召回率) 点列 —— 供 report.py 画 effort 曲线。"""
    total_e, total_y = float(effort.sum()), float(y.sum())
    xs, ys, ce, cy = [0.0], [0.0], 0.0, 0.0
    for i in order:
        ce += float(effort[i])
        cy += float(y[i])
        xs.append(ce / total_e)
        ys.append(cy / total_y)
    return np.array(xs), np.array(ys)


def recall_at_effort(order, effort, y, frac) -> float:
    return recall_and_count_at_effort(order, effort, y, frac)[0]


def recall_and_count_at_effort(order, effort, y, frac):
    """累计工作量达到 frac 时的（召回率, 已审提交条数）。

    条数很重要：同样的 20% LOC 预算，按 risk_score 降序可能只审到几百条巨提交，
    按风险密度降序却要审两万多条 —— 不写条数，「召回高」很容易被误读成「更准」。
    """
    total_e, total_y = float(effort.sum()), float(y.sum())
    if total_e <= 0 or total_y <= 0:
        return float("nan"), 0
    order = np.asarray(order)
    cum_e = np.cumsum(effort[order])
    idx = int(np.searchsorted(cum_e, total_e * frac, side="left"))
    idx = min(idx, len(order) - 1)
    cum_y = float(np.cumsum(y[order])[: idx + 1][-1])
    return cum_y / total_y, idx + 1


def _spearman(a, b) -> float:
    """秩相关。必须用平均秩处理并列（effort 里有大量相同值），否则相关性会被压低。"""
    from scipy.stats import rankdata

    ra = rankdata(a)
    rb = rankdata(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def budget_order(proba, effort, floor) -> np.ndarray:
    """预算感知排序：先过滤掉不值得单独评审的小提交，再按风险密度降序。

    低于 `floor` 的提交排到队尾（仍可能被审到，只是优先级最低），这样 20% 预算
    不会一次性被两万多条 8 行提交吃掉，也不至于像 `risk_score` 降序那样被少数巨
    提交独占。

    `floor` 的单位必须与 `effort` 一致（LOC 口径是"行"，nf 口径是"文件"），
    由调用方按口径传入 —— 本函数不再假设"10 行"这种固定值（评审意见 #2）。
    """
    floor = float(floor)
    eligible = np.where(effort >= floor)[0]
    tiny = np.where(effort < floor)[0]
    head = eligible[np.argsort(-(proba[eligible] / effort[eligible]), kind="stable")]
    tail = tiny[np.argsort(-proba[tiny], kind="stable")]
    return np.concatenate([head, tail])


def effort_aware_metrics(proba, y, effort, review_floor=None) -> dict:
    """`review_floor` 是该 effort 口径下的"最小可评审工作量"，None 表示不启用预算感知口径。

    单位随口径走：LOC 口径传行数（`config.MIN_REVIEW_LOC`），nf 口径要传文件数
    （`config.MIN_REVIEW_FILES`），不能拿 10 行去卡 10 个文件（评审意见 #2）。
    """
    effort = np.maximum(np.asarray(effort, dtype=float), 1.0)  # 0 行防除零
    orders = {
        "model": np.argsort(-proba, kind="stable"),
        "density": np.argsort(-(proba / effort), kind="stable"),
    }
    if review_floor is not None:
        orders["budget"] = budget_order(proba, effort, review_floor)
    orders["optimal"] = np.argsort(-(y / effort), kind="stable")
    out = {}
    for k, o in orders.items():
        rec20, n20 = recall_and_count_at_effort(o, effort, y, 0.20)
        out[k] = {
            "area": cumulative_area(o, effort, y),
            "recall@20": rec20,
            "recall@50": recall_at_effort(o, effort, y, 0.50),
            "n_commits@20": n20,
        }
    rng = np.random.default_rng(RANDOM_BASELINE_SEED)
    areas, rec20s = [], []
    for _ in range(RANDOM_BASELINE_REPEATS):
        perm = rng.permutation(len(y))
        areas.append(cumulative_area(perm, effort, y))
        rec20s.append(recall_at_effort(perm, effort, y, 0.20))
    baseline = float(np.mean(areas))
    out["random"] = {
        "area": baseline,
        "area_std": float(np.std(areas)),
        "repeats": RANDOM_BASELINE_REPEATS,
        "recall@20": float(np.mean(rec20s)),
        "recall@50": float("nan"),
        "n_commits@20": round(len(y) * 0.20),
    }
    # 规模混杂诊断：risk_score 与「提交规模」的秩相关。
    # 高相关意味着按 risk_score 降序 ≈ 先审最大的提交，effort-aware 指标必然被拖累。
    out["confound"] = {
        "spearman_risk_log_effort": _spearman(proba, np.log(effort)),
        "median_effort": float(np.median(effort)),
    }
    denom = out["optimal"]["area"] - baseline
    for k in [k for k in out if "area" in out[k]]:  # 只给排序项算归一值，跳过 confound
        out[k]["p_norm"] = (
            (out[k]["area"] - baseline) / denom if abs(denom) > 1e-12 else float("nan")
        )
        # 文献标准别名（同一数字的两种叫法，避免「自造口径」的误读）：
        #   popt = 1 − Δopt（Mende & Koschke, CSMR 2010；形式与本组 P_norm 一致）
        #   ce20 = CE@20%（20% 工作量处的缺陷召回率，20-80 原则）
        out[k]["popt"] = out[k]["p_norm"]
        out[k]["ce20"] = out[k]["recall@20"]
    return out


def effort_unaware(y, proba, threshold=None) -> dict:
    threshold = DECISION_THRESHOLD if threshold is None else threshold
    pred = (proba >= threshold).astype(int)
    return {
        "auc": float(roc_auc_score(y, proba)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y, pred)),
    }


def safe_summary(y, proba, threshold=0.5) -> tuple[dict, list[str]]:
    """退化场景包装（不是第二套公式）：

    · 空检验集 → 五项指标全 None + 警告（不编造 0）；
    · 单类检验集 → AUC 无定义置 None + 警告，其余四项仍用 effort_unaware 的
      同一套 sklearn zero_division=0 公式；
    · 非退化 → 原样返回 effort_unaware 结果，warnings=[]。
    """
    y = np.asarray(y)
    proba = np.asarray(proba, dtype=float)
    if y.size == 0:
        return (
            {key: None for key in ("auc", "f1", "precision", "recall", "accuracy")},
            ["empty_test_set_metrics_undefined"],
        )
    if len(np.unique(y)) < 2:
        pred = (proba >= threshold).astype(int)
        return (
            {
                "auc": None,
                "f1": float(f1_score(y, pred, zero_division=0)),
                "precision": float(precision_score(y, pred, zero_division=0)),
                "recall": float(recall_score(y, pred, zero_division=0)),
                "accuracy": float(accuracy_score(y, pred)),
            },
            ["single_class_test_auc_undefined"],
        )
    return effort_unaware(y, proba, threshold), []


# ── W7 指标注册表与统一计算入口（公式仍来自上方单源函数，不另写口径）──
METRICS = [
    {
        "key": "auc",
        "name": "ROC 曲线下面积",
        "description": "概率排序判别能力",
        "formula": "sklearn.roc_auc_score",
        "threshold_dependent": False,
        "effort_aware": False,
    },
    {
        "key": "ap",
        "name": "平均精确率",
        "description": "PR 曲线平均精确率",
        "formula": "sklearn.average_precision_score",
        "threshold_dependent": False,
        "effort_aware": False,
    },
    {
        "key": "f1",
        "name": "F1 分数",
        "description": "精确率与召回率调和平均",
        "formula": "sklearn.f1_score",
        "threshold_dependent": True,
        "effort_aware": False,
    },
    {
        "key": "precision",
        "name": "精确率",
        "description": "预测为正中的真正例比例",
        "formula": "sklearn.precision_score",
        "threshold_dependent": True,
        "effort_aware": False,
    },
    {
        "key": "recall",
        "name": "召回率",
        "description": "真正例被预测出的比例",
        "formula": "sklearn.recall_score",
        "threshold_dependent": True,
        "effort_aware": False,
    },
    {
        "key": "accuracy",
        "name": "准确率",
        "description": "预测正确的样本比例",
        "formula": "sklearn.accuracy_score",
        "threshold_dependent": True,
        "effort_aware": False,
    },
    {
        "key": "recall_at_20",
        "name": "Recall@20% 工作量",
        "description": "审查 20% 工作量时的缺陷召回率",
        "formula": "effort_aware_metrics.model.recall@20",
        "threshold_dependent": False,
        "effort_aware": True,
    },
    {
        "key": "recall_at_50",
        "name": "Recall@50% 工作量",
        "description": "审查 50% 工作量时的缺陷召回率",
        "formula": "effort_aware_metrics.model.recall@50",
        "threshold_dependent": False,
        "effort_aware": True,
    },
    {
        "key": "p_norm",
        "name": "P_norm",
        "description": "模型排序面积相对随机/最优的归一化",
        "formula": "effort_aware_metrics.model.p_norm",
        "threshold_dependent": False,
        "effort_aware": True,
    },
    {
        "key": "popt",
        "name": "Popt",
        "description": "P_norm 的文献标准别名（1−Δopt）",
        "formula": "effort_aware_metrics.model.popt",
        "threshold_dependent": False,
        "effort_aware": True,
    },
]
DEFAULT_METRICS = ["auc", "ap", "f1", "precision", "recall", "accuracy"]
_EFFORT_KEYS = {
    "recall_at_20": "recall@20",
    "recall_at_50": "recall@50",
    "p_norm": "p_norm",
    "popt": "popt",
}


def registry() -> list[dict]:
    return [dict(item) for item in METRICS]


def metric_keys() -> list[str]:
    return [item["key"] for item in METRICS]


def compute_metrics(y, proba, threshold=DECISION_THRESHOLD, *, effort=None, selected=None):
    """按所选指标计算数值；不可用项置 None 并给原因，绝不伪造 0。

    非 effort 指标复用 effort_unaware/sklearn 单源；effort 指标复用 effort_aware_metrics，
    缺 effort（LOC 工作量）时返回 missing_effort，不从概率反推工作量。
    """
    selected = list(selected) if selected else list(DEFAULT_METRICS)
    y = np.asarray(y)
    proba = np.asarray(proba, dtype=float)
    values, unavailable = {}, []
    base, base_warnings = safe_summary(y, proba, threshold)
    for key in selected:
        if key in _EFFORT_KEYS:
            if effort is None:
                values[key] = None
                unavailable.append(
                    {
                        "key": key,
                        "reason_code": "missing_effort",
                        "message": "缺 LOC 工作量输入，effort-aware 指标不可用",
                    }
                )
                continue
            aware = effort_aware_metrics(proba, y, np.asarray(effort, dtype=float))["model"]
            value = aware[_EFFORT_KEYS[key]]
            values[key] = (
                None
                if value is None or (isinstance(value, float) and np.isnan(value))
                else float(value)
            )
            continue
        if key == "ap":
            if y.size == 0 or len(np.unique(y)) < 2:
                values[key] = None
                unavailable.append(
                    {
                        "key": key,
                        "reason_code": "single_class_auc_undefined",
                        "message": "空或单类样本，AP 无定义",
                    }
                )
            else:
                values[key] = float(average_precision_score(y, proba))
            continue
        values[key] = base.get(key)
    for warning in base_warnings:
        if any(item["reason_code"] == warning for item in unavailable):
            continue
        for key in selected:
            if key not in _EFFORT_KEYS and values.get(key) is None:
                unavailable.append({"key": key, "reason_code": warning, "message": warning})
                break
    return values, unavailable
