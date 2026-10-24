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
# --from-saved 的探索性图表另起目录：旧权重复算的图不得覆盖重训产出的权威三张图
FIG_DIR_NAME_FROM_SAVED = FIG_DIR_NAME + "_from_saved"


def fig_dir_name(from_saved: bool = False) -> str:
    """图表目录名（报告正文与图片链接的唯一来源）。

    ``from_saved=True`` → ``figs_from_saved``；否则 ``figs``。
    ``train.py::fig_dir_for()`` 与 ``render()`` 都必须走这里，避免「图落 A 目录、
    报告链接写 B 目录」导致探索性报告展示权威图或断图（评审第三轮阻断项）。
    """
    return FIG_DIR_NAME_FROM_SAVED if from_saved else FIG_DIR_NAME


def _roc_ax(ax, y, probas: dict, title):
    for name, proba in probas.items():
        fpr, tpr, _ = roc_curve(y, proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={float(_trapz(tpr, fpr)):.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title); ax.legend(fontsize=8); ax.grid(alpha=0.3)


def make_charts(results: dict, probas: dict, y: np.ndarray,
                effort_loc: np.ndarray, out_dir: Path) -> list[Path]:
    # 绘图依赖延迟导入：只出 Markdown（render）时不要求装 matplotlib
    import matplotlib
    matplotlib.use("Agg")      # 无显示环境也能出图
    import matplotlib.pyplot as plt

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
             "budget": f"budget-aware (LOC>={config.MIN_REVIEW_LOC}, density)",
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
        orders = [("model", np.argsort(-probas[name], kind="stable"))]
        if "budget" in eff:
            orders.append(("budget", budget_order(
                probas[name], effort, config.EFFORT_REVIEW_FLOORS["LOC（改动行数 la+ld）"])))
        orders.append(("density", np.argsort(-(probas[name] / effort), kind="stable")))
        for key, order in orders:
            xs, ys = cumulative_curve(order, effort, y)
            ax.plot(xs, ys, linestyle=style[key], label=label[key], color=color[key],
                    lw=1.4 if key != "density" else 1.1)
        ax.plot(rand_xs, rand_ys, linestyle=style["random"], label=label["random"],
                color=color["random"], lw=0.9)
        ax.plot(opt_xs, opt_ys, linestyle=style["optimal"], label=label["optimal"],
                color=color["optimal"], lw=0.9)
        ax.set_title("{}  P_norm  {:.2f} / {:.2f} / {:.2f}".format(
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
    # 图表目录跟着口径走：--from-saved 的报告只链接 figs_from_saved/，
    # 否则探索性报告会指向重训产出的权威图（评审第三轮阻断项）
    fig_dir = fig_dir_name(getattr(args, "from_saved", False))
    lines = [
        "# expert 线模型评估指标（pipelines/expert/train.py 产出）\n",
        ("> baseline（Kamei 14 特征）。指标口径与 `data_model/06_train_model.py` 逐字一致；\n"
         f"> 本文件与同目录 `{fig_dir}/` 图表可入库，供四线横向对比。\n"),
    ]
    if getattr(args, "from_saved", False):
        lines.append("> **探索性结果（非权威指标）**：本次由 `--from-saved` 读取 `models/*.pkl` "
                     "复算重生成，未重训、未重算 SHAP（第三节显示「未实测」）。\n"
                     "> 这些权重的训练数据版本未随文件记录，无法证明与当前检验集无重叠；"
                     "**权威指标以重训产出为准**（`model_metrics.md`）。\n")
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
        lines.append(f"| **模型排序**（契约三当前口径） | `{r['model_name']}` | {m['area']:.4f} | "
                     f"**{m['p_norm']:.4f}** | {m['recall@20']:.4f} | {m['recall@50']:.4f} | "
                     f"{m['n_commits@20']} |\n")
        b = r["effort"]["LOC（改动行数 la+ld）"].get("budget")
        if b is not None:
            lines.append(f"| **预算感知**：LOC ≥ {config.MIN_REVIEW_LOC} 内按 "
                         f"`risk_score / 工作量` 降序 | `{r['model_name']}` | {b['area']:.4f} | "
                         f"**{b['p_norm']:.4f}** | {b['recall@20']:.4f} | {b['recall@50']:.4f} | "
                         f"{b['n_commits@20']} |\n")
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append(f"| 对照：按 `risk_score / 工作量` 降序（无下限） | `{r['model_name']}` | "
                     f"{d['area']:.4f} | **{d['p_norm']:.4f}** | {d['recall@20']:.4f} | "
                     f"{d['recall@50']:.4f} | {d['n_commits@20']} |\n")
    o = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["optimal"]
    r_ = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["random"]
    lines.append(f"| 上界：真实缺陷密度降序 | — | {o['area']:.4f} | {o['p_norm']:.4f} | "
                 f"{o['recall@20']:.4f} | {o['recall@50']:.4f} | {o['n_commits@20']} |\n")
    lines.append(f"| 基线：随机排序（{r_['repeats']} 次均值） | — | {r_['area']:.4f} ± "
                 f"{r_['area_std']:.4f} | {r_['p_norm']:.4f} | {r_['recall@20']:.4f} | — | — |\n")
    lines.append("\n> 随机基线应落在 0.5 附近 —— 它是面积算法的自我校验。\n")
    # 读法：结论必须由本轮结果算出来，不能写死（评审意见 #4）：
    # `--models` 支持子集、数据也可能是别的切分，硬编码「全为负 / 最低出自 svm」会说谎。
    LOC = "LOC（改动行数 la+ld）"
    per_model = [(name, r) for name, r in results.items() if LOC in r.get("effort", {})]
    if per_model:
        pns = {name: r["effort"][LOC]["model"]["p_norm"] for name, r in per_model}
        confs = {name: r["effort"][LOC]["confound"]["spearman_risk_log_effort"]
                 for name, r in per_model}
        ms = [r["effort"][LOC]["model"] for _, r in per_model]
        bs = [r["effort"][LOC]["budget"] for _, r in per_model if "budget" in r["effort"][LOC]]
        ds = [r["effort"][LOC]["density"] for _, r in per_model]
        n_neg = sum(1 for v in pns.values() if v < 0)
        worst = min(pns, key=lambda k: pns[k])
        rho_vals = sorted(confs.values())
        rho_med = float(np.median(rho_vals))
        rho_lo, rho_hi = rho_vals[0], rho_vals[-1]
        median_loc = per_model[0][1]["effort"][LOC]["confound"]["median_effort"]

        worst_txt = "即全为负" if n_neg == len(pns) else f"最低为 `{worst}`（{pns[worst]:.3f}）"
        head = (f"\n> **模型排序一列的表现**：{n_neg}/{len(pns)} 个模型的 `P_norm` 为负"
                f"（{worst_txt}）。")
        rho_txt = (f"`risk_score` 与提交规模的 Spearman ρ 在 {rho_lo:.3f}~{rho_hi:.3f}（中位数 {rho_med:.3f}）")
        if n_neg:
            n_lo, n_hi = (min(m["n_commits@20"] for m in ms),
                          max(m["n_commits@20"] for m in ms))
            rec_lo, rec_hi = (100 * min(m["recall@20"] for m in ms),
                              100 * max(m["recall@20"] for m in ms))
            head += (rho_txt + "，越接近 1 越说明分数在预测「提交有多大」；"
                     f"按 `risk_score` 降序就等于先审最大的提交：20% LOC 预算只审到 "
                     f"{n_lo}~{n_hi} 条，召回 {rec_lo:.2f}%~{rec_hi:.2f}%，"
                     f"随机基线 {100 * r_['recall@20']:.2f}%。\n>\n")
        else:
            head += (rho_txt + "；本轮回填的模型排序不低于随机基线，"
                     "说明这批判分与提交规模的耦合不足以拖垮 effort-aware 指标。\n>\n")

        if bs:
            b_lo, b_hi = (min(b["n_commits@20"] for b in bs), max(b["n_commits@20"] for b in bs))
            br_lo = 100 * min(b["recall@20"] for b in bs)
            br_hi = 100 * max(b["recall@20"] for b in bs)
            bp_lo, bp_hi = (min(b["p_norm"] for b in bs), max(b["p_norm"] for b in bs))
            d_lo, d_hi = (min(d["n_commits@20"] for d in ds), max(d["n_commits@20"] for d in ds))
            dr_lo = 100 * min(d["recall@20"] for d in ds)
            dr_hi = 100 * max(d["recall@20"] for d in ds)
            dp_lo, dp_hi = (min(d["p_norm"] for d in ds), max(d["p_norm"] for d in ds))
            cost = (f"**两种改法都要看成本**：预算感知（LOC ≥ {config.MIN_REVIEW_LOC} 再按密度）"
                    f"审 {b_lo}~{b_hi} 条，召回 {br_lo:.2f}%~{br_hi:.2f}%"
                    f"（P_norm {bp_lo:.3f}~{bp_hi:.3f}）；无下限的纯密度排序审 {d_lo}~{d_hi} 条，"
                    f"召回 {dr_lo:.2f}%~{dr_hi:.2f}%（P_norm {dp_lo:.3f}~{dp_hi:.3f}）。"
                    f"后者指标更高，代价是把预算摊到大量小提交"
                    f"（本轮检验集中位 LOC = {median_loc} 行）上，不是真实评审节奏。\n>\n")
        else:
            cost = ("**预算感知列未启用**：本次调用未给 `review_floor`，只报模型排序与纯密度两种口径。\n>\n")
        lines.append(head + cost +
                     "> 负 `P_norm` 属**排序口径**问题（契约三 Issue #37），不是模型判别力问题；"
                     "主口径仍按契约三保留 `risk_score` 降序，切换口径走提案，不在本报告里静默改。\n")
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
        lines.append(f"![{fig}]({fig_dir}/{fig}.png)\n\n")
    return "".join(lines)
