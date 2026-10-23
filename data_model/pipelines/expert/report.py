"""expert 线结果报告：Markdown 表格 + matplotlib 图表（reports/figs/）。

图表统一命名（四条线一致，便于横向对比）：
  figs/roc_curves.png         各模型 ROC
  figs/effort_curves_loc.png  累计召回 ~ 累计工作量（LOC 代理，每模型一格 × 四种排序）
  figs/metric_bars.png        AUC / F1 柱状对比
图表内文字用英文 —— matplotlib 默认字体不含中文，避免乱码。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# numpy>=2.4 移除了 np.trapz，改用 np.trapezoid；老版本回退
try:
    _trapz = np.trapezoid
except AttributeError:  # numpy < 2.0
    _trapz = np.trapz
from sklearn.metrics import roc_curve

from . import config
from .metrics import budget_order, cumulative_curve

FIG_DIR_NAME = "figs"


def _roc_ax(ax, y, probas: dict, title):
    for name, proba in probas.items():
        fpr, tpr, _ = roc_curve(y, proba)
        ax.plot(fpr, tpr, label="%s (AUC=%.3f)" % (name, float(_trapz(tpr, fpr))))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title); ax.legend(fontsize=8); ax.grid(alpha=0.3)


def make_charts(results: dict, probas: dict, y: np.ndarray,
                effort_loc: np.ndarray, out_dir: Path) -> list[Path]:
    # 绘图依赖延迟导入：只出 Markdown（render）时不要求装 matplotlib
    import matplotlib
    matplotlib.use("Agg")      # 无显示环境也能出图
    import matplotlib.pyplot as plt  # noqa: F401  (供本函数内使用)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # 1) ROC
    fig, ax = plt.subplots(figsize=(6, 5))
    _roc_ax(ax, y, probas, "ROC curves (test set)")
    p = out_dir / "roc_curves.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    # 2) Effort 曲线（LOC 代理；每个模型一格，两种排序 + 上界/随机示意）
    #    为什么不全画在一张：8 条线的 model 排序几乎重合，混在一起看不出差别；
    #    分格后每格都能读到「risk_score 降序 vs 风险密度降序」两条曲线的落差。
    effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
    style = {"model": "-", "budget": "--", "density": "-.", "optimal": ":", "random": (0, (1, 2))}
    label = {"model": "model (risk_score desc)",
             "budget": "budget-aware (LOC>=%d, density)" % config.MIN_REVIEW_LOC,
             "density": "density (score/effort, no floor)",
             "optimal": "optimal (oracle)", "random": "random baseline"}
    color = {"model": "#1f77b4", "budget": "#9467bd", "density": "#ff7f0e",
             "optimal": "#2ca02c", "random": "#d62728"}
    names = list(results)
    ncol = 4
    nrow = max(1, -(-len(names) // ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 3.0 * nrow + 0.6),
                             sharex=True, sharey=True, squeeze=False)
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    rand_xs, rand_ys = cumulative_curve(rng.permutation(len(y)), effort, y)
    opt_xs, opt_ys = cumulative_curve(np.argsort(-(y / effort), kind="stable"), effort, y)
    for i, name in enumerate(names):
        ax = axes[i // ncol][i % ncol]
        eff = results[name]["effort"]["LOC（改动行数 la+ld）"]
        for key, order in (("model", np.argsort(-probas[name], kind="stable")),
                           ("budget", budget_order(probas[name], effort)),
                           ("density", np.argsort(-(probas[name] / effort), kind="stable"))):
            xs, ys = cumulative_curve(order, effort, y)
            ax.plot(xs, ys, linestyle=style[key], label=label[key], color=color[key],
                    lw=1.4 if key != "density" else 1.1)
        ax.plot(rand_xs, rand_ys, linestyle=style["random"], label=label["random"],
                color=color["random"], lw=0.9)
        ax.plot(opt_xs, opt_ys, linestyle=style["optimal"], label=label["optimal"],
                color=color["optimal"], lw=0.9)
        ax.set_title("%s  P_norm  %.2f / %.2f / %.2f" % (
            name, eff["model"]["p_norm"], eff["budget"]["p_norm"], eff["density"]["p_norm"]),
            fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
        if i // ncol == nrow - 1:
            ax.set_xlabel("Cumulative effort fraction", fontsize=9)
        if i % ncol == 0:
            ax.set_ylabel("Cumulative recall", fontsize=9)
    for j in range(len(names), nrow * ncol):
        axes[j // ncol][j % ncol].axis("off")
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.005),
               ncol=5, fontsize=7.5, frameon=False)
    fig.suptitle("Effort-aware curves (LOC proxy, test set) — "
                 "P_norm = risk desc / budget-aware / density", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.07, 1, 0.96))
    p = out_dir / "effort_curves_loc.png"; fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    # 3) AUC / F1 柱状
    names = list(results)
    auc = [results[n]["auc"] for n in names]
    f1 = [results[n]["f1"] for n in names]
    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * len(names)), 4.5))
    ax.bar(x - w / 2, auc, w, label="AUC")
    ax.bar(x + w / 2, f1, w, label="F1")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylim(0, 1); ax.set_title("AUC / F1 by model (test set)")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    p = out_dir / "metric_bars.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)
    return written


def render(args, train, test, results) -> str:
    y_test = test[config.LABEL_COL].astype(int).to_numpy()
    lines = [
        "# expert 线模型评估指标（pipelines/expert/train.py 产出）\n",
        ("> baseline（Kamei 14 特征）。指标口径与 `data_model/06_train_model.py` 逐字一致；\n"
         "> 本文件与同目录 `figs/` 图表可入库，供四线横向对比。\n"),
    ]
    if getattr(args, "from_saved", False):
        lines.append("> 本次由 `--from-saved` 读取 `models/*.pkl` 复算重生成（未重训、未重算 SHAP，"
                     "故第三节显示「未实测」）；\n"
                     "> 切分为当前 `split_szz_*.csv`，与 06 时代的 7,625 / 3,268 切分不可直接比较。\n")
    lines += [
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        f"| 训练集 | `{args.train.name}` —— {len(train)} 条 |\n",
        f"| 检验集 | `{args.test.name}` —— {len(test)} 条 |\n",
        "| 特征列 | 契约二第三节 14 项（顺序即交付清单顺序） |\n",
        "| 标签 | `szz`（`is_bug_inducing`） |\n",
        f"| 训练/检验正样本比例 | {train[config.LABEL_COL].mean() * 100:.2f}% / {y_test.mean() * 100:.2f}%（时间序切分的自然差，非 bug） |\n",
        f"| 随机种子 | `{args.seed}` |\n",
        f"| 判定阈值 | {config.DECISION_THRESHOLD}（服务端常量） |\n",
        "| 检验集时间范围 | {} ~ {} |\n".format(test["committed_at"].iloc[0],
                                          test["committed_at"].iloc[-1]),
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
    ]
    for name, r in results.items():
        lines.append("| `{}`（{}） | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(
            r["model_name"], r["label"], r["auc"], r["f1"],
            r["precision"], r["recall"], r["accuracy"]))
    lines.append("\n## 二、Effort-aware 指标（检验集，LOC 工作量代理）\n\n")
    lines.append("> 文献口径对照：`P_norm` 即 **Popt**（Mende & Koschke, CSMR 2010，"
                 "`Popt = 1 − Δopt`，按「最优 − 随机」归一）；`Recall@20%` 即 **CE@20%**"
                 "（20-80 原则）。ALPA 未获可核验定义，**不实现、登记待补**。\n\n")
    lines.append("| 排序方式 | 模型 | 曲线下面积 | **P_norm（=Popt）** | Recall@20%（=CE@20%） | Recall@50% | 20% 预算审到的条数 |\n"
                 "|---|---|---|---|---|---|---|\n")
    for name, r in results.items():
        m = r["effort"]["LOC（改动行数 la+ld）"]["model"]
        lines.append("| **模型排序**（契约三当前口径） | `%s` | %.4f | **%.4f** | %.4f | %.4f | %d |\n"
                     % (r["model_name"], m["area"], m["p_norm"], m["recall@20"], m["recall@50"],
                        m["n_commits@20"]))
        b = r["effort"]["LOC（改动行数 la+ld）"]["budget"]
        lines.append("| **预算感知**：LOC ≥ %d 内按 `risk_score / 工作量` 降序 | `%s` | %.4f | **%.4f** | %.4f | %.4f | %d |\n"
                     % (config.MIN_REVIEW_LOC, r["model_name"], b["area"], b["p_norm"],
                        b["recall@20"], b["recall@50"], b["n_commits@20"]))
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append("| 对照：按 `risk_score / 工作量` 降序（无下限） | `%s` | %.4f | **%.4f** | %.4f | %.4f | %d |\n"
                     % (r["model_name"], d["area"], d["p_norm"], d["recall@20"], d["recall@50"],
                        d["n_commits@20"]))
    o = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["optimal"]
    r_ = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["random"]
    lines.append("| 上界：真实缺陷密度降序 | — | %.4f | %.4f | %.4f | %.4f | %d |\n"
                 % (o["area"], o["p_norm"], o["recall@20"], o["recall@50"], o["n_commits@20"]))
    lines.append("| 基线：随机排序（%d 次均值） | — | %.4f ± %.4f | %.4f | %.4f | — | — |\n"
                 % (r_["repeats"], r_["area"], r_["area_std"], r_["p_norm"], r_["recall@20"]))
    lines.append("\n> 随机基线应落在 0.5 附近 —— 它是面积算法的自我校验。\n")
    # 读法：把「P_norm 为负」归因到排序口径而不是模型判别力，给出可核验的数字
    confs = [r["effort"]["LOC（改动行数 la+ld）"]["confound"]["spearman_risk_log_effort"]
             for r in results.values()]
    ms = [r["effort"]["LOC（改动行数 la+ld）"]["model"] for r in results.values()]
    bs = [r["effort"]["LOC（改动行数 la+ld）"]["budget"] for r in results.values()]
    ds = [r["effort"]["LOC（改动行数 la+ld）"]["density"] for r in results.values()]
    lines.append(
        "\n> **为什么「模型排序」一列全是负的**：`risk_score` 与提交规模强相关"
        "（Spearman ρ 中位数 %.3f，最低 %.3f 出自 `svm` —— 它的概率被 Platt 压缩、"
        "对规模不敏感；其余模型 0.85 上下），越接近 1 越说明分数基本在预测「提交有多大」。"
        "按 `risk_score` 降序 = 先审最大的提交：20%% LOC 预算只审到 %d~%d 条，"
        "召回 %.2f%%~%.2f%%，**低于随机基线 %.2f%%**。\n>\n"
        "> **两种改法都要看成本**：预算感知（LOC ≥ %d 再按密度）审 %d~%d 条，"
        "召回 %.2f%%~%.2f%%（P_norm %.3f~%.3f）；无下限的纯密度排序审 %d~%d 条，"
        "召回 %.2f%%~%.2f%%（P_norm %.3f~%.3f）—— 后者指标更高，代价是把预算摊到"
        "两万多条 8 行提交上，不是真实评审节奏。\n>\n"
        "> 所以负 `P_norm` 是**排序口径**问题（契约三 Issue #37），不是模型判别力问题。"
        "主口径仍按契约三保留 `risk_score` 降序；口径是否切换走提案，不在本报告里静默改。\n"
        % (float(np.median(confs)), min(confs),
           min(m["n_commits@20"] for m in ms), max(m["n_commits@20"] for m in ms),
           100 * min(m["recall@20"] for m in ms), 100 * max(m["recall@20"] for m in ms),
           100 * r_["recall@20"],
           config.MIN_REVIEW_LOC,
           min(b["n_commits@20"] for b in bs), max(b["n_commits@20"] for b in bs),
           100 * min(b["recall@20"] for b in bs), 100 * max(b["recall@20"] for b in bs),
           min(b["p_norm"] for b in bs), max(b["p_norm"] for b in bs),
           min(d["n_commits@20"] for d in ds), max(d["n_commits@20"] for d in ds),
           100 * min(d["recall@20"] for d in ds), 100 * max(d["recall@20"] for d in ds),
           min(d["p_norm"] for d in ds), max(d["p_norm"] for d in ds)))
    lines.append("\n## 三、SHAP 单条解释耗时（实测，随机器负载波动）\n\n")
    lines.append(f"| 模型 | p50 | p95 | 最大 | 是否满足 95% < {config.LATENCY_BUDGET_MS} ms |\n|---|---|---|---|---|\n")
    for name, r in results.items():
        s = r.get("shap", {})
        if "p95_ms" in s:
            ok = "满足" if s["p95_ms"] < config.LATENCY_BUDGET_MS else "**不满足**"
            lines.append("| `{}` | {:.1f} ms | {:.1f} ms | {:.1f} ms | {} |\n".format(name, s["p50_ms"], s["p95_ms"], s["max_ms"], ok))
        else:
            lines.append("| `{}` | — | — | — | {} |\n".format(name, s.get("skipped", s.get("error", "未实测")).replace("|", "/")))
    lines.append("\n## 图表\n\n")
    for fig in ("roc_curves", "effort_curves_loc", "metric_bars"):
        lines.append(f"![{fig}](figs/{fig}.png)\n\n")
    return "".join(lines)
