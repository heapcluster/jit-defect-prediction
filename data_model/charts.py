"""评估图表：后端生成 PNG。"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    auc,
    precision_recall_curve,
    roc_curve,
)

from data_model import metrics as metric_lib  # noqa: E402


def _save(fig, path: Path) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    size = fig.get_size_inches() * fig.dpi
    plt.close(fig)
    return int(size[0]), int(size[1])


def roc_figure(y_true, y_score, path: Path) -> tuple[int, int]:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, color="#2f6fed", label=f"AUC={auc(fpr, tpr):.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#9aa4b2")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    return _save(fig, path)


def pr_figure(y_true, y_score, path: Path) -> tuple[int, int]:
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(recall, precision, color="#e07b39")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall Curve")
    return _save(fig, path)


def confusion_figure(y_true, y_score, threshold: float, path: Path) -> tuple[int, int]:
    tn, fp, fn, tp = metric_lib.confusion(y_true, y_score, threshold)
    fig, ax = plt.subplots(figsize=(4, 4))
    matrix = np.array([[tn, fp], [fn, tp]])
    disp = ConfusionMatrixDisplay(matrix, display_labels=["normal", "defect"])
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title(f"Confusion Matrix @ {threshold:.2f}")
    return _save(fig, path)


def bar_figure(metrics: dict, path: Path) -> tuple[int, int]:
    labels = [key.upper() for key, value in metrics.items() if value is not None]
    values = [float(value) for value in metrics.values() if value is not None]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color="#2f6fed")
    for index, value in enumerate(values):
        ax.text(index, value, f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_title("Selected Metrics")
    return _save(fig, path)
