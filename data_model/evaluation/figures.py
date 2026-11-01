"""按模型生成指标图：ROC / PR / 混淆矩阵 / 校准曲线 / Effort-aware / 特征重要性。

图类型与 `docs/database/model_figure.md` 对齐（新增 `effort`，决策 B）。
每个模型一套图，落两处：
  · 数据线自产：`data_model/pipelines/{line}/reports/figs_by_model/{model}/{type}.png`
  · 后端静态：`backend/static/figures/{line}/{model}/{type}.png`（owner 授权数据线拷贝）
"""

from __future__ import annotations

import shutil
from datetime import UTC, datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from . import config

TITLES = {
    "roc": "ROC curve",
    "pr": "Precision-Recall curve",
    "confusion": "Confusion matrix (threshold=0.5)",
    "calibration": "Calibration (reliability) curve",
    "effort": "Effort-aware curve (LOC proxy)",
    "feat_importance": "Feature importance (Kamei 14)",
}


# ── 指标 ────────────────────────────────────────────────────────────────────
def _metrics(y: np.ndarray, proba: np.ndarray) -> dict:
    pred = (proba >= config.DECISION_THRESHOLD).astype(int)
    return {
        "auc": float(roc_auc_score(y, proba)),
        "ap": float(average_precision_score(y, proba)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "accuracy": float(accuracy_score(y, pred)),
        "n": int(len(y)),
        "pos_rate": float(np.mean(y)),
    }


# ── 各图 ────────────────────────────────────────────────────────────────────
def _fig_roc(y, proba):
    fpr, tpr, _ = roc_curve(y, proba)
    auc = roc_auc_score(y, proba)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.plot(fpr, tpr, color="#1f77b4", lw=1.8, label=f"AUC = {auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC curve (test set)")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    return fig


def _fig_pr(y, proba):
    prec, rec, _ = precision_recall_curve(y, proba)
    ap = average_precision_score(y, proba)
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    ax.plot(rec, prec, color="#ff7f0e", lw=1.8, label=f"AP = {ap:.4f}")
    ax.axhline(float(np.mean(y)), color="grey", ls="--", lw=0.8, label="baseline (pos rate)")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall curve (test set)")
    ax.legend(loc="upper right")
    ax.grid(alpha=0.3)
    return fig


def _fig_confusion(y, proba):
    cm = confusion_matrix(y, (proba >= config.DECISION_THRESHOLD).astype(int), labels=[0, 1])
    fig, ax = plt.subplots(figsize=(4.6, 4.0))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["pred 0", "pred 1"])
    ax.set_yticklabels(["true 0", "true 1"])
    for i in range(2):
        for j in range(2):
            ax.text(
                j, i, f"{cm[i, j]}", ha="center", va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black", fontsize=12,
            )
    ax.set_title("Confusion matrix (threshold=0.5)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return fig


def _fig_calibration(y, proba):
    frac_pos, mean_pred = calibration_curve(y, proba, n_bins=10, strategy="uniform")
    fig, ax = plt.subplots(figsize=(5.0, 4.2))
    ax.plot(mean_pred, frac_pos, "o-", color="#2ca02c", lw=1.6, label="model")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="perfectly calibrated")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Calibration curve (test set)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    return fig


def _cum(effort, y, order):
    eff = np.maximum(np.asarray(effort, dtype=float), 1.0)
    total_e, total_y = float(eff.sum()), float(y.sum())
    xs, ys = [0.0], [0.0]
    ce = cy = 0.0
    for i in order:
        ce += float(eff[i])
        cy += float(y[i])
        xs.append(ce / total_e if total_e else 0.0)
        ys.append(cy / total_y if total_y else 0.0)
    return np.asarray(xs), np.asarray(ys)


def _fig_effort(y, proba, effort):
    eff = np.maximum(np.asarray(effort, dtype=float), 1.0)
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    xs, ys = _cum(eff, y, np.argsort(-proba, kind="stable"))
    ax.plot(xs, ys, color="#1f77b4", lw=1.8, label="model (risk_score desc)")
    opt = _cum(eff, y, np.argsort(-(y / eff), kind="stable"))
    ax.plot(opt[0], opt[1], ":", color="#2ca02c", lw=1.0, label="optimal (oracle)")
    rng = np.random.default_rng(0)
    rnd = _cum(eff, y, rng.permutation(len(y)))
    ax.plot(rnd[0], rnd[1], ls=(0, (1, 2)), color="#d62728", lw=0.9, label="random baseline")
    ax.set_xlabel("Cumulative effort fraction (LOC)")
    ax.set_ylabel("Cumulative recall")
    ax.set_title("Effort-aware curve (test set, LOC proxy)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    return fig


def _importance_vector(model, X, y):
    est = model.named_steps[list(model.named_steps)[-1]] if hasattr(model, "named_steps") else model
    if hasattr(est, "feature_importances_"):
        return np.asarray(est.feature_importances_, dtype=float)
    if hasattr(est, "coef_"):
        return np.abs(np.ravel(est.coef_)).astype(float)
    # 无原生重要性：在测试集子样本上做置换重要性（限 800 条，避免过慢）
    from sklearn.inspection import permutation_importance

    n = min(len(X), 800)
    r = permutation_importance(model, X[:n], y[:n], n_repeats=3, random_state=0, n_jobs=-1)
    return np.asarray(r.importances_mean, dtype=float)


def _fig_importance(model, X, y):
    vals = _importance_vector(model, X, y)
    order = np.argsort(vals)
    names = [config.FEATURE_FIELDS[i] for i in order]
    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    ax.barh(range(len(order)), vals[order], color="#9467bd")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(names)
    ax.set_xlabel("importance")
    ax.set_title("Feature importance (Kamei 14)")
    ax.grid(alpha=0.3, axis="x")
    return fig


# ── 主入口 ──────────────────────────────────────────────────────────────────
def render_all(
    test: pd.DataFrame,
    preds: pd.DataFrame,
    probas: dict[str, np.ndarray],
    models: dict[str, object],
    X14: np.ndarray,
    effort: np.ndarray,
) -> tuple[pd.DataFrame, list[dict]]:
    y = test[config.LABEL_COL].astype(int).to_numpy()
    model_lines = preds.groupby("model_name")["line"].first().to_dict()
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    metrics_rows: list[dict] = []
    figure_rows: list[dict] = []

    for name, proba in probas.items():
        line = model_lines[name]
        out_dir = config.figs_dir(line) / name
        static_dir = config.BACKEND_STATIC_FIGURES / line / name
        out_dir.mkdir(parents=True, exist_ok=True)
        static_dir.mkdir(parents=True, exist_ok=True)

        metrics_rows.append({"line": line, "model_name": name, **_metrics(y, proba)})

        makers = {
            "roc": lambda p=proba: _fig_roc(y, p),
            "pr": lambda p=proba: _fig_pr(y, p),
            "confusion": lambda p=proba: _fig_confusion(y, p),
            "calibration": lambda p=proba: _fig_calibration(y, p),
            "effort": lambda p=proba: _fig_effort(y, p, effort),
        }
        # 特征重要性：仅 expert（14 维可读）
        if line == "expert" and name in models:
            makers["feat_importance"] = lambda m=models[name]: _fig_importance(m, X14, y)

        for ftype, make in makers.items():
            try:
                fig = make()
            except Exception as exc:  # noqa: BLE001 —— 单张图失败不应中断整批
                print(f"[eval] {name} 的 {ftype} 图生成失败：{type(exc).__name__}: {exc}")
                continue
            path = out_dir / f"{ftype}.png"
            fig.savefig(path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            shutil.copy2(path, static_dir / f"{ftype}.png")
            figure_rows.append(
                {
                    "model_name": name,
                    "figure_type": ftype,
                    "title": TITLES[ftype],
                    "file_path": f"/static/figures/{line}/{name}/{ftype}.png",
                    "generated_at": generated_at,
                }
            )

        print(f"[eval] 图完成：{name}（{out_dir}）")

    return pd.DataFrame(metrics_rows), figure_rows
