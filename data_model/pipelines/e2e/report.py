"""e2e 线结果报告：Markdown + 图表（单模型版，命名与其它线一致）。"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import roc_curve

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
            % (config.MODEL_NAME, float(np.trapz(tpr, fpr))))
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


def render(args, n_train, n_test, y_test, res) -> str:
    eff = res.get("effort") or {}
    lines = [
        "# e2e 线模型评估指标（CodeBERT 端到端微调）\n",
        "> 对照线：与 expert 同切分、同指标口径；唯一做反向传播的一条（需 GPU）。\n",
        "## 数据与参数\n",
        "| 项 | 值 |\n|---|---|\n",
        "| 骨干模型 | `%s` |\n" % args.text_model,
        "| 特征版本（本线标识） | `%s` |\n" % config.FEATURE_VERSION,
        "| 训练/检验 | %d / %d 条（共享切分） |\n" % (n_train, n_test),
        "| 最大长度 / 轮数 / 学习率 | %d token / %d / %g |\n"
        % (args.max_len, args.epochs, args.lr),
        "| 有效 batch | %d（%d × 累积） |\n" % (args.batch_size * max(1, config.GRAD_ACCUM_TARGET // args.batch_size), args.batch_size),
        "| 随机种子 | `%d` |\n" % args.seed,
        "| 判定阈值 | %s |\n" % config.DECISION_THRESHOLD,
        "| 检验集正样本比例 | %.2f%% |\n" % (y_test.mean() * 100),
        "| 设备 | %s |\n" % ("CUDA（fp16）" if torch.cuda.is_available() else "CPU"),
        "\n## 一、Effort-unaware 指标（检验集）\n",
        "| 模型 | AUC | F1 | Precision | Recall | Accuracy |\n|---|---|---|---|---|---|\n",
        "| `%s` | %.4f | %.4f | %.4f | %.4f | %.4f |\n"
        % (config.MODEL_NAME, res["auc"], res["f1"], res["precision"],
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
            lines.append("| %s | %.4f | **%.4f** | %.4f | %.4f |\n"
                         % (lbl, m["area"], m["p_norm"], m["recall@20"], m["recall@50"]))
        r_ = eff["random"]
        lines.append("| 基线：随机排序（%d 次均值） | %.4f ± %.4f | %.4f | — | — |\n"
                     % (r_["repeats"], r_["area"], r_["area_std"], r_["p_norm"]))
    else:
        lines.append("\n> ⚠️ 未计算 Effort-aware：缺 `commit_features_raw.csv` 或 hash 对不上。\n")
    lines += [
        "\n## 与 baseline 对照（读法）\n\n",
        "> 与 `pipelines/expert/reports/model_metrics.md` 并排：e2e 的 AUC/P_norm 高出"
        " baseline 多少 = 端到端微调相对 Kamei14 手工特征的增益；不优时如实登记。\n",
        "\n## 图表\n\n",
    ]
    for fig in ("roc_curves", "effort_curves_loc"):
        lines.append("![%s](figs/%s.png)\n\n" % (fig, fig))
    return "".join(lines)
