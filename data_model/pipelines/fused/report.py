"""fused 线结果报告：Markdown + 图表（命名与 expert / semantic 一致）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# numpy>=2.4 移除了 np.trapz，改用 np.trapezoid；老版本回退
try:
    _trapz = np.trapezoid
except AttributeError:  # numpy < 2.0
    _trapz = np.trapz
from sklearn.metrics import roc_curve

from .. import text_source
from . import config
from .metrics import cumulative_curve

FIG_DIR_NAME = "figs"


def _roc_ax(ax, y, probas, title):
    for name, proba in probas.items():
        fpr, tpr, _ = roc_curve(y, proba)
        ax.plot(fpr, tpr, label="%s (AUC=%.3f)" % (name, float(_trapz(tpr, fpr))))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title); ax.legend(fontsize=8); ax.grid(alpha=0.3)


def make_charts(results, probas, y, effort_loc, out_dir: Path) -> list[Path]:
    # 绘图依赖延迟导入：只出 Markdown（render）时不要求装 matplotlib
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    fig, ax = plt.subplots(figsize=(6, 5))
    _roc_ax(ax, y, probas, "ROC curves - fused (Kamei14 + semantic)")
    p = out_dir / "roc_curves.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
    first = next(iter(results))
    proba = probas[first]
    fig, ax = plt.subplots(figsize=(6, 5))
    for key, lbl, order in (
            ("model", "model (risk_score desc)", np.argsort(-proba, kind="stable")),
            ("density", "density (score/effort)", np.argsort(-(proba / effort), kind="stable")),
            ("optimal", "optimal (oracle)", np.argsort(-(y / effort), kind="stable"))):
        xs, ys = cumulative_curve(order, effort, y)
        ax.plot(xs, ys, "-" if key == "model" else "--" if key == "density" else ":",
                label=lbl)
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    xs, ys = cumulative_curve(rng.permutation(len(y)), effort, y)
    ax.plot(xs, ys, "-.", label="random baseline")
    ax.set_xlabel("Cumulative effort fraction"); ax.set_ylabel("Cumulative recall")
    ax.set_title(f"Effort-aware curves - fused (LOC, model={first})")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    p = out_dir / "effort_curves_loc.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    names = list(results)
    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * len(names)), 4.5))
    ax.bar(x - w / 2, [results[n]["auc"] for n in names], w, label="AUC")
    ax.bar(x + w / 2, [results[n]["f1"] for n in names], w, label="F1")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylim(0, 1); ax.set_title("AUC / F1 - fused"); ax.legend()
    ax.grid(alpha=0.3, axis="y")
    p = out_dir / "metric_bars.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)
    return written


def render(args, results, n_train, n_test, y_test, coverage=None, text_stats=None) -> str:
    lines = [
        f"# fused 线模型评估指标（Kamei14 ⊕ 语义 768 = {config.EXPECTED_DIM} 维 → 12 分类器）\n",
        "> 对照线：同切分、同分类器族、同指标口径；特征 = 专家特征 + 语义向量拼接。\n",
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        f"| 输入维度 | {config.EXPECTED_DIM}（Kamei 14 + 语义 768） |\n",
        f"| 语义缓存 | `{config.EMBEDDINGS_NPZ}` |\n",
        f"| 训练/检验 | {n_train} / {n_test} 条（共享切分，内连接对齐） |\n",
    ]
    if coverage:
        lines.append(
            "| 语义覆盖率 | 训练 {:.2f}% / 检验 {:.2f}%（内连接后保留比例，低于 100% 需说明缺失原因） |\n".format(coverage["train"], coverage["test"]))
    lines += [
        "| 检验集正样本比例 | %.2f%% |\n" % (y_test.mean() * 100),
        f"| 随机种子 | `{args.seed}` |\n",
        f"| 判定阈值 | {config.DECISION_THRESHOLD} |\n",
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
    ]
    for r in results.values():
        lines.append("| `{}`（{}） | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(
            r["model_name"], r["label"], r["auc"], r["f1"],
            r["precision"], r["recall"], r["accuracy"]))
    lines.append("\n## 二、Effort-aware 指标（检验集，LOC 工作量代理）\n\n"
                 "| 排序方式 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n"
                 "|---|---|---|---|---|---|\n")
    for r in results.values():
        m = r["effort"]["LOC（改动行数 la+ld）"]["model"]
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append("| **模型排序** | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(r["model_name"], m["area"], m["p_norm"], m["recall@20"], m["recall@50"]))
        lines.append("| 对照：密度排序 | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(r["model_name"], d["area"], d["p_norm"], d["recall@20"], d["recall@50"]))
    first = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]
    optimal, random = first["optimal"], first["random"]
    lines.append(f"| 上界：真实密度 | — | {optimal['area']:.4f} | {optimal['p_norm']:.4f} | {optimal['recall@20']:.4f} | {optimal['recall@50']:.4f} |\n"
                 f"| 基线：随机（{random['repeats']} 次均值） | — | {random['area']:.4f} ± {random['area_std']:.4f} | {random['p_norm']:.4f} | — | — |\n")
    lines.append("\n## 融合对照读法\n\n")
    lines.append("> 三方并排：expert（14 维）/ semantic（768 维）/ fused（782 维）。"
                 "fused 优于两者 = 两模态互补；只与 expert 持平 = 语义无增量（如实登记）。\n")
    if coverage and (coverage["train"] < 100.0 or coverage["test"] < 100.0):
        lines.append("\n> ⚠ **样本口径警告**：本线语义覆盖率不足 100%（内连接丢了行），"
                     "与 expert / semantic / e2e 的样本集合不同，**指标不可直接并排比较**；"
                     "要并排请先让语义缓存覆盖全部切分内提交，再重跑本线。\n")
    lines.append("\n")
    if text_stats:
        lines.extend(text_source.registration_lines(
            text_stats["counts"], text_stats["n_total"], text_stats.get("positives")))
        lines.append("\n")
        lines.extend(text_source.robustness_lines(
            text_stats["kept"], text_stats["dropped"], text_stats.get("deltas"),
            text_stats.get("retrained", False)))
    else:
        lines.append("## 文本来源与覆盖率\n\n"
                     "> **未登记**：语义缓存没有 `text_source` 键（旧版缓存），不按 `diff` 冒充。"
                     "由 semantic 线重跑 `train.py --force-encode` 生成新缓存后本段自动出现。\n")
    lines.append("\n## 图表\n\n")
    for fig in ("roc_curves", "effort_curves_loc", "metric_bars"):
        lines.append(f"![{fig}](figs/{fig}.png)\n\n")
    return "".join(lines)
