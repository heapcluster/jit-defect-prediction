"""semantic 线结果报告：Markdown + 图表（命名与 expert 线一致，便于横向对比）。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_curve

from . import config
from .metrics import cumulative_curve

FIG_DIR_NAME = "figs"


def _roc_ax(ax, y, probas, title):
    for name, proba in probas.items():
        fpr, tpr, _ = roc_curve(y, proba)
        ax.plot(fpr, tpr, label="%s (AUC=%.3f)" % (name, float(np.trapz(tpr, fpr))))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title); ax.legend(fontsize=8); ax.grid(alpha=0.3)


def make_charts(results, probas, y, effort_loc, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    fig, ax = plt.subplots(figsize=(6, 5))
    _roc_ax(ax, y, probas, "ROC curves - semantic (frozen CodeBERT)")
    p = out_dir / "roc_curves.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
    first = next(iter(results))
    fig, ax = plt.subplots(figsize=(6, 5))
    proba = probas[first]
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
    ax.set_title("Effort-aware curves - semantic (LOC, model=%s)" % first)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    p = out_dir / "effort_curves_loc.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    names = list(results)
    x = np.arange(len(names)); w = 0.38
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * len(names)), 4.5))
    ax.bar(x - w / 2, [results[n]["auc"] for n in names], w, label="AUC")
    ax.bar(x + w / 2, [results[n]["f1"] for n in names], w, label="F1")
    ax.set_xticks(x); ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylim(0, 1); ax.set_title("AUC / F1 - semantic"); ax.legend()
    ax.grid(alpha=0.3, axis="y")
    p = out_dir / "metric_bars.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)
    return written


def render(args, results, n_train, n_test, y_test) -> str:
    lines = [
        "# semantic 线模型评估指标（冻结 CodeBERT 768 维 → 8 分类器）\n",
        "> 对照线：与 expert 线同切分、同分类器族、同指标口径；唯一变量是特征模态。\n",
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        "| 编码器 | `%s`（冻结，mean-pool） |\n" % config.TEXT_MODEL,
        "| 向量维度 | 768 |\n",
        "| 训练/检验 | %d / %d 条（共享切分 `split_szz_*.csv`） |\n" % (n_train, n_test),
        "| 检验集正样本比例 | %.2f%% |\n" % (y_test.mean() * 100),
        "| 随机种子 | `%d` |\n" % args.seed,
        "| 判定阈值 | %s |\n" % config.DECISION_THRESHOLD,
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
    ]
    for name, r in results.items():
        lines.append("| `%s`（%s） | %.4f | %.4f | %.4f | %.4f | %.4f |\n" % (
            r["model_name"], r["label"], r["auc"], r["f1"],
            r["precision"], r["recall"], r["accuracy"]))
    lines.append("\n## 二、Effort-aware 指标（检验集，LOC 工作量代理）\n\n"
                 "| 排序方式 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n"
                 "|---|---|---|---|---|---|\n")
    for name, r in results.items():
        m = r["effort"]["LOC（改动行数 la+ld）"]["model"]
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append("| **模型排序** | `%s` | %.4f | **%.4f** | %.4f | %.4f |\n"
                     % (r["model_name"], m["area"], m["p_norm"], m["recall@20"], m["recall@50"]))
        lines.append("| 对照：密度排序 | `%s` | %.4f | **%.4f** | %.4f | %.4f |\n"
                     % (r["model_name"], d["area"], d["p_norm"], d["recall@20"], d["recall@50"]))
    first = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]
    lines.append("| 上界：真实密度 | — | %.4f | %.4f | %.4f | %.4f |\n| 基线：随机（%d 次均值） | — | %.4f ± %.4f | %.4f | — | — |\n"
                 % (first["optimal"]["area"], first["optimal"]["p_norm"],
                    first["optimal"]["recall@20"], first["optimal"]["recall@50"],
                    first["random"]["repeats"], first["random"]["area"],
                    first["random"]["area_std"], first["random"]["p_norm"]))
    lines.append("\n## 与 baseline 对照（读法）\n\n")
    lines.append("> 把本表与 `pipelines/expert/reports/model_metrics.md` 并排：AUC 高出多少 = "
                 "纯语义模态的增益；若不升反降，如实登记，不选择性只报更好的一组。\n")
    lines.append("\n## 图表\n\n")
    for fig in ("roc_curves", "effort_curves_loc", "metric_bars"):
        lines.append("![%s](figs/%s.png)\n\n" % (fig, fig))
    return "".join(lines)
