"""预测性能评估：导入、预检、指标与图表、历史保存。"""

from __future__ import annotations

import shutil
from datetime import datetime

import numpy as np
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from app.constants import EVAL_METRICS, FIGURE_TYPES, PREDICTION_EXTRA_COLUMNS
from app.errors import AppError
from app.models import Dataset, Evaluation, EvaluationFigure, Prediction, User
from app.services import artifacts, datasets, uploads
from app.services.jobs import JobContext
from app.services.validation import expected_columns
from app.utils import iso, loads, new_id, now, valid_name
from data_model import charts, metrics as metric_lib


def import_file(user: User, filename: str, payload: bytes, label: str | None) -> dict:
    result = uploads.save_prediction_upload(user.user_id, filename, payload, label)
    return {
        "file_id": result["meta"]["file_id"],
        "label": result["meta"]["label"],
        "line": result["line"],
        "sample_count": result["sample_count"],
        "pos": result["pos"],
        "neg": result["neg"],
        "threshold": result["threshold"],
    }


def _dataset_predictions(db, dataset: Dataset) -> list[Prediction]:
    return db.scalars(
        select(Prediction).where(Prediction.dataset_id == dataset.dataset_id).order_by(Prediction.commit_hash)
    ).all()


def _threshold_of(rows: list[Prediction]) -> float | None:
    values = {round(float(row.threshold), 3) for row in rows}
    return values.pop() if len(values) == 1 else None


def precheck_dataset(db, user: User, dataset_id: str) -> dict:
    dataset = datasets.owned(db, user, dataset_id)
    if dataset.source_type != "prediction":
        raise AppError(40001, "仅接受预测结果数据集")
    rows = _dataset_predictions(db, dataset)
    if not rows:
        raise AppError(42201, "预测结果为空")
    invalid = [index + 1 for index, row in enumerate(rows) if row.actual_label is None]
    if invalid:
        raise AppError(42201, "预测结果缺少真实标签", {"invalid_rows": invalid[:20]})
    pos = sum(1 for row in rows if row.actual_label == 1)
    model_label = next((row.model_label or row.model_name for row in rows if row.model_label or row.model_name), None)
    return {
        "line": dataset.line,
        "sample_count": len(rows),
        "pos": pos,
        "neg": len(rows) - pos,
        "model_label": model_label,
        "threshold": _threshold_of(rows),
    }


def _validate_request(metrics: list[str], threshold: float) -> None:
    if not metrics:
        raise AppError(40001, "至少选择一个指标")
    unknown = [item for item in metrics if item not in EVAL_METRICS]
    if unknown:
        raise AppError(40001, f"未知指标：{unknown[0]}")
    if len(set(metrics)) != len(metrics):
        raise AppError(40001, "指标不能重复")
    try:
        threshold = float(threshold)
    except (TypeError, ValueError):
        raise AppError(40001, "阈值非法")
    if not 0 <= threshold <= 1:
        raise AppError(40001, "阈值必须位于 0–1")


def planned_figures(metrics: list[str]) -> list[str]:
    figures = ["bar"]
    if "auc" in metrics:
        figures.append("roc")
    if "ap" in metrics:
        figures.append("pr")
    if any(item in metrics for item in ("accuracy", "precision", "recall", "f1", "mcc")):
        figures.append("confusion")
    return figures


def _load_source(db, user: User, source: dict) -> dict:
    kind = source.get("kind")
    if kind == "dataset":
        dataset = datasets.owned(db, user, source.get("id", ""))
        if dataset.source_type != "prediction":
            raise AppError(40001, "仅接受预测结果数据集")
        rows = _dataset_predictions(db, dataset)
        if not rows:
            raise AppError(42201, "预测结果为空")
        if any(row.actual_label is None for row in rows):
            raise AppError(42201, "预测结果缺少真实标签")
        columns, export_rows = datasets.export_rows(db, dataset)
        model_label = next((row.model_label or row.model_name for row in rows if row.model_label or row.model_name), None)
        return {
            "columns": columns, "rows": export_rows, "line": dataset.line,
            "model_name": next((row.model_name for row in rows if row.model_name), None),
            "model_label": model_label, "source_kind": "dataset",
            "source_label": dataset.name, "threshold": _threshold_of(rows),
            "source_id": dataset.dataset_id,
        }
    if kind == "file":
        meta, path = uploads.read_import(user.user_id, source.get("id", ""))
        if meta.get("role") != "data":
            raise AppError(40401, "导入文件不存在")
        columns, rows = artifacts.read_table(path)
        return {
            "columns": columns, "rows": rows, "line": meta.get("line") or "expert",
            "model_name": None, "model_label": None, "source_kind": "file",
            "source_label": meta.get("label") or meta.get("original_name") or "imported",
            "threshold": meta.get("threshold"), "source_id": None,
        }
    raise AppError(40001, "数据源类型非法")


def _labels_scores(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    labels, scores = [], []
    for row in rows:
        bug = str(row.get("bug", "")).strip()
        if bug not in ("0", "1"):
            raise AppError(42201, "预测结果缺少真实标签")
        labels.append(int(bug))
        scores.append(float(row.get("risk_score", 0) or 0))
    return np.array(labels, dtype=int), np.array(scores, dtype=float)


def run_evaluate(ctx: JobContext) -> None:
    from app.db import SessionLocal

    params = ctx.params
    metrics = list(params.get("metrics") or [])
    threshold = float(params.get("threshold", 0.5))
    _validate_request(metrics, threshold)
    with SessionLocal() as session:
        user = session.get(User, ctx.user_id)
        source = _load_source(session, user, params.get("source") or {})
    y_true, y_score = _labels_scores(source["rows"])
    if len(set(y_true.tolist())) < 2 and ("auc" in metrics or "ap" in metrics):
        raise AppError(42201, "单类别数据无法计算 AUC / AP")
    figures = planned_figures(metrics)
    ctx.set_total(len(figures))
    ctx.update(force=True)
    out_dir = artifacts.output_dir(ctx.user_id, ctx.job_id)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for figure in figures:
        ctx.check()
        ctx.set_stage(f"生成 {figure} 图")
        target = fig_dir / f"{figure}.png"
        if figure == "roc":
            charts.roc_figure(y_true, y_score, target)
        elif figure == "pr":
            charts.pr_figure(y_true, y_score, target)
        elif figure == "confusion":
            charts.confusion_figure(y_true, y_score, threshold, target)
        else:
            values = metric_lib.compute_metrics(y_true, y_score, threshold, metrics)
            display = {name: values.get(name) for name in metrics}
            charts.bar_figure(display, target)
        paths[figure] = artifacts.rel(target)
        ctx.advance(1)
    values = metric_lib.compute_metrics(y_true, y_score, threshold, metrics)
    pos = int((y_true == 1).sum())
    result = {
        "threshold": threshold,
        "sample_count": int(len(y_true)),
        "pos": pos,
        "neg": int(len(y_true)) - pos,
        "metrics": values,
        "figure_paths": paths,
        "metric_names": metrics,
    }
    artifacts.write_json(out_dir / "evaluate.json", result)
    ctx.set_output({
        **result,
        "source_kind": source["source_kind"],
        "source_label": source["source_label"],
        "model_name": source["model_name"],
        "model_label": source["model_label"],
        "line": source["line"],
        "source_id": source["source_id"],
    })


def _job_ref(db, user: User, job_id: str) -> dict:
    from app.models import Job

    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    if job.kind != "evaluate" or job.status != "success":
        raise AppError(40901, "评估结果未就绪")
    ref = loads(job.output_ref_json, {}) or {}
    if not ref.get("metrics"):
        raise AppError(40901, "评估结果已失效")
    return ref


def result_payload(ref: dict, job_id: str) -> dict:
    figures = []
    for figure in FIGURE_TYPES:
        if figure in (ref.get("figure_paths") or {}):
            figures.append({"type": figure, "url": f"/api/evaluate/results/{job_id}/figures/{figure}"})
    return {
        "threshold": ref.get("threshold"),
        "sample_count": ref.get("sample_count"),
        "pos": ref.get("pos"),
        "neg": ref.get("neg"),
        "metrics": ref.get("metrics") or {},
        "figures": figures,
    }


def save_evaluation(db, user: User, job_id: str, name: str) -> str:
    if not valid_name(name):
        raise AppError(40001, "评估名称非法")
    ref = _job_ref(db, user, job_id)
    if db.scalar(select(Evaluation).where(Evaluation.owner_user_id == user.user_id, Evaluation.name == name)):
        raise AppError(40901, "评估名称已存在")
    evaluation_id = new_id("evaluation")
    target = artifacts.evaluation_dir(user.user_id, evaluation_id)
    copied: dict[str, dict] = {}
    for figure, path in (ref.get("figure_paths") or {}).items():
        source = artifacts.resolve(path)
        if not source.is_file():
            raise AppError(40901, "图表文件缺失")
        destination = target / "figures" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied[figure] = {
            "path": artifacts.rel(destination), "sha256": artifacts.file_sha256(destination),
        }
    evaluation = Evaluation(
        evaluation_id=evaluation_id,
        owner_user_id=user.user_id,
        name=name,
        source_kind=ref.get("source_kind") or "file",
        source_label=str(ref.get("source_label") or "")[:255],
        dataset_id=ref.get("source_id") if ref.get("source_kind") == "dataset" else None,
        model_name=ref.get("model_name"),
        model_label=ref.get("model_label"),
        threshold=float(ref.get("threshold", 0.5)),
        metrics_json={
            "metrics": ref.get("metrics") or {},
            "metric_names": ref.get("metric_names") or list((ref.get("metrics") or {}).keys()),
            "sample_count": ref.get("sample_count"),
            "pos": ref.get("pos"),
            "neg": ref.get("neg"),
        },
        sample_count=int(ref.get("sample_count") or 0),
        pos_count=int(ref.get("pos") or 0),
        neg_count=int(ref.get("neg") or 0),
        created_at=now(),
    )
    try:
        db.add(evaluation)
        db.flush()
        for figure, item in copied.items():
            db.add(EvaluationFigure(
                figure_id=new_id("figure"), evaluation_id=evaluation_id, figure_type=figure,
                file_path=item["path"], sha256=item["sha256"], created_at=now(),
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return evaluation_id


def history(db, user: User, q: str | None, page: int, page_size: int) -> dict:
    query = select(Evaluation).where(Evaluation.owner_user_id == user.user_id)
    count_query = select(func.count()).select_from(Evaluation).where(Evaluation.owner_user_id == user.user_id)
    if q:
        query = query.where(Evaluation.name.like(f"%{q}%"))
        count_query = count_query.where(Evaluation.name.like(f"%{q}%"))
    total = db.scalar(count_query) or 0
    rows = db.scalars(
        query.order_by(Evaluation.created_at.desc(), Evaluation.evaluation_id.asc())
        .offset(page_size * (page - 1)).limit(page_size)
    ).all()
    items = []
    for row in rows:
        payload = row.metrics_json or {}
        items.append({
            "evaluation_id": row.evaluation_id, "name": row.name, "source_kind": row.source_kind,
            "source_label": row.source_label, "model_label": row.model_label,
            "threshold": float(row.threshold), "sample_count": row.sample_count,
            "metrics": payload.get("metrics") or {}, "created_at": iso(row.created_at),
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _owned_evaluation(db, user: User, evaluation_id: str) -> Evaluation:
    row = db.get(Evaluation, evaluation_id)
    if row is None or row.owner_user_id != user.user_id:
        raise AppError(40401, "评估记录不存在")
    return row


def evaluation_detail(db, user: User, evaluation_id: str) -> dict:
    row = _owned_evaluation(db, user, evaluation_id)
    payload = row.metrics_json or {}
    figures = db.scalars(
        select(EvaluationFigure).where(EvaluationFigure.evaluation_id == evaluation_id)
    ).all()
    return {
        "evaluation_id": row.evaluation_id,
        "name": row.name,
        "source_kind": row.source_kind,
        "source_label": row.source_label,
        "model_label": row.model_label,
        "threshold": float(row.threshold),
        "sample_count": row.sample_count,
        "pos": row.pos_count,
        "neg": row.neg_count,
        "metrics": payload.get("metrics") or {},
        "created_at": iso(row.created_at),
        "figures": [
            {"type": item.figure_type, "url": f"/api/evaluate/history/{evaluation_id}/figures/{item.figure_type}"}
            for item in sorted(figures, key=lambda fig: FIGURE_TYPES.index(fig.figure_type) if fig.figure_type in FIGURE_TYPES else 99)
        ],
    }


def evaluation_figure_path(db, user: User, evaluation_id: str, figure_type: str) -> str:
    row = _owned_evaluation(db, user, evaluation_id)
    figure = db.scalar(
        select(EvaluationFigure).where(
            EvaluationFigure.evaluation_id == row.evaluation_id, EvaluationFigure.figure_type == figure_type
        )
    )
    if figure is None:
        raise AppError(40901, "图表不存在")
    path = artifacts.resolve(figure.file_path)
    if not path.is_file():
        raise AppError(40901, "图表文件缺失")
    return figure.file_path


def delete_evaluation(db, user: User, evaluation_id: str) -> None:
    row = _owned_evaluation(db, user, evaluation_id)
    user_id = row.owner_user_id
    try:
        db.execute(sa_delete(EvaluationFigure).where(EvaluationFigure.evaluation_id == evaluation_id))
        db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    shutil.rmtree(artifacts.evaluation_dir(user_id, evaluation_id), ignore_errors=True)


def export_table(ref: dict) -> tuple[list[str], list[dict]]:
    metrics = ref.get("metrics") or {}
    names = ref.get("metric_names") or list(metrics.keys())
    columns = list(names) + ["threshold"]
    row = {name: metrics.get(name) for name in names}
    row["threshold"] = ref.get("threshold")
    return columns, [row]
