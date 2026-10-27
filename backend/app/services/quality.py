"""预测质量与标签回流（change quality-loop）。

口径：
- ground truth 只认 `label_method="manual"` 的人工标签（不认 SZZ 自动标签）；
- 预测侧用 `prediction.risk_score >= threshold` 二值化；
- 纯只读，`MUST NOT` 触发任何预测或写入（校准写 `runtime_setting` 除外）。

有了这两个口径，才能回答「模型还准不准」「阈值该定在哪」这两个运营问题。
"""

from __future__ import annotations

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Commit, CommitFeature, CommitLabel, Prediction
from app.services import settings as runtime_settings
from app.services.commits import MANUAL_LABEL_METHOD, default_model_in_table, feature_dict
from app.timeutil import iso_z, now_naive_utc

# 可评估样本少于 2 条、或标签只有单一类别时算不出 F1：校准只报告、不落库
MIN_EVALUATED = 2
# 候选阈值：0.05 ~ 0.95，步长 0.05（与契约「0.1 步进」的展示口径不冲突，内部更细）
THRESHOLD_CANDIDATES = [round(0.05 * i, 2) for i in range(1, 20)]


def resolve_model(model_name: str | None) -> str | None:
    """显式给定时原样使用（历史模型也可评估）；否则取表内最新模型。"""
    if model_name:
        return model_name
    with SessionLocal() as session:
        return default_model_in_table(session)


def _labeled_rows(model_name: str, start, end) -> list[tuple[float, int]]:
    """[(risk_score, is_defect)]：manual 标签 INNER JOIN 该模型 prediction。"""
    with SessionLocal() as session:
        stmt = (
            select(Prediction.risk_score, CommitLabel.is_bug_inducing)
            .join(CommitLabel, CommitLabel.commit_hash == Prediction.commit_hash)
            .join(Commit, Commit.commit_hash == Prediction.commit_hash)
            .where(
                CommitLabel.label_method == MANUAL_LABEL_METHOD,
                Prediction.model_name == model_name,
            )
        )
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        return [(float(score), int(label)) for score, label in session.execute(stmt).all()]


def _labeled_total(start, end) -> int:
    """区间内 manual 标签总数（含尚无 prediction 的，故可能大于 evaluated）。"""
    with SessionLocal() as session:
        stmt = (
            select(func.count())
            .select_from(CommitLabel)
            .join(Commit, Commit.commit_hash == CommitLabel.commit_hash)
            .where(CommitLabel.label_method == MANUAL_LABEL_METHOD)
        )
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        return int(session.execute(stmt).scalar_one() or 0)


def _confusion(rows: list[tuple[float, int]], threshold: float) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for score, label in rows:
        predicted = score >= threshold
        if predicted and label:
            tp += 1
        elif predicted:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    return tp, fp, tn, fn


def _stats(tp: int, fp: int, tn: int, fn: int) -> dict:
    """派生指标；分母为 0 时返回 None（MUST NOT 用 0 冒充「完美」）。"""
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else None
    return {
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "accuracy": round(accuracy, 4) if accuracy is not None else None,
    }


def best_threshold(rows: list[tuple[float, int]], current: float) -> float:
    """F1 最高的候选阈值；F1 并列时取更接近当前阈值的（避免无意义抖动）。"""
    best_key: tuple[float, float] | None = None
    best = current
    for candidate in THRESHOLD_CANDIDATES:
        stats = _stats(*_confusion(rows, candidate))
        if stats["f1"] is None:
            continue
        key = (stats["f1"], -abs(candidate - current))
        if best_key is None or key > best_key:
            best_key = key
            best = candidate
    return best


def report(model_name: str | None, threshold: float | None, start, end) -> dict:
    model = resolve_model(model_name)
    if threshold is None:
        threshold = runtime_settings.high_threshold()
    labeled_total = _labeled_total(start, end)
    if model is None:
        return {
            "model_name": None,
            "threshold": round(threshold, 4),
            "labeled_total": labeled_total,
            "evaluated": 0,
            "tp": 0,
            "fp": 0,
            "tn": 0,
            "fn": 0,
            "precision": None,
            "recall": None,
            "f1": None,
            "accuracy": None,
            "avg_risk_defect": None,
            "avg_risk_clean": None,
            "recommended_threshold": None,
            "evaluated_at": iso_z(now_naive_utc()),
        }
    rows = _labeled_rows(model, start, end)
    tp, fp, tn, fn = _confusion(rows, threshold)
    defects = [score for score, label in rows if label]
    cleans = [score for score, label in rows if not label]
    return {
        "model_name": model,
        "threshold": round(threshold, 4),
        "labeled_total": labeled_total,
        "evaluated": len(rows),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        **_stats(tp, fp, tn, fn),
        "avg_risk_defect": round(sum(defects) / len(defects), 4) if defects else None,
        "avg_risk_clean": round(sum(cleans) / len(cleans), 4) if cleans else None,
        "recommended_threshold": (
            best_threshold(rows, threshold) if len(rows) >= MIN_EVALUATED else None
        ),
        "evaluated_at": iso_z(now_naive_utc()),
    }


def dataset() -> dict:
    """导出回流样本：人工标签 + 14 维特征，供离线再训练直接消费。"""
    with SessionLocal() as session:
        rows = session.execute(
            select(CommitLabel, Commit, CommitFeature)
            .join(Commit, Commit.commit_hash == CommitLabel.commit_hash)
            .outerjoin(CommitFeature, CommitFeature.commit_hash == CommitLabel.commit_hash)
            .where(CommitLabel.label_method == MANUAL_LABEL_METHOD)
            .order_by(CommitLabel.labeled_at, CommitLabel.commit_hash)
        ).all()
        items = [
            {
                "commit_hash": commit.commit_hash,
                "is_defect": bool(label.is_bug_inducing),
                "labeled_at": iso_z(label.labeled_at),
                "committed_at": iso_z(commit.committed_at),
                "features": feature_dict(feature),
            }
            for label, commit, feature in rows
        ]
    return {"count": len(items), "items": items}


def calibrate(model_name: str | None) -> dict:
    """按人工标签校准 `high_risk_threshold`；仅在有实质改善时落库。"""
    model = resolve_model(model_name)
    current = runtime_settings.high_threshold()
    current_mid = runtime_settings.mid_threshold()
    before_stats = {
        "threshold": round(current, 4),
        "precision": None,
        "recall": None,
        "f1": None,
    }
    if model is None:
        return {
            "model_name": None,
            "labeled_total": 0,
            "evaluated": 0,
            "applied": False,
            "reason": "no_model",
            "before": before_stats,
            "after": dict(before_stats),
        }

    rows = _labeled_rows(model, None, None)
    before = {**_stats(*_confusion(rows, current)), "threshold": round(current, 4)}
    positives = sum(1 for _, label in rows if label)
    if len(rows) < MIN_EVALUATED or positives == 0 or positives == len(rows):
        return {
            "model_name": model,
            "labeled_total": _labeled_total(None, None),
            "evaluated": len(rows),
            "applied": False,
            "reason": "insufficient_labels",
            "before": before,
            "after": dict(before),
        }

    candidate = best_threshold(rows, current)
    after = {**_stats(*_confusion(rows, candidate)), "threshold": round(candidate, 4)}
    improved = (
        candidate != current
        and after["f1"] is not None
        and (before["f1"] is None or after["f1"] > before["f1"])
    )
    if improved:
        # mid 必须 <= high：阈值下调时同步压低 mid，保证等级区间仍然有序
        runtime_settings.set_thresholds(high=candidate, mid=min(current_mid, candidate))
    return {
        "model_name": model,
        "labeled_total": _labeled_total(None, None),
        "evaluated": len(rows),
        "applied": improved,
        "reason": None if improved else "no_improvement",
        "before": before,
        "after": after,
    }
