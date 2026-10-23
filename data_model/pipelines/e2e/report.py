"""e2e 线结果报告：Markdown + 图表（单模型版，命名与其它线一致）。"""

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
import torch
from sklearn.metrics import roc_curve

from .. import text_source
from . import config
from .metrics import cumulative_curve

FIG_DIR_NAME = "figs"


def make_charts(y: np.ndarray, proba: np.ndarray, effort_loc: np.ndarray | None,
                out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    # ROC
    fpr, tpr, _ = roc_curve(y, proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr, label="%s (AUC=%.3f)"
            % (config.MODEL_NAME, float(_trapz(tpr, fpr))))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC curve - e2e (fine-tuned CodeBERT)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    p = out_dir / "roc_curves.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    # Effort 曲线
    if effort_loc is not None and len(effort_loc) == len(y):
        effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
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
        ax.set_title("Effort-aware curves - e2e (LOC)")
        ax.legend(fontsize=8); ax.grid(alpha=0.3)
        p = out_dir / "effort_curves_loc.png"; fig.tight_layout()
        fig.savefig(p, dpi=150); plt.close(fig)
        written.append(p)
    return written


def render(args, n_train, n_val, n_test, y_test, res, text_stats=None) -> str:
    eff = res.get("effort") or {}
    lines = [
        "# e2e 线模型评估指标（CodeBERT 端到端微调）\n",
        "> 对照线：与 expert 同切分、同指标口径；唯一做反向传播的一条（需 GPU）。\n",
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        f"| 骨干模型 | `{args.text_model}` |\n",
        f"| 特征版本（本线标识） | `{config.FEATURE_VERSION}` |\n",
        f"| 训练/验证/检验 | {n_train} / {n_val} / {n_test} 条（共享切分；验证集=训练尾部时间序，仅供选模） |\n",
        f"| 最大长度 / 轮数 / 学习率 | {args.max_len} token / {args.epochs} / {args.lr:g} |\n",
        f"| 有效 batch | {args.batch_size * max(1, config.GRAD_ACCUM_TARGET // args.batch_size)}（{args.batch_size} × 累积） |\n",
        f"| 随机种子 | `{args.seed}` |\n",
        f"| 判定阈值 | {config.DECISION_THRESHOLD} |\n",
        "| 检验集正样本比例 | %.2f%% |\n" % (y_test.mean() * 100),
        "| 设备 | %s |\n" % ("CUDA（fp16）" if torch.cuda.is_available() else "CPU"),
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
        "| `{}` | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(config.MODEL_NAME, res["auc"], res["f1"], res["precision"],
           res["recall"], res["accuracy"]),
    ]
    if eff:
        lines += [
            "\n## 二、Effort-aware 指标（检验集，LOC 工作量代理）\n\n",
            "| 排序方式 | 曲线下面积 | **P_norm** | Recall@20% | Recall@50% |\n|---|---|---|---|---|\n",
        ]
        for key, lbl in (("model", "**模型排序**（契约三当前口径）"),
                         ("density", "对照：按 `risk_score / 工作量` 降序"),
                         ("optimal", "上界：真实缺陷密度降序")):
            m = eff[key]
            lines.append("| {} | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(lbl, m["area"], m["p_norm"], m["recall@20"], m["recall@50"]))
        r_ = eff["random"]
        lines.append("| 基线：随机排序（{} 次均值） | {:.4f} ± {:.4f} | {:.4f} | — | — |\n".format(
            r_["repeats"], r_["area"], r_["area_std"], r_["p_norm"]))
    else:
        lines.append("\n> ⚠️ 未计算 Effort-aware：缺 `commit_features_raw.csv` 或 hash 对不上。\n")
    lines += [
        "\n## 与 baseline 对照（读法）\n\n",
        ("> 与 `pipelines/expert/reports/model_metrics.md` 并排：e2e 的 AUC/P_norm 高出"
         " baseline 多少 = 端到端微调相对 Kamei14 手工特征的增益；不优时如实登记。\n"),
    ]
    lines.append("\n")
    if text_stats:
        lines.extend(text_source.registration_lines(
            text_stats["counts"], text_stats["n_total"], text_stats.get("positives")))
        lines.append("\n")
        lines.extend(text_source.robustness_lines(
            text_stats["kept"], text_stats["dropped"], text_stats.get("deltas"),
            text_stats.get("retrained", False)))
        lines.append("- 占位样本**参与了微调**（它们是有标签的真实提交，输入是显式占位串，"
                     "不是空串也不是伪造 diff）；本次未按剔除后样本重训，所以上面的剔除"
                     "只是检验集口径的敏感性检查。\n")
    else:
        lines.append("## 文本来源与覆盖率\n\n"
                     "> **未登记**：文本数据集没有 `text_source` 列（旧版 `commit_text.csv`），"
                     "不按 `diff` 冒充；用打过补丁的 `build_text_dataset.py` 重建文本后本段自动出现。\n")
    lines.append("\n## 图表\n\n")
    for fig in ("roc_curves", "effort_curves_loc"):
        lines.append(f"![{fig}](figs/{fig}.png)\n\n")
    return "".join(lines)
