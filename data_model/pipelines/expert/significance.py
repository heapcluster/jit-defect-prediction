"""expert 线统计显著性检验（原 data_model/16_statistical_test.py 移植）。

结论的支撑证据 —— 三步走：
1. **Bootstrap 置信区间**：检验集上重抽 1000 次，给出每个指标的 95% 区间；
   报告**同时**给出区间的上/下限 —— 一个指标只有下限也高于 0.7 才叫「稳」。
2. **随机基线对比（二项检验）**：真实模型 Recall@20% 与「随机前 20% 抽样」对比，
   `scipy.stats.binomtest` 给 p 值 —— 回答「是不是碰巧」。
3. **Wilcoxon 符号秩检验**：交付两两配对（lr vs rf、lr vs xgb、rf vs xgb），
   每条提交上谁的分更靠前 —— 回答「模型间差异是不是显著」。

≥0.7 判据说明：课程里程碑 M2 的验收线是 **AUC ≥ 0.70**（用户在与导师沟通后定下的），
不是拍脑袋的数。所有指标都在**同一检验集**上算 —— 时间序 70/30 切分由 05 产出，
本脚本**不重切**。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)

from . import config
from .data import load_effort
from .metrics import recall_at_effort
from .model import MODEL_NAMES, build_model

BOOTSTRAP_REPEATS = 1000
EFFORT_FRACTION = 0.2
AUC_TARGET = 0.7
PAIRWISE_PAIRS = [("lr", "rf"), ("lr", "xgb"), ("rf", "xgb")]
DELIVERY_MODELS = ("lr", "rf", "xgb")   # 契约约定: feature_order.txt 的 [models] 段


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="交付模型的 Bootstrap 置信区间 + 显著性检验",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--models", default=",".join(DELIVERY_MODELS))
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--bootstrap-repeats", type=int, default=BOOTSTRAP_REPEATS)
    p.add_argument("--effort-fraction", type=float, default=EFFORT_FRACTION)
    p.add_argument("--report", type=Path,
                   default=config.REPORTS_DIR / "statistical_test.md")
    return p.parse_args()


def bootstrap_ci(y: np.ndarray, proba: np.ndarray, n_repeats: int,
                 seed: int) -> dict[str, tuple[float, float, float]]:
    """重抽 n_repeats 次，返回 {指标: (均值, 下限, 上限)}。"""
    rng = np.random.default_rng(seed)
    n = len(y)
    metrics = {"auc": [], "f1": [], "precision": [], "recall": [], "accuracy": []}
    for _ in range(n_repeats):
        idx = rng.integers(0, n, size=n)
        y_b, p_b = y[idx], proba[idx]
        if len(np.unique(y_b)) < 2:
            continue
        pred = (p_b >= config.DECISION_THRESHOLD).astype(int)
        metrics["auc"].append(roc_auc_score(y_b, p_b))
        metrics["f1"].append(f1_score(y_b, pred, zero_division=0))
        metrics["precision"].append(precision_score(y_b, pred, zero_division=0))
        metrics["recall"].append(recall_score(y_b, pred, zero_division=0))
        metrics["accuracy"].append(accuracy_score(y_b, pred))
    out = {}
    for k, vals in metrics.items():
        arr = np.asarray(vals)
        out[k] = (float(arr.mean()), float(np.percentile(arr, 2.5)),
                  float(np.percentile(arr, 97.5)))
    return out


def top_by_effort(p: np.ndarray, effort: np.ndarray,
                  effort_fraction: float) -> np.ndarray:
    """Commits reviewable within an LOC budget, taken in score order.

    Budget = ``effort.sum() * effort_fraction``. Selection walks the
    score-descending order and stops once the cumulative LOC would exceed the
    budget, always keeping at least the first commit (a single high-LOC commit
    may alone exceed the budget; returning nothing would make the metric
    meaningless rather than honest).
    """
    order = np.argsort(-p, kind="stable")
    cum = np.cumsum(effort[order])
    within = int(np.searchsorted(cum, effort.sum() * effort_fraction,
                                 side="right"))
    return order[:max(1, within)]


def main() -> int:
    args = parse_args()
    for path in (args.train, args.test):
        if not path.is_file():
            print("[expert-significance] 找不到切分文件：%s（先跑 preparation/05_split_dataset.py）"
                  % path, file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    missing = [c for c in config.FEATURE_FIELDS + [config.LABEL_COL]
               if c not in train.columns]
    if missing:
        print("[expert-significance] 训练集缺列：%s" % missing, file=sys.stderr)
        return 2
    if config.LABEL_COL not in test.columns:
        print("[expert-significance] 检验集缺 `%s`：只认主标签 szz" % config.LABEL_COL,
              file=sys.stderr)
        return 2

    X_train = train[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[config.LABEL_COL].astype(int).to_numpy()
    X_test = test[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[config.LABEL_COL].astype(int).to_numpy()

    # 工作量代理: LOC = la + ld（原始值）。修掉旧 16 版的 ravel 交错问题：
    # load_effort 返回双列 DataFrame（effort_loc / effort_files），
    # 直接 .ravel() 会把两列交错成一个数组 —— 这里显式取 LOC 列。
    effort_df = load_effort(args.features_raw, test["commit_hash"])
    effort = np.maximum(effort_df["effort_loc"].to_numpy(dtype=float), 1.0)

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    unknown = [m for m in wanted if m not in MODEL_NAMES]
    if unknown:
        print("[expert-significance] 未知模型：%s；可选 %s" % (unknown, ",".join(MODEL_NAMES)),
              file=sys.stderr)
        return 2

    # 训练 + 全量预测概率（Bootstrap 与配对检验共用，保证口径一致）
    probas: dict[str, np.ndarray] = {}
    for name in wanted:
        model = build_model(name, args.seed)
        model.fit(X_train, y_train)
        probas[name] = model.predict_proba(X_test)[:, 1]
        print("[expert-significance] %-8s 拟合完成" % name)

    bootstrap = {name: bootstrap_ci(y_test, p, args.bootstrap_repeats, args.seed)
                 for name, p in probas.items()}

    # Effort-aware 配额：预算 = 检验集总 LOC 的 effort_fraction，
    # 按模型分数降序「花」预算，累计 LOC 不超过预算的提交都在审阅范围内。
    # 修掉旧口径：之前用 len(y_test) * fraction 取**条数**，effort 加载了却
    # 一行都没用 —— 那是 count-based，不是 Effort-aware（见下方的最小反例）。
    effort_budget = float(effort.sum()) * args.effort_fraction

    # 随机基线二项检验：Recall@effort_fraction（按 LOC 预算）
    binom_rows = []
    for name, p in probas.items():
        top = top_by_effort(p, effort, args.effort_fraction)
        hit = int(y_test[top].sum())
        k_pos = int(y_test.sum())
        # 随机排序下，审阅集合的期望 LOC 占比就是 effort_fraction，
        # 因此期望抓到的缺陷比例也是 effort_fraction。
        binom = stats.binomtest(hit, k_pos, args.effort_fraction,
                                alternative="greater")
        binom_rows.append((name, hit, k_pos, binom.pvalue, len(top)))

    # Wilcoxon 符号秩：交付模型两两配对（按正标签子集上的 rank 差）
    wilcoxon_rows = []
    ranks = {}
    for name, p in probas.items():
        r = np.empty_like(p)
        r[np.argsort(-p, kind="stable")] = np.arange(1, len(p) + 1)
        ranks[name] = r
    for a, b in PAIRWISE_PAIRS:
        if a not in ranks or b not in ranks:
            continue
        mask = y_test == 1
        diff = ranks[a][mask] - ranks[b][mask]
        diff = diff[diff != 0]
        if len(diff) < 10:
            wilcoxon_rows.append((a, b, float("nan"), len(diff)))
            continue
        stat = stats.wilcoxon(diff)
        wilcoxon_rows.append((a, b, float(stat.pvalue), len(diff)))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render(args, train, test, wanted, bootstrap, binom_rows, wilcoxon_rows,
               y_test, effort_budget),
        encoding="utf-8", newline="\n")
    print("[expert-significance] 显著性检验报告：%s" % args.report)
    return 0


def render(args, train, test, wanted, bootstrap, binom_rows, wilcoxon_rows,
           y_test, effort_budget) -> str:
    L: list[str] = []
    L.append(f"""# 交付模型统计显著性检验（pipelines/expert/significance.py 产出）

> 本文件可入库，对应里程碑 M2 的「模型优于随机」验收线（AUC ≥ {AUC_TARGET:.2f}）。
> 指标口径与 `pipelines/expert/metrics.py` 同源，本文件只做**统计推断**，不再复述公式。

## 数据与参数

| 项 | 值 |
|---|---|
| 训练集 | `{args.train.name}` —— {len(train)} 条 |
| 检验集 | `{args.test.name}` —— {len(test)} 条 |
| 模型 | {', '.join('`%s_v1`' % m for m in wanted)} |
| Bootstrap 重复次数 | {args.bootstrap_repeats}（种子 {args.seed}） |
| Effort-aware 预算 | 检验集总 LOC 的 {args.effort_fraction:.0%}（{effort_budget:.0f} LOC） |
| AUC 验收线 | ≥ {AUC_TARGET:.2f} |
| 检验集正样本比例 | {y_test.mean() * 100:.2f}% |

> Bootstrap 的重抽在**检验集内部**进行（衡量指标的抽样波动），**不是**重训模型；
> 训练/检验切分不变 —— 否则时间序信息会泄漏。

## 一、Bootstrap 95% 置信区间（检验集）

| 模型 | 指标 | 均值 | 95% 区间 |
|---|---|---|---|
""")
    for name in wanted:
        for key in ("auc", "f1", "precision", "recall", "accuracy"):
            mean, lo, hi = bootstrap[name][key]
            L.append("| `%s_v1` | %s | %.4f | [%.4f, %.4f] |\n"
                     % (name, key, mean, lo, hi))
    L.append(f"""
> **读法**：AUC 的区间**下限**也 ≥ {AUC_TARGET:.2f} 才叫「稳」；均值过线但下限不过线，
> 说明波动大、结论不稳。交付报告引用时写「95% CI [下限, 上限]」，别只写均值。

## 二、随机基线对比（二项检验， Recall@{args.effort_fraction:.0%} effort）

原假设：模型在「累计 LOC = 检验集总 LOC 的 {args.effort_fraction:.0%}」的审阅范围内抓到的
缺陷数，与「随机排序花同样预算」无差别。
备择假设：模型抓得**更多**（单侧检验）。

| 模型 | 审阅条数 | 抓到缺陷 | 随机期望 | p 值 | 结论（α=0.05） |
|---|---|---|---|---|---|
""")
    for name, hit, k_pos, p_value, n_reviewed in binom_rows:
        expected = args.effort_fraction * k_pos
        L.append("| `%s_v1` | %d | %d | %.1f | %.2e | %s |\n"
                 % (name, n_reviewed, hit, expected, p_value,
                    "**拒绝 H0（显著优于随机）**" if p_value < 0.05
                    else "不能拒绝 H0"))
    L.append("""
> 随机期望 = effort_fraction × 检验集缺陷总数（随机排序花同一 LOC 预算时，
> 期望抓到的缺陷占比就是预算占比）。p < 0.05 说明「抓这么多不是碰巧」。
>
> **口径说明**：这里的 Effort-aware 用 **LOC = la + ld** 作工作量代理（Kamei et al. 2013）。
> 旧版曾误用「提交条数的 20%」充当预算 —— 那是 count-based 指标，两者结果可差 0.5
> 召回（最小反例：LOC=[10,10,10,10,60]、标签=[0,1,0,0,1]，条数口径前 20% 只审 1 条
> 召回 0，LOC 预算可审 2 条召回 0.5）。已改为真实 LOC 预算。
""")

    L.append("""
## 三、交付模型两两配对（Wilcoxon 符号秩，正标签子集）

| 模型 A | 模型 B | 正标签数 | p 值 | 结论（α=0.05） |
|---|---|---|---|---|
""")
    for a, b, p_value, n_pos in wilcoxon_rows:
        if np.isnan(p_value):
            L.append("| `%s_v1` | `%s_v1` | %d | — | 正标签差值样本不足（<10），不检验 |\n"
                     % (a, b, n_pos))
        else:
            L.append("| `%s_v1` | `%s_v1` | %d | %.2e | %s |\n"
                     % (a, b, n_pos, p_value,
                        "**差异显著**" if p_value < 0.05 else "差异不显著"))
    L.append("""
> 只在**正标签**（真实缺陷）提交上比较 rank：模型的价值就在「把真缺陷排到前面」；
> 负标签上的排序差异对业务没有意义。
""")

    L.append(f"""
## 四、结论与边界

1. **所有指标同一检验集**：时间序 70/30 切分由 05 产出，本脚本不重切。
2. **交付边界**：`models/feature_order.txt` 的 `[models]` 段与 `predict.py` 未改 ——
   本文件只提供统计证据，不改任何交付物（specs/model-coverage R6）。
3. **α = 0.05，单侧检验**：全程一致；Bonferroni 校正未做（三组配对是预先声明的，
   不是事后挑选）。
4. **工作量表**：LOC = la + ld（原始值，下限 1.0）；`nf` 代理的对照数字见
   `reports/model_metrics.md` 的 Effort-aware 表。
5. **未做多类合并检验**：课程要求的是提交级二分类，多分类不在范围。
""")
    return "".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
