"""expert 线结果报告：Markdown 表格 + matplotlib 图表（reports/figs/）。

图表统一命名（四条线一致，便于横向对比）：
  figs/roc_curves.png         各模型 ROC
  figs/effort_curves_loc.png  累计召回 ~ 累计工作量（LOC 代理，四种排序）
  figs/metric_bars.png        AUC / F1 柱状对比
图表内文字用英文 —— matplotlib 默认字体不含中文，避免乱码。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")          # 无显示环境也能出图
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import roc_curve

from . import config
from .metrics import cumulative_curve

FIG_DIR_NAME = "figs"


def _roc_ax(ax, y, probas: dict, title):
    for name, proba in probas.items():
        fpr, tpr, _ = roc_curve(y, proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={float(np.trapz(tpr, fpr)):.3f})")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.set_title(title); ax.legend(fontsize=8); ax.grid(alpha=0.3)


def make_charts(results: dict, probas: dict, y: np.ndarray,
                effort_loc: np.ndarray, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # 1) ROC
    fig, ax = plt.subplots(figsize=(6, 5))
    _roc_ax(ax, y, probas, "ROC curves (test set)")
    p = out_dir / "roc_curves.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
    written.append(p)

    # 2) Effort 曲线（LOC 代理；只画第一个模型的四种排序 + 上界/随机示意）
    first = next(iter(results))
    effort = np.maximum(np.asarray(effort_loc, dtype=float), 1.0)
    fig, ax = plt.subplots(figsize=(6, 5))
    style = {"model": "-", "density": "--", "optimal": ":", "random": "-."}
    label = {"model": "model (risk_score desc)", "density": "density (score/effort)",
             "optimal": "optimal (oracle)", "random": "random baseline"}
    for key in ("model", "density", "optimal"):
        proba = probas[first] if key == "model" else None
        if key == "model":
            order = np.argsort(-proba, kind="stable")
        elif key == "density":
            order = np.argsort(-(probas[first] / effort), kind="stable")
        else:
            order = np.argsort(-(y / effort), kind="stable")
        xs, ys = cumulative_curve(order, effort, y)
        ax.plot(xs, ys, style[key], label=label[key])
    rng = np.random.default_rng(config.RANDOM_BASELINE_SEED)
    xs, ys = cumulative_curve(rng.permutation(len(y)), effort, y)
    ax.plot(xs, ys, style["random"], label=label["random"])
    ax.set_xlabel("Cumulative effort fraction"); ax.set_ylabel("Cumulative recall")
    ax.set_title(f"Effort-aware curves (LOC, model={first})")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    p = out_dir / "effort_curves_loc.png"; fig.tight_layout(); fig.savefig(p, dpi=150); plt.close(fig)
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
    lines.append("| 排序方式 | 模型 | 曲线下面积 | **P_norm（=Popt）** | Recall@20%（=CE@20%） | Recall@50% |\n"
                 "|---|---|---|---|---|---|\n")
    for name, r in results.items():
        m = r["effort"]["LOC（改动行数 la+ld）"]["model"]
        lines.append("| **模型排序**（契约三当前口径） | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(r["model_name"], m["area"], m["p_norm"], m["recall@20"], m["recall@50"]))
        d = r["effort"]["LOC（改动行数 la+ld）"]["density"]
        lines.append("| 对照：按 `risk_score / 工作量` 降序 | `{}` | {:.4f} | **{:.4f}** | {:.4f} | {:.4f} |\n".format(r["model_name"], d["area"], d["p_norm"], d["recall@20"], d["recall@50"]))
    o = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["optimal"]
    r_ = results[next(iter(results))]["effort"]["LOC（改动行数 la+ld）"]["random"]
    lines.append("| 上界：真实缺陷密度降序 | — | {:.4f} | {:.4f} | {:.4f} | {:.4f} |\n".format(o["area"], o["p_norm"], o["recall@20"], o["recall@50"]))
    lines.append(f"| 基线：随机排序（{r_['repeats']} 次均值） | — | {r_['area']:.4f} ± {r_['area_std']:.4f} | {r_['p_norm']:.4f} | — | — |\n")
    lines.append("\n> 随机基线应落在 0.5 附近 —— 它是面积算法的自我校验。\n")
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
