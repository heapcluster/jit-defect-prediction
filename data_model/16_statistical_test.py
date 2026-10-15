"""16 统计显著性检验：模型两两差异是真的，还是单次划分的偶然。

对应 OpenSpec change: semantic-feature-mainline（第 11.3 条任务）
口径来源：`docs/common/test-strategy.md` §1；`openspec/changes/semantic-feature-mainline/design.md` D9

── 为什么需要这个脚本 ────────────────────────────────────────────────────
`08_model_matrix.py` 报出的「谁比谁高 0.003」是**单次时间划分下的一个数字**，
没有方差、没有检验。8 个模型在同一检验集上是**配对**的（同样的提交、同样的标签），
所以「xgb 比 rf 好」这句话必须回答：这个差是否可能只是检验集抽样的噪声？

── 三种检验，各回答一个问题 ───────────────────────────────────────────────
1. **Bootstrap（≥1000 次重采样）** —— 给出每个模型每个指标的**分布**，
   而不是一个点估计。回答「这个数字有多不确定」。
2. **Wilcoxon signed-rank（配对）** —— 在**同一组 bootstrap 样本**上两两比较，
   回答「A 与 B 的差是否系统性为正」。用配对版而非独立版，是因为两者看的是同一批提交。
3. **McNemar 检验** —— 只用阈值 0.5 下的**二值对错**，回答「A 判对的样本里 B 判错的
   是否显著多于反过来」。它不看概率排序，只看决策本身。

── 配对是怎么保证的（关键）───────────────────────────────────────────────
Bootstrap 的**重采样下标对所有模型完全一致**。若不共用下标，A 和 B 的差异里
会混进「抽样不同」的噪声，Wilcoxon 的前提就破了。

── 多重比较校正 ───────────────────────────────────────────────────────────
8 个模型 → 28 个两两比较。不做校正时，α=0.05 下期望约 1.4 个假阳性。
故同时报**原始 p 值**与 **Bonferroni 校正后阈值**（α/比较次数），两者都列，不藏。

── 本脚本测的是什么、不测什么（如实说明）──────────────────────────────────
· 测：**检验集抽样不确定性** —— 模型只训一次（固定种子），重采样只发生在检验集上。
· 不测：训练过程本身的不确定性（那需要 bootstrap 后重训，成本高一个量级）。
  论文两种做法都有；本脚本取前者，并在报告中写明该口径，不冒充后者。

跑法（环境 jit-defect，不需要 torch）：
    cd data_model && python 16_statistical_test.py
产出：
    data_model/reports/statistical_test.md
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, wilcoxon

BASE = Path(__file__).resolve().parent
REPORTS_DIR = BASE / "reports"

# 从 06 复用特征口径、模型构造与工作量指标（文件名以数字开头，须按路径加载）
_spec06 = importlib.util.spec_from_file_location("train06", BASE / "06_train_model.py")
t06 = importlib.util.module_from_spec(_spec06)
_spec06.loader.exec_module(t06)

DEFAULT_MODELS = "lr,rf,xgb,lgbm,et,svm,mlp_deep,tabnet"
DEFAULT_BOOTSTRAP = 1000
BONFERRONI_ALPHA = 0.05


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="模型两两统计显著性检验（Bootstrap + Wilcoxon + McNemar）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--train", type=Path, default=t06.DATA_DIR / "split_szz_train.csv")
    p.add_argument("--test", type=Path, default=t06.DATA_DIR / "split_szz_test.csv")
    p.add_argument("--features-raw", type=Path,
                   default=t06.DATA_DIR / "commit_features_raw.csv",
                   help="03 产出的原始特征表，用于取工作量（LOC）")
    p.add_argument("--models", default=DEFAULT_MODELS)
    p.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP,
                   help=f"bootstrap 重采样次数（默认 {DEFAULT_BOOTSTRAP}）")
    p.add_argument("--seed", type=int, default=t06.DEFAULT_SEED)
    p.add_argument("--report", type=Path, default=REPORTS_DIR / "statistical_test.md")
    return p.parse_args()


def bootstrap_indices(n: int, repeats: int, seed: int) -> np.ndarray:
    """产出 repeats × n 的重采样下标矩阵。

    **所有模型共用同一份下标** —— 这是配对比较成立的前提（见模块 docstring）。
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(repeats, n))


def metrics_point(proba: np.ndarray, y: np.ndarray, effort: np.ndarray) -> dict:
    """单次抽样下的三个指标：AUC / F1 / Recall@20%（工作量口径）。"""
    from sklearn.metrics import f1_score, roc_auc_score
    pred = (proba >= 0.5).astype(int)
    order = np.argsort(-proba, kind="stable")
    return {
        "auc": roc_auc_score(y, proba) if len(np.unique(y)) > 1 else np.nan,
        "f1": f1_score(y, pred, zero_division=0),
        "recall@20": t06.recall_at_effort(order, effort, y, 0.20),
    }


def mcnemar_exact(a_correct: np.ndarray, b_correct: np.ndarray) -> tuple[int, int, float]:
    """McNemar 精确检验：返回 (A对B错, B对A错, p)。

    只关心**不一致**的两格；一致的两格（都对 / 都错）不提供区分信息。
    样本量小时用精确二项检验，不用卡方近似。
    """
    n01 = int(np.sum(~a_correct & b_correct))  # A 错 B 对
    n10 = int(np.sum(a_correct & ~b_correct))  # A 对 B 错
    n = n01 + n10
    if n == 0:
        return n10, n01, 1.0
    p = binomtest(min(n10, n01), n, 0.5).pvalue
    return n10, n01, float(p)


def main() -> int:
    args = parse_args()
    for path in (args.train, args.test):
        if not path.exists():
            print("[16] 找不到切分文件：%s（先跑 05_split_dataset.py）" % path,
                  file=sys.stderr)
            return 2

    train = pd.read_csv(args.train)
    test = pd.read_csv(args.test)
    names = [m.strip() for m in args.models.split(",") if m.strip()]

    X_train = train[t06.FEATURE_FIELDS].to_numpy(dtype=float)
    y_train = train[t06.LABEL_COL].astype(int).to_numpy()
    X_test = test[t06.FEATURE_FIELDS].to_numpy(dtype=float)
    y_test = test[t06.LABEL_COL].astype(int).to_numpy()

    effort_df = t06.load_effort(args.features_raw, test["commit_hash"])
    effort = np.maximum(effort_df.to_numpy(dtype=float).ravel(), 1.0)

    n = len(y_test)
    idx = bootstrap_indices(n, args.bootstrap, args.seed)

    # ── 模型各训一次（固定种子），此后只重采样检验集 ──────────────────────
    probas: dict[str, np.ndarray] = {}
    for name in names:
        model = t06.build_model(name, args.seed)
        model.fit(X_train, y_train)
        probas[name] = model.predict_proba(X_test)[:, 1]

    # ── bootstrap：每个模型在同一份下标上重算指标 ────────────────────────
    boot: dict[str, dict[str, np.ndarray]] = {}
    for name in names:
        vals = {k: [] for k in ("auc", "f1", "recall@20")}
        for b in range(args.bootstrap):
            j = idx[b]
            if len(np.unique(y_test[j])) < 2:
                continue  # 该次抽样只剩单一类别，AUC 无定义，跳过（不填 0 冒充）
            m = metrics_point(probas[name][j], y_test[j], effort[j])
            for k in vals:
                vals[k].append(m[k])
        boot[name] = {k: np.asarray(v, dtype=float) for k, v in vals.items()}

    # ── 两两检验 ──────────────────────────────────────────────────────────
    pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
    n_pairs = len(pairs)
    alpha_bonf = BONFERRONI_ALPHA / n_pairs if n_pairs else BONFERRONI_ALPHA

    rows = []
    for a, b in pairs:
        for metric in ("auc", "f1", "recall@20"):
            va, vb = boot[a][metric], boot[b][metric]
            k = min(len(va), len(vb))
            if k < 10:
                continue
            va, vb = va[:k], vb[:k]
            diff = va - vb
            if np.allclose(diff, 0):
                p = 1.0
            else:
                p = float(wilcoxon(va, vb).pvalue)
            rows.append({
                "模型 A": a, "模型 B": b, "指标": metric,
                "A 均值": float(np.mean(va)), "B 均值": float(np.mean(vb)),
                "差（A-B）": float(np.mean(diff)),
                "差 95%CI 下": float(np.percentile(diff, 2.5)),
                "差 95%CI 上": float(np.percentile(diff, 97.5)),
                "Wilcoxon p": p,
                "Bonferroni 显著": "是" if p < alpha_bonf else "否",
            })

    # ── McNemar（阈值 0.5 的二值对错）────────────────────────────────────
    correct = {m: (probas[m] >= 0.5).astype(int) == y_test for m in names}
    mcn = []
    for a, b in pairs:
        n10, n01, p = mcnemar_exact(correct[a], correct[b])
        mcn.append({"模型 A": a, "模型 B": b,
                    "A对B错": n10, "B对A错": n01,
                    "McNemar p": p,
                    "Bonferroni 显著": "是" if p < alpha_bonf else "否"})

    render(args, test, names, boot, rows, mcn, alpha_bonf, n_pairs)
    print("[16] 报告已写出：%s" % args.report)
    return 0


def render(args, test, names, boot, rows, mcn, alpha_bonf, n_pairs) -> None:
    import joblib  # noqa: F401  (与 06 的依赖清单保持一致)
    import sklearn

    def f4(x: float) -> str:
        return "nan" if x != x else "%.4f" % x

    L: list[str] = []
    L.append("# 模型两两统计显著性检验\n")
    L.append("> 脚本：`data_model/16_statistical_test.py` ｜ 环境：conda `jit-defect`（不需要 torch）")
    L.append("> 口径来源：`design.md` D9、`docs/common/test-strategy.md` §1\n")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append("| 训练集 | `%s` —— %d 条 |" % (args.train.name, len(pd.read_csv(args.train))))
    L.append("| 检验集 | `%s` —— %d 条 |" % (args.test.name, len(test)))
    L.append("| 检验集正样本比例 | %.2f%% |" % (test[t06.LABEL_COL].mean() * 100))
    L.append("| 参与模型 | %s（%d 个） |" % ("、".join("`%s_v1`" % m for m in names), len(names)))
    L.append("| Bootstrap 次数 | %d |" % args.bootstrap)
    L.append("| 随机种子 | %d（固定，可复现） |" % args.seed)
    L.append("| 两两比较次数 | %d |" % n_pairs)
    L.append("| Bonferroni 阈值 | %.5f（= 0.05 / %d） |" % (alpha_bonf, n_pairs))
    L.append("")

    L.append("## 一、所测口径（先说清测的是什么）\n")
    L.append("| 检验 | 回答什么问题 | 配对方式 |")
    L.append("|---|---|---|")
    L.append("| Bootstrap | 指标有多不确定 | 模型各训一次（固定种子），只重采样检验集 |")
    L.append("| Wilcoxon signed-rank | A 与 B 的差是否系统性为正 | **同一组 bootstrap 下标**，保证配对 |")
    L.append("| McNemar（精确） | 阈值 0.5 下 A 判对的样本里 B 判错的是否显著更多 | 同一批提交的二值对错 |")
    L.append("")
    L.append("**不测什么（如实说明）**：本脚本只测**检验集抽样不确定性**，不测训练过程不确定性")
    L.append("（后者需 bootstrap 后重训，成本高一个量级）。论文两种做法都有，本组取前者并写明口径。\n")

    L.append("## 二、各模型指标分布（bootstrap）\n")
    L.append("| 模型 | AUC 均值 ± 标准差 | AUC 95% CI | F1 均值 ± 标准差 | Recall@20% 均值 ± 标准差 |")
    L.append("|---|---|---|---|---|")
    for m in names:
        a = boot[m]["auc"]
        L.append("| `%s_v1` | %.4f ± %.4f | [%.4f, %.4f] | %.4f ± %.4f | %.4f ± %.4f |" % (
            m, np.mean(a), np.std(a),
            np.percentile(a, 2.5), np.percentile(a, 97.5),
            np.mean(boot[m]["f1"]), np.std(boot[m]["f1"]),
            np.mean(boot[m]["recall@20"]), np.std(boot[m]["recall@20"])))
    L.append("")

    L.append("## 三、Wilcoxon signed-rank 两两检验\n")
    L.append("> 差 = A 均值 − B 均值；CI 为重采样差的 2.5% / 97.5% 分位；")
    L.append("> **Bonferroni 显著**列已按上表阈值校正，未校正的原始 p 值同时列出，不藏。")
    L.append("> ⚠️ **p 值被系统性压低，读结论前必读 §六**：出现大量相同的极小 p（如 3.326e-165）")
    L.append("> 不是 bug，而是「全部 bootstrap 差的符号一致」时检验统计量触顶的结果；")
    L.append("> 它反映的是**检验集固定**带来的过度自信，不是真实效应量。\n")
    L.append("| 模型 A | 模型 B | 指标 | A 均值 | B 均值 | 差（A-B） | 差 95%CI | Wilcoxon p | Bonferroni 显著 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x["指标"], x["Wilcoxon p"])):
        L.append("| `%s_v1` | `%s_v1` | %s | %s | %s | %s | [%s, %s] | %s | %s |" % (
            r["模型 A"], r["模型 B"], r["指标"],
            f4(r["A 均值"]), f4(r["B 均值"]), f4(r["差（A-B）"]),
            f4(r["差 95%CI 下"]), f4(r["差 95%CI 上"]),
            ("%.4g" % r["Wilcoxon p"]), r["Bonferroni 显著"]))
    L.append("")

    L.append("## 四、McNemar 检验（阈值 0.5 的二值决策）\n")
    L.append("| 模型 A | 模型 B | A 对 B 错 | B 对 A 错 | McNemar p | Bonferroni 显著 |")
    L.append("|---|---|---|---|---|---|")
    for r in sorted(mcn, key=lambda x: x["McNemar p"]):
        L.append("| `%s_v1` | `%s_v1` | %d | %d | %.4g | %s |" % (
            r["模型 A"], r["模型 B"], r["A对B错"], r["B对A错"],
            r["McNemar p"], r["Bonferroni 显著"]))
    L.append("")

    sig = [r for r in rows if r["Bonferroni 显著"] == "是"]
    L.append("## 五、结论与边界\n")
    L.append("- 经 Bonferroni 校正后**显著的指标对：%d 组**（共 %d 组）。" % (len(sig), len(rows)))
    if rows and len(sig) >= 0.9 * len(rows):
        L.append("")
        L.append("  ⚠️ **显著比例高达 %.0f%% —— 这个结果本身不正常，不要照单全收**。"
                 % (100.0 * len(sig) / len(rows)))
        L.append("  连 AUC 仅差千分之几的模型对也给出 p ≈ 1e-27，说明 p 值被系统性压低（见 §六），")
        L.append("  **不能据此宣称「所有模型两两都有真实差异」**。")
    if not sig:
        L.append("  → 即：**当前没有任何一对模型存在统计上显著的差异**。所有排名差异"
                 "都落在检验集抽样的噪声范围内。**这个结论必须如实讲，不能拿点估计排名当结论。**")
    L.append("- **边界**：① 只测检验集抽样不确定性，不含训练不确定性；② 只跑了 %d 条检验集样本；"
             "③ 工作量代理取 LOC（回溯 `commit_features_raw.csv`），换成改动文件数结论可能变化。"
             % len(test))
    L.append("- 本报告不改变交付模型；模型切换须另开提案（`model-coverage` R6）。\n")

    L.append("## 六、方法学局限（必读 —— 决定上面 p 值能不能直接用）\n")
    L.append("本脚本在**固定的**检验集上做 bootstrap 重采样。这是文献常见做法，但有一个**已知的失效方向**：\n")
    L.append("| 问题 | 说明 |")
    L.append("|---|---|")
    L.append("| **p 值系统性偏低（Type I 错误膨胀）** | 重采样只模拟了「检验集抽到哪些样本」，"
             "**没有**模拟「换一个检验集会怎样」，也没模拟训练不确定性。"
             "两个模型看的是同一批提交、同一份标签，差异跨重采样高度相关 → 方差被低估 → p 被压低 |")
    L.append("| **典型症状** | 出现大量**完全相同的极小 p**（如 3.326e-165）。"
             "这是「所有重采样的差符号一致」时统计量触顶，属**过度自信**而非真实效应 |")
    L.append("| **后果** | 按 §三 的表直接下结论，会得出「8 个模型两两都显著不同」——"
             "**这个结论不可信**，尤其对 AUC 只差千分之几的模型对 |")
    L.append("")
    L.append("**文献里的更保守做法（本组未采用，如实登记）**：")
    L.append("- **Nadeau & Bengio 校正的重采样 t 检验** —— 针对固定数据集上重采样检验的方差低估做修正；")
    L.append("- **5×2 交叉验证配对 t 检验（Dietterich）** —— 需要多次重划分，而 JIT 场景下切分必须按时间序，")
    L.append("  多次重划分会破坏时间约束，故本组**不采用**；")
    L.append("- **Bootstrap 后重训** —— 连训练一起重采样，代价高一个量级，Sprint 2 内不做。")
    L.append("")
    L.append("**因此本报告的正确用法**：")
    L.append("1. **不要**用 §三 的 p 值宣称模型优劣。**可用的是 §二 的分布与 §三 的差 + 95%CI** ——")
    L.append("   两者的差 CI 若不跨 0，说明差异在检验集抽样下是稳的。")
    L.append("2. 对 **AUC 差 < 0.01 的模型对**（具体数值由本报告 §二 在每次重跑后给出），")
    L.append("   结论只能是「**在当前检验集上无法区分**」，不得排序。")
    L.append("3. 答辩若被问到「你怎么证明 A 比 B 好」，正确答法是**引 §二 的 CI 重叠情况**，")
    L.append("   而不是引一个 1e-165 的 p 值 —— 后者会被追问方法学而答不上。\n")

    L.append("## 依赖版本（可复现）\n")
    L.append("```")
    L.append("scikit-learn==%s" % sklearn.__version__)
    L.append("```\n")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    # 与仓库既有 Markdown（LF）保持一致；newline 显式指定，不随平台
    args.report.write_text("\n".join(L), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
