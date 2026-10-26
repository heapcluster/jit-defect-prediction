"""semantic 线结果报告：Markdown + 图表（命名与 expert 线一致，便于横向对比）。"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
        ax.plot(fpr, tpr, label=f"{name} (AUC={float(_trapz(tpr, fpr)):.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def make_charts(results, probas, y, effort_loc, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    fig, ax = plt.subplots(figsize=(6, 5))
    _roc_ax(ax, y, probas, "ROC curves - semantic (frozen CodeBERT)")
    p = out_dir / "roc_curves.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
    first = next(iter(results))
    fig, ax = plt.subplots(figsize=(6, 5))
    proba = probas[first]
    for key, lbl, order in (
        ("model", "model (risk_score desc)", np.argsort(-proba, kind="stable")),
        ("density", "density (score/effort)", np.argsort(-(proba / effort), kind="stable")),
        ("optimal", "optimal (oracle)", np.argsort(-(y / effort), kind="stable")),
    ):
        xs, ys = cumulative_curve(order, effort, y)
        ax.plot(xs, ys, "-" if key == "model" else "--" if key == "density" else ":", label=lbl)
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    xs, ys = cumulative_curve(rng.permutation(len(y)), effort, y)
    ax.plot(xs, ys, "-.", label="random baseline")
    ax.set_xlabel("Cumulative effort fraction")
    ax.set_ylabel("Cumulative recall")
    ax.set_title(f"Effort-aware curves - semantic (LOC, model={first})")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    p = out_dir / "effort_curves_loc.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)

    names = list(results)
    x = np.arange(len(names))
    w = 0.38
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * len(names)), 4.5))
    ax.bar(x - w / 2, [results[n]["auc"] for n in names], w, label="AUC")
    ax.bar(x + w / 2, [results[n]["f1"] for n in names], w, label="F1")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylim(0, 1)
    ax.set_title("AUC / F1 - semantic")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    p = out_dir / "metric_bars.png"
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    written.append(p)
    return written


def render(args, results, n_train, n_test, y_test, text_stats=None) -> str:
    lines = [
        # 分类器数量按本次实际训练的模型数动态写，避免「默认 8 个、标题却写 12」的漂移
        f"# semantic 线模型评估指标（冻结 CodeBERT 768 维 → {len(results)} 分类器）\n",
        "> 对照线：与 expert 线同切分、同分类器族、同指标口径；唯一变量是特征模态。\n",
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        f"| 编码器 | `{config.TEXT_MODEL}`（冻结，mean-pool） |\n",
        "| 向量维度 | 768 |\n",
        f"| 训练/检验 | {n_train} / {n_test} 条（共享切分 `split_szz_*.csv`） |\n",
        "| 检验集正样本比例 | %.2f%% |\n" % (y_test.mean() * 100),
        f"| 随机种子 | `{args.seed}` |\n",
        f"| 判定阈值 | {config.DECISION_THRESHOLD} |\n",
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
    ]
    for r in results.values():
        lines.append(
            "| `{}`（{}） | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(
                r["model_name"],
                r["label"],
                r["auc"],
                r["f1"],
                r["precision"],
                r["recall"],
                r["accuracy"],
            )
        )
    lines.append(
        "\n## 二、Effort-aware 指标（检验集，LOC 工作量代理）\n\n"
        "| 排序方式 | 模型 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n"
        "|---|---|---|---|---|---|\n"
    )
    for r in results.values():
        m = r["effort"]["LOC（改动行数 la+ld）"]["model"]
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append(
            "| **模型排序** | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(
                r["model_name"], m["area"], m["p_norm"], m["recall@20"], m["recall@50"]
            )
        )
        lines.append(
            "| 对照：密度排序 | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(
                r["model_name"], d["area"], d["p_norm"], d["recall@20"], d["recall@50"]
            )
        )
    first = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]
    optimal, random = first["optimal"], first["random"]
    lines.append(
        f"| 上界：真实密度 | — | {optimal['area']:.4f} | {optimal['p_norm']:.4f} | {optimal['recall@20']:.4f} | {optimal['recall@50']:.4f} |\n"
        f"| 基线：随机（{random['repeats']} 次均值） | — | {random['area']:.4f} ± {random['area_std']:.4f} | {random['p_norm']:.4f} | — | — |\n"
    )
    lines.append("\n## 与 baseline 对照（读法）\n\n")
    lines.append(
        "> 把本表与 `pipelines/expert/reports/model_metrics.md` 并排：AUC 高出多少 = "
        "纯语义模态的增益；若不升反降，如实登记，不选择性只报更好的一组。\n"
    )
    lines.append("\n")
    if text_stats:
        lines.extend(
            text_source.registration_lines(
                text_stats["counts"], text_stats["n_total"], text_stats.get("positives")
            )
        )
        lines.append("\n")
        lines.extend(
            text_source.robustness_lines(
                text_stats["kept"],
                text_stats["dropped"],
                text_stats.get("deltas"),
                text_stats.get("retrained", False),
            )
        )
        test_counts = text_stats.get("test_counts") or {}
        placeholder_test = sum(
            test_counts.get(n, 0)
            for n in (text_source.SOURCE_NO_TEXT_CHANGE, text_source.SOURCE_ROOT_COMMIT)
        )
        lines.append(
            f"- 检验集内含占位 {placeholder_test} 条（上表「剔除」即这部分）；"
            "训练侧占位数见全量登记。\n"
        )
    else:
        lines.append(
            "## 文本来源与覆盖率\n\n"
            "> **未登记**：本次读的编码缓存没有 `text_source` 键（旧版缓存），"
            "不按 `diff` 冒充。重跑 `train.py --force-encode`（或重建文本数据集）后本段自动出现。\n"
        )
    lines.append("\n## 图表\n\n")
    for fig in ("roc_curves", "effort_curves_loc", "metric_bars"):
        lines.append(f"![{fig}](figs/{fig}.png)\n\n")
    return "".join(lines)
