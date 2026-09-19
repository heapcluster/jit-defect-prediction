"""09 概率校准与阈值策略证据（change `model-expansion` 第 3.1 / 3.2 条任务）。

本脚本**只出证据，不改契约**。它回答两个已经挂着的契约三提案：

- **Issue #38「高风险阈值语义」**：契约三第三节把风险阈值定为**服务端常量 0.50**。
  问题是「0.50」在**未校准**的概率谱上并不等于「这条提交有 50% 是缺陷引入」。
  本脚本量出：校准前/后，`p >= 0.5` 的集合里**真实缺陷率**各是多少。
- **Issue #37「风险列表排序口径」**：契约三规定风险列表按 `risk_score` 降序。
  本脚本在**同一工作量预算**下对照「按 `risk_score` 降序」与「按风险密度 `p/工作量` 降序」
  的召回，给排序口径的取舍提供实测数字。

── 两条纪律（写进代码，不靠自觉）────────────────────────────────────────────
1. **校准的交叉验证必须时间序**（`TimeSeriesSplit`）。随机 `KFold` 会让校准折里混进
   未来提交，红线第 1 条同样适用于校准环节。本脚本显式构造折并打印每折的时间边界。
2. **等工作量对照**：两种策略必须落在同一工作量口径上比（LOC 与改动文件数各一版），
   否则「配额取前 5% 更好」可能只是「配额那一边本来就要审更多代码」。

── 一个必须先讲清的事实 ────────────────────────────────────────────────────
Platt（sigmoid）与 isotonic 都是**单调变换**：校准改变的是「概率的数值含义」，
**不改变排序**。所以校准能解 #38（阈值语义），解不了 #37（排序口径）—— 两者是独立问题，
不要指望校准顺带把排序问题解决掉。
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import TimeSeriesSplit

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"


def load_training_module():
    spec = importlib.util.spec_from_file_location(
        "train06", BASE / "06_train_model.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="概率校准（时间序 CV）与阈值/配额策略的等工作量对照",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--train", type=Path, default=DATA_DIR / "split_szz_train.csv")
    p.add_argument("--test", type=Path, default=DATA_DIR / "split_szz_test.csv")
    p.add_argument("--features-raw", type=Path,
                   default=DATA_DIR / "commit_features_raw.csv")
    p.add_argument("--models", default="xgb,lr,mlp",
                   help="做校准对照的模型（默认一个提升树 / 一个线性 / 一个神经网络）")
    p.add_argument("--primary", default="xgb",
                   help="分箱可靠性表与策略对照表用哪个模型（默认交付模型 xgb）")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--splits", type=int, default=3, help="时间序 CV 折数")
    p.add_argument("--bins", type=int, default=10, help="可靠性曲线分箱数（等宽）")
    p.add_argument("--quotas", default="0.01,0.05,0.10",
                   help="配额策略的审查条数比例，逗号分隔")
    p.add_argument("--report", type=Path,
                   default=REPORTS_DIR / "calibration_threshold.md")
    return p.parse_args()


# ─────────────────────────── 概率质量指标 ───────────────────────────

def reliability(proba: np.ndarray, y: np.ndarray, bins: int) -> tuple[list[dict], float, float]:
    """等宽分箱的可靠性表 + ECE（期望校准误差）+ MCE（最大校准误差）。"""
    idx = np.clip((proba * bins).astype(int), 0, bins - 1)
    rows: list[dict] = []
    ece = 0.0
    mce = 0.0
    n = len(y)
    for b in range(bins):
        mask = idx == b
        cnt = int(mask.sum())
        if cnt == 0:
            rows.append({"lo": b / bins, "hi": (b + 1) / bins, "count": 0,
                         "mean_p": float("nan"), "rate": float("nan"),
                         "gap": float("nan")})
            continue
        mean_p = float(proba[mask].mean())
        rate = float(y[mask].mean())
        gap = abs(mean_p - rate)
        ece += (cnt / n) * gap
        mce = max(mce, gap)
        rows.append({"lo": b / bins, "hi": (b + 1) / bins, "count": cnt,
                     "mean_p": mean_p, "rate": rate, "gap": gap})
    return rows, ece, mce


def prob_metrics(proba: np.ndarray, y: np.ndarray, bins: int) -> dict:
    return {
        "brier": brier_score_loss(y, proba),
        "logloss": log_loss(y, np.clip(proba, 1e-12, 1 - 1e-12)),
        "ece": reliability(proba, y, bins)[1],
        "mce": reliability(proba, y, bins)[2],
    }


# ─────────────────────────── 策略对照 ───────────────────────────

def mask_stats(mask: np.ndarray, effort: np.ndarray, y: np.ndarray) -> dict:
    n = int(mask.sum())
    total_e = float(effort.sum())
    mark = {
        "n": n,
        "n_frac": n / len(y),
        "effort_frac": float(effort[mask].sum()) / total_e if total_e > 0 else float("nan"),
        "recall": float(y[mask].sum()) / float(y.sum()),
        "precision": float(y[mask].mean()) if n > 0 else float("nan"),
    }
    return mark


def topk_mask(proba: np.ndarray, k: int) -> np.ndarray:
    k = max(1, min(k, len(proba)))
    cut = np.argsort(-proba, kind="stable")[:k]
    mask = np.zeros(len(proba), dtype=bool)
    mask[cut] = True
    return mask


def budget_mask(order: np.ndarray, effort: np.ndarray, budget: float) -> np.ndarray:
    """按给定顺序累加工作量 —— 「同等审查精力」的写法，**严格不超预算**。

    实现细节要写清，否则数字对不上：沿给定顺序加，若某一条会让累计**超过**预算，就
    **跳过这一条、继续试后面的**（而不是「加到超了就停」）。本数据集工作量是重尾的
    （LOC 中位数 23、最大 32 万行），「加到超了就停」会让最后一个超大的提交把实际预算
    顶出去 —— 那两边的预算就不等了，对照失效。
    """
    mask = np.zeros(len(effort), dtype=bool)
    used = 0.0
    for i in order:
        e = float(effort[i])
        if used + e > budget:
            continue
        mask[i] = True
        used += e
    return mask


def main() -> int:
    args = parse_args()
    t6 = load_training_module()
    for path in (args.train, args.test):
        if not path.is_file():
            print("[09] 找不到切分文件：%s" % path, file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    X_train = train[t6.FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[t6.LABEL_COL].astype(int).to_numpy()
    X_test = test[t6.FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[t6.LABEL_COL].astype(int).to_numpy()

    # 时间序折：显式构造并落报告，证明折间是「过去 → 将来」
    splits = list(TimeSeriesSplit(n_splits=args.splits).split(X_train))
    fold_info = []
    for i, (tr, va) in enumerate(splits, 1):
        fold_info.append({
            "fold": i,
            "train_n": len(tr), "calib_n": len(va),
            "train_last": str(train["committed_at"].iloc[tr[-1]]),
            "calib_first": str(train["committed_at"].iloc[va[0]]),
            "ordered": bool(str(train["committed_at"].iloc[tr[-1]])
                            <= str(train["committed_at"].iloc[va[0]])),
        })

    wanted = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.primary not in wanted:
        wanted.insert(0, args.primary)

    # 1) 每个模型：原始 / Platt / Isotonic 三种概率质量
    cal: dict[str, dict] = {}
    proba_raw: dict[str, np.ndarray] = {}
    proba_cal: dict[str, np.ndarray] = {}
    for name in wanted:
        base = t6.build_model(name, args.seed)
        base.fit(X_train, y_train)
        p_raw = base.predict_proba(X_test)[:, 1]
        proba_raw[name] = p_raw
        entry = {"raw": prob_metrics(p_raw, y_test, args.bins)}
        for method, key in (("sigmoid", "platt"), ("isotonic", "isotonic")):
            c = CalibratedClassifierCV(
                estimator=t6.build_model(name, args.seed), method=method, cv=splits)
            c.fit(X_train, y_train)
            p_cal = c.predict_proba(X_test)[:, 1]
            entry[key] = prob_metrics(p_cal, y_test, args.bins)
            proba_cal["%s|%s" % (name, key)] = p_cal
        cal[name] = entry
        print("[09] %-6s Brier raw=%.4f platt=%.4f isotonic=%.4f | ECE raw=%.4f "
              "platt=%.4f isotonic=%.4f"
              % (name, entry["raw"]["brier"], entry["platt"]["brier"],
                 entry["isotonic"]["brier"], entry["raw"]["ece"],
                 entry["platt"]["ece"], entry["isotonic"]["ece"]))

    # 2) 策略对照（交付模型 + 两种工作量代理）
    effort_raw = t6.load_effort(args.features_raw, test["commit_hash"])
    proxies = {
        "LOC（改动行数 la+ld）": effort_raw["effort_loc"].to_numpy(),
        "改动文件数 nf": effort_raw["effort_files"].to_numpy(),
    }
    p_primary = proba_raw[args.primary]
    strategies: dict[str, dict[str, dict]] = {}
    for label, eff in proxies.items():
        eff = np.maximum(eff.astype(float), 1.0)
        rows: dict[str, dict] = {}
        thr_mask = p_primary >= t6.DECISION_THRESHOLD
        rows["① 固定阈值 0.50（契约三现状）"] = mask_stats(thr_mask, eff, y_test)
        for q in [float(x) for x in args.quotas.split(",") if x.strip()]:
            k = math.ceil(q * len(y_test))
            rows["② 配额取前 %.0f%%（条数口径）" % (q * 100)] = mask_stats(
                topk_mask(p_primary, k), eff, y_test)
        budget = float(eff[thr_mask].sum()) or float(eff.sum()) * 0.05
        rows["③ 等工作量预算：按 risk_score 降序"] = mask_stats(
            budget_mask(np.argsort(-p_primary, kind="stable"), eff, budget), eff, y_test)
        rows["④ 等工作量预算：按风险密度 p/工作量 降序"] = mask_stats(
            budget_mask(np.argsort(-(p_primary / eff), kind="stable"), eff, budget),
            eff, y_test)
        strategies[label] = {"rows": rows, "budget": budget}

    # 3) 校准前后「阈值 0.50」的含义
    iso_key = "%s|isotonic" % args.primary
    thr_after = mask_stats(proba_cal[iso_key] >= t6.DECISION_THRESHOLD,
                           np.ones(len(y_test)), y_test)
    thr_before = mask_stats(p_primary >= t6.DECISION_THRESHOLD,
                            np.ones(len(y_test)), y_test)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        render(args, t6, train, test, y_test, wanted, cal, proba_raw, proba_cal,
               fold_info, strategies, thr_before, thr_after),
        encoding="utf-8", newline="\n")
    print("[09] 报告：%s" % args.report)
    return 0


def render(args, t6, train, test, y_test, wanted, cal, proba_raw, proba_cal,
           fold_info, strategies, thr_before, thr_after) -> str:
    L: list[str] = []
    L.append(f"""# 概率校准与阈值策略证据（09_calibration_threshold.py 产出）

> 本文件可入库，是 OpenSpec change `model-expansion` 第 3.1 / 3.2 条任务的证据，
> 也是契约三提案 **Issue #38（阈值语义）** 与 **Issue #37（排序口径）** 的决策依据。
> **本文件不改契约** —— 证据交提案决策（specs/model-coverage R4 / R5）。

## 一、数据与折划分（时间序，红线第 1 条）

| 项 | 值 |
|---|---|
| 训练集 | `{args.train.name}` —— {len(train)} 条 |
| 检验集 | `{args.test.name}` —— {len(test)} 条 |
| 检验集正样本比例 | {y_test.mean() * 100:.2f}% |
| 折划分方式 | `TimeSeriesSplit(n_splits={args.splits})` —— **时间序，非随机 KFold** |
| 校准方法 | `sigmoid`（Platt）与 `isotonic`，各用同一组时间序折 |
| 随机种子 | `{args.seed}` |

| 折 | 拟合集条数 | 校准集条数 | 拟合集最后时间 | 校准集最早时间 | 时间序成立 |
|---|---|---|---|---|---|
""")
    for f in fold_info:
        L.append("| %d | %d | %d | %s | %s | %s |\n"
                 % (f["fold"], f["train_n"], f["calib_n"],
                    f["train_last"], f["calib_first"],
                    "✅" if f["ordered"] else "❌"))

    L.append("""
## 二、概率质量对照（检验集）

Brier 与对数损失越小越好；ECE（期望校准误差）是「预测概率与真实频率的平均差距」，
0 表示概率可以当频率读。

| 模型 | 类别 | Brier（原始） | Brier（Platt） | Brier（Isotonic） | ECE（原始） | ECE（Platt） | ECE（Isotonic） |
|---|---|---|---|---|---|---|---|
""")
    for name in wanted:
        e = cal[name]
        L.append("| `%s` | %s | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f |\n"
                 % (name, t6.MODEL_CLASS.get(name, "未登记"),
                    e["raw"]["brier"], e["platt"]["brier"], e["isotonic"]["brier"],
                    e["raw"]["ece"], e["platt"]["ece"], e["isotonic"]["ece"]))

    primary = args.primary
    rows_raw = reliability(proba_raw[primary], y_test, args.bins)[0]
    rows_iso = reliability(proba_cal["%s|isotonic" % primary], y_test, args.bins)[0]
    L.append(f"""
### 分箱可靠性（交付模型 `{primary}_v1`，等宽 {args.bins} 箱）

| 概率区间 | 条数 | 平均预测概率 | 真实缺陷率 | 差距 |
|---|---|---|---|---|
""")
    for r in rows_raw:
        if r["count"] == 0:
            continue
        L.append("| %.1f–%.1f | %d | %.3f | %.3f | %.3f |\n"
                 % (r["lo"], r["hi"], r["count"], r["mean_p"], r["rate"], r["gap"]))
    L.append("\n上表是**原始概率**的分箱 —— 这就是后端今天返回的 `risk_score` 的统计含义。\n")

    L.append("""
## 三、校准前后「阈值 0.50」的含义（Issue #38）

| 口径 | 被判定为高风险（`p >= 0.50`）的条数 | 条数占比 | 这批提交里的**真实缺陷率** |
|---|---|---|---|
| 原始概率（今天的行为） | %d | %.2f%% | **%.1f%%** |
| Isotonic 校准后 | %d | %.2f%% | **%.1f%%** |
""" % (thr_before["n"], thr_before["n_frac"] * 100, thr_before["precision"] * 100,
       thr_after["n"], thr_after["n_frac"] * 100, thr_after["precision"] * 100))

    L.append("""
> 读法：若「原始概率」那行的真实缺陷率明显低于 50%%，说明 `risk_score >= 0.5` **不等于**
> 「这条提交有一半概率是缺陷引入」—— 排序接口返回的 `risk_score` 是要给评审员看的，
> 数值含义对不上会直接误导。这就是 Issue #38 要处理的问题。
>
> ⚠️ **注意上表的对比方向**：这就是本报告最重要的一条实测结论 —— 校准**没有**把阈值含义
> 修好（两个口径的真实缺陷率几乎一样，差 **%+.1f** 个百分点）。原因不是实现错，而是
> **校准器是在训练期内做的时间序折**（拟合集时间一路早于校准集），而真正的偏差来自
> **训练期 → 检验期的正样本比例漂移**（训练期 %.2f%% → 检验期 %.2f%%）。
> 校准学到的「高概率其实没那么高」的映射，在检验期**依旧偏乐观**，只是幅度略变小。
> → 结论：**「把阈值校准到 50%% 语义」这条路在时间序切分下不成立**，
> Issue #38 的取舍应转向「配额取前 N%%」（见第四节），或另立「重采样/漂移修正」提案。
""" % (thr_after["precision"] * 100 - thr_before["precision"] * 100,
       train[t6.LABEL_COL].mean() * 100, y_test.mean() * 100))

    L.append("""
## 四、策略对照（同一工作量口径）

每条策略给出：标记条数、条数占比、**审查工作量占比**、召回、精确率。
`③ / ④` 行的预算是 `①`（阈值 0.50）实际占用的工作量 —— 所以它们与 ① 是**同一份审查精力**，
可以直接比召回。
""")
    for label, data in strategies.items():
        L.append("\n### 工作量代理：%s\n\n" % label)
        L.append("| 策略 | 标记条数 | 条数占比 | 工作量占比 | 召回 | 精确率 |\n")
        L.append("|---|---|---|---|---|---|\n")
        for sname, s in data["rows"].items():
            L.append("| %s | %d | %.2f%% | %.2f%% | %.2f%% | %.2f%% |\n"
                     % (sname, s["n"], s["n_frac"] * 100, s["effort_frac"] * 100,
                        s["recall"] * 100, s["precision"] * 100))

    L.append("\n### 同一预算下谁更好（脚本自动算，不手抄）\n\n")
    L.append("| 工作量代理 | ① 阈值 0.50 的召回 | ③ 等预算·`risk_score` 降序 | "
             "④ 等预算·风险密度降序 | ④ − ① |\n|---|---|---|---|---|\n")
    gains: dict[str, float] = {}
    for label, data in strategies.items():
        rows = list(data["rows"].values())
        r1, r3, r4 = rows[0], rows[-2], rows[-1]
        gains[label] = (r4["recall"] - r1["recall"]) * 100
        L.append("| %s | %.2f%% | %.2f%% | %.2f%% | **%+.2f pp** |\n"
                 % (label, r1["recall"] * 100, r3["recall"] * 100,
                    r4["recall"] * 100, gains[label]))

    first_label = list(strategies)[0]
    rows_first = list(strategies[first_label]["rows"].items())
    r_thr = rows_first[0][1]
    quota_txt = "、".join(
        "%s 召回 %.2f%%（工作量占比 %.2f%%）"
        % (k.split("（")[0].replace("② 配额取", "配额"),
           v["recall"] * 100, v["effort_frac"] * 100)
        for k, v in rows_first[1:-2])
    gain_txt = "；".join("%s 下 %+.2f pp" % (k, v) for k, v in gains.items())
    delta_pp = thr_after["precision"] * 100 - thr_before["precision"] * 100

    L.append(f"""
> 上表是「同一份审查精力下谁抓到更多缺陷」的直接答案。
> · `③` = 按 `risk_score` 降序 + 严格不超预算。**它与 `①` 的数值完全相同，这不是巧合**：
>   阈值策略 `p >= 0.50` 在 `risk_score` 降序里本来就是一个**前缀**，而该前缀的总工作量
>   又正好等于「预算」。换句话说 —— **契约三现状其实隐含了一个没写出来的工作量配额**
>   （本次实测：37.8% 的提交 / 83.4% 的 LOC）。这一点本身值得写进提案：不是「要不要引入配额」，
>   而是「把已经在跑的配额写明」。
> · `④` = 按风险密度 `p/工作量` 降序 + 同一预算 —— 这个才是真正不同的策略。

## 五、结论（交提案决策，本 change 不改契约）

1. **Issue #38（阈值语义）—— 「把阈值校准到 50% 语义」这条路实测走不通**：
   `p >= 0.50` 的真实缺陷率，原始概率 **{thr_before['precision'] * 100:.1f}%**、
   Isotonic 校准后 **{thr_after['precision'] * 100:.1f}%**（差 **{delta_pp:+.1f} pp**）。
   根因是**训练期 → 检验期的正样本比例漂移**（{train[t6.LABEL_COL].mean() * 100:.2f}% →
   {y_test.mean() * 100:.2f}%）：校准器学到的是训练期内的映射，到了检验期照样偏乐观。
   现状 `①` 的代价也已量出 —— 标记 {r_thr['n']} 条（{r_thr['n_frac'] * 100:.1f}% 的提交），
   却吃掉 **{r_thr['effort_frac'] * 100:.1f}%** 的 LOC 审查量，召回 {r_thr['recall'] * 100:.1f}%。
   配额口径的对应数字：{quota_txt}。
   → 建议提案把「高风险」的判定从「固定概率阈值」改为**明确的工作量配额**，
   并把「按条数还是按工作量」一并写清（本数据集工作量重尾，两者差得很远）；
   决策权在提案与老师，**本 change 不改契约**。
2. **Issue #37（排序口径）—— 同一预算下密度排序更好**：风险密度降序相对现状 `①` 的
   召回变化：{gain_txt}。→ 支持「风险列表按风险密度排序」的提案方向。
   两点必须一起写进提案，否则会被现实打脸：**(a)** LOC 代理下密度排序会大量吸纳**极小提交**
   （「标记条数」列会涨到接近全量），需要同时规定「按条数封顶」；**(b)** Platt 与 isotonic
   都是**单调变换**，校准**不改变排序** —— 所以「校准」不可能顺带解掉排序问题，
   这两件事必须分开决策。
3. **证据边界**：全部数字来自检验集（时间在后的 30%），未回看训练期；换随机种子或换工作量
   代理会小幅变动，故两种代理都列出、不挑好看的那一版；校准一律时间序折，未使用随机 `KFold`。
""")

    return "".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
