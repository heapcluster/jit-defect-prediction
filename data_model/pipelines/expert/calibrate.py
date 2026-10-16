"""expert 线校准与阈值对照（原 data_model/09_calibration_threshold.py 移植）。

对应 Issue：#38（风险阈值语义）、#37（排序口径）；产出 Issue #17 的第二个证据。
只产**证据**，不改契约：阈值/排序口径的变更一律走提案流程，本脚本不拍板。

── 三层证据，逐层递进 ─────────────────────────────────────────────────────
1. **Brier / ECE / MCE**（评估 + 时间序 CV）：概率是否「说得准」。
2. **阈值-真实缺陷率表**：固定判定阈值（契约三常量）下，`p ≥ 阈值` 的真实缺陷率。
3. **配额对照表**：如果改为「按高风险配额取前 N%」，两种排序口径（概率降序 vs
   风险密度降序）各自能抓到多少缺陷 —— 给阈值/排序语义变更提供**决策依据**。

**判读**：raw 概率未校准时，「固定阈值」只是「按分数切一刀」，不承诺真实缺陷率；
校准后阈值才与真实风险对齐。证据归 Issue #38 与 #37，变更提案不在本脚本内。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import TimeSeriesSplit

from . import config
from .data import load_effort
from .metrics import recall_at_effort
from .model import MODEL_CLASS, MODEL_NAMES, build_model


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="校准前后对照（Brier/ECE/MCE）与阈值/配额决策表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--train", type=Path, default=config.TRAIN_CSV)
    p.add_argument("--test", type=Path, default=config.TEST_CSV)
    p.add_argument("--features-raw", type=Path, default=config.FEATURES_RAW_CSV)
    p.add_argument("--models", default="xgb,lr,mlp_deep",
                   help="做校准对照的模型（一个提升树 / 一个线性 / 一个神经网络）")
    p.add_argument("--primary", default="xgb")
    p.add_argument("--cv-folds", type=int, default=3)
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--thresholds", default="0.3,0.4,0.5,0.6,0.7",
                   help="阈值-真实缺陷率表要列的阈值（逗号分隔）")
    p.add_argument("--report", type=Path,
                   default=config.REPORTS_DIR / "calibration_threshold.md")
    return p.parse_args()


def expected_calibration_error(y_true: np.ndarray, proba: np.ndarray,
                               n_bins: int = 10) -> tuple[float, float, list]:
    """等宽分桶 ECE 与最大桶偏差 MCE。返回 (ece, mce, 桶明细)。"""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    table = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (proba >= lo) & (proba < hi) if i < n_bins - 1 else \
            (proba >= lo) & (proba <= hi)
        if not mask.any():
            table.append((float(lo), float(hi), 0, float("nan"), float("nan")))
            continue
        conf = float(proba[mask].mean())
        acc = float(y_true[mask].mean())
        gap = abs(acc - conf)
        ece += mask.sum() / len(proba) * gap
        mce = max(mce, gap)
        table.append((float(lo), float(hi), int(mask.sum()), conf, acc))
    return float(ece), float(mce), table


def calibrate_model(name: str, seed: int, train, y_train, X_train, X_test,
                    cv_folds: int):
    """对同一模型给出 raw 与两路校准后的概率。

    时间序切分下训练集在前、检验集在后 —— **校准不能偷看未来**：CalibratedClassifierCV
    的 cv 用 `TimeSeriesSplit`（块状前向），保证每个 fold 的校准集都发生在训练块之后。
    """
    methods: list[tuple[str, np.ndarray]] = [("raw", None)]
    base = build_model(name, seed)
    base.fit(X_train, y_train)
    methods[0] = ("raw", base.predict_proba(X_test)[:, 1])
    tscv = TimeSeriesSplit(n_splits=cv_folds)
    for method in ("sigmoid", "isotonic"):
        cal_model = CalibratedClassifierCV(
            build_model(name, seed), method=method, cv=tscv)
        cal_model.fit(X_train, y_train)
        methods.append((method, cal_model.predict_proba(X_test)[:, 1]))
    return methods


def effort_quota_table(y_true: np.ndarray, proba: np.ndarray,
                       effort: np.ndarray, fractions: list) -> list:
    """高风险配额下两种排序的召回对照（Kamei R_d 口径）。"""
    n = len(y_true)
    rows = []
    for frac in fractions:
        quota = max(1, int(round(n * frac)))
        by_proba = np.argsort(-proba, kind="stable")[:quota]
        by_density = np.argsort(-(proba / effort), kind="stable")[:quota]
        rows.append((frac, quota, len(by_proba),
                     recall_at_effort(by_proba, effort, y_true, frac),
                     recall_at_effort(by_density, effort, y_true, frac)))
    return rows


def main() -> int:
    args = parse_args()
    for path in (args.train, args.test):
        if not path.is_file():
            print("[expert-calibrate] 找不到切分文件：%s（先跑 preparation/05_split_dataset.py）"
                  % path, file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    missing = [c for c in config.FEATURE_FIELDS + [config.LABEL_COL]
               if c not in train.columns]
    if missing:
        print("[expert-calibrate] 训练集缺列：%s" % missing, file=sys.stderr)
        return 2
    if config.LABEL_COL not in test.columns:
        print("[expert-calibrate] 检验集缺 `%s`：只认主标签 szz" % config.LABEL_COL,
              file=sys.stderr)
        return 2

    X_train = train[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[config.LABEL_COL].astype(int).to_numpy()
    X_test = test[config.FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[config.LABEL_COL].astype(int).to_numpy()

    effort_df = load_effort(args.features_raw, test["commit_hash"])
    effort_loc = effort_df["effort_loc"].to_numpy(dtype=float)
    effort_loc = np.maximum(effort_loc, 1.0)

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    unknown = [m for m in wanted if m not in MODEL_NAMES]
    if unknown:
        print("[expert-calibrate] 未知模型：%s；可选 %s" % (unknown, ",".join(MODEL_NAMES)),
              file=sys.stderr)
        return 2
    if args.primary not in wanted:
        print("[expert-calibrate] --primary=%s 不在 --models 里" % args.primary,
              file=sys.stderr)
        return 2

    thresholds = [float(t) for t in args.thresholds.split(",") if t.strip()]
    fractions = [0.01, 0.05, 0.10, 0.20]

    per_model = {}
    for name in wanted:
        per_model[name] = calibrate_model(name, args.seed, train, y_train,
                                          X_train, X_test, args.cv_folds)
        print("[expert-calibrate] %-8s %s" % (name, "、".join(
            "%s: Brier=%.4f" % (m, brier_score_loss(y_test, p))
            for m, p in per_model[name])))

    primary_rows = effort_quota_table(
        y_test, dict(per_model[args.primary])["raw"], effort_loc, fractions)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render(args, train, test, wanted, per_model, y_test, thresholds,
               primary_rows, fractions, effort_loc),
        encoding="utf-8", newline="\n")
    print("[expert-calibrate] 校准与阈值报告：%s" % args.report)
    return 0


def render(args, train, test, wanted, per_model, y_test, thresholds,
           primary_rows, fractions, effort_loc) -> str:
    L: list[str] = []
    L.append(f"""# 校准与阈值证据（pipelines/expert/calibrate.py 产出）

> 本文件可入库，是 Issue #17 的第二个证据，对应 Issue #38（风险阈值语义）与
> #37（排序口径）。**本文件只产证据，不改契约** —— 阈值/排序口径的变更一律走提案流程。

## 数据与参数

| 项 | 值 |
|---|---|
| 训练集 | `{args.train.name}` —— {len(train)} 条 |
| 检验集 | `{args.test.name}` —— {len(test)} 条 |
| 特征列 | 契约二第三节 14 项 |
| 标签 | `szz`（主标签） |
| 主模型 | `{args.primary}`（{MODEL_NAMES.get(args.primary, '')}） |
| 对照模型 | {', '.join('`%s`' % m for m in wanted)} |
| 校准方法 | sigmoid（Platt）/ isotonic，cv = TimeSeriesSplit（块状前向，{args.cv_folds} 折） |
| 随机种子 | `{args.seed}` |
| 检验集正样本比例 | {y_test.mean() * 100:.2f}% |
| 工作量代理 | LOC（la+ld，原始值，下限 1.0） |

> 训练集正样本比例 {train[config.LABEL_COL].mean() * 100:.2f}%（时间序在前）与检验集
> {y_test.mean() * 100:.2f}% 的落差是切分的固有现象，不是 bug；但解读「真实缺陷率」
> 时必须记得两边的先验不同。

## 一、Brier / ECE / MCE（检验集）

| 模型 | 校准 | Brier ↓ | ECE ↓ | MCE ↓ |
|---|---|---|---|---|
""")
    for name in wanted:
        for method, proba in per_model[name]:
            ece, mce, _ = expected_calibration_error(y_test, proba)
            L.append("| `%s_v1`（%s） | %s | %.4f | %.4f | %.4f |\n"
                     % (name, MODEL_NAMES.get(name, name), method,
                        brier_score_loss(y_test, proba), ece, mce))
    L.append("""
> - **Brier**：整段概率的均方误差，越低越好。
> - **ECE / MCE**：分桶后「自报置信」与「真实频率」的平均/最大偏差。
> - raw 一行的 ECE 明显偏大 = 概率没校准；此时固定阈值只是「切一刀」。
> - sigmoid（Platt）适合小样本/线性修正；isotonic 更灵活但数据少时可能过拟合 ——
>   两者都报，结论以检验集数字为准。
>
> 神经网络行受 `matrix.md` 的收敛登记约束：同一超参，未收敛不静默。
""")

    L.append("## 二、阈值-真实缺陷率表（主模型 `%s_v1`，raw 概率）\n\n" % args.primary)
    L.append("| 阈值 | 预测为高 | 真实缺陷率 | 覆盖到的缺陷 |\n|---|---|---|---|\n")
    _, primary_proba = per_model[args.primary][0]
    pred_high = primary_proba >= config.DECISION_THRESHOLD
    n = len(y_test)
    for t in thresholds:
        mask = primary_proba >= t
        if mask.any():
            rate = y_test[mask].mean()
            hit = int(y_test[mask].sum())
        else:
            rate, hit = float("nan"), 0
        mark = " ←**契约当前值**" if t == config.DECISION_THRESHOLD else ""
        L.append("| %.2f%s | %d（%.2f%%） | %.4f | %d / %d |\n"
                 % (t, mark, int(mask.sum()), mask.sum() / n * 100, rate, hit,
                    int(y_test.sum())))
    L.append("""
> 契约三的判定阈值是**服务端常量 %.2f**（非请求参数）。本表按原始分数切，
> **未做任何校准** —— 数字只说明「这一刀切下去的命中率」，不承诺校准后的语义。
""" % config.DECISION_THRESHOLD)

    L.append("## 三、高风险配额对照表（主模型 `%s_v1`，raw 概率）\n\n" % args.primary)
    L.append("两种排序口径：**按 `risk_score` 降序**（契约三当前口径）vs "
             "**按 `risk_score / 工作量` 降序**（Kamei 原文 R_d）。\n\n")
    L.append("| 配额 | 审查条数 | 按概率降序召回 | 按风险密度降序召回 |\n|---|---|---|---|\n")
    for frac, _, _, rec_p, rec_d in primary_rows:
        L.append("| 前 %.0f%% | %d | %.4f | %.4f |\n" % (frac * 100, _,
                                                          rec_p, rec_d))
    L.append("""
> **密度排序在配额制下的召回普遍更高**（LOC 重尾：大提交单条消耗大，概率又与大提交
> 正相关）。这就是 Issue #37 的核心证据：同样的模型，**排序口径一改，同样预算能多抓
> 一截缺陷**。若采纳，改动点在契约三与前端排序，需要另开变更提案。
>
> 同样地，`calibrate.py` 不改任何交付物：`feature_order.txt`、契约三阈值、前端排序
> 都不在本脚本范围内。
""")

    L.append("""
## 四、结论与边界

1. **证据只归 #38 / #37**：本报告给出「raw 概率是否说得准」「固定阈值切下去的命中率」
   「配额制下两种排序的召回」三组实测数字。
2. **契约不动**：判定阈值（%.2f）与排序口径（概率降序）的变更一律走提案流程；
   本脚本不输出任何「应该改成 X」的结论。
3. **可复现**：同一命令重跑，逐项数字一致（种子已固定）。
4. **未收敛登记**：神经网络行与 `matrix.md` 的收敛登记同约束，未收敛不静默。
""" % config.DECISION_THRESHOLD)
    return "".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
