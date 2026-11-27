"""预测接口：POST /api/predict 单条在线预测；POST /api/predict/run 文件批量预测。"""

from __future__ import annotations

import csv
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from app import schemas
from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Prediction
from app.services import file_contracts as fc
from app.services import job_store, output_store, predict_run
from app.services.predict import predict_single
from app.timeutil import iso_z

router = APIRouter(dependencies=[Depends(require_api_key)])


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_hash: str
    model_name: str
    decision_threshold: float | None = Field(default=None, gt=0, lt=1)
    force_recompute: bool = False


@router.post("/api/predict", response_model=schemas.PredictResponse)
def predict(body: PredictRequest) -> dict:
    return ok(predict_single(body.commit_hash, body.model_name,
                             decision_threshold=body.decision_threshold, force_recompute=body.force_recompute))


@router.post("/api/predict/run")
async def run_predict(request: Request, config: Annotated[str, Form()] = '{}',
                      files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]'} or len(form.getlist('config')) > 1:
        fc.invalid('未知或重复的表单字段')
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid('预测上传文件超过合计大小限制')
        remaining -= len(content)
        uploaded.append((file.filename or '', content))

    def submit():
        with predict_run.db.SessionLocal() as session:
            return predict_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get("/api/predict/preview/{job_id}")
def preview_predict(
    request: Request,
    job_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """批量预测结果分页预览：优先读 prediction 表，缺失时回退核心 CSV。"""
    query_keys(request, {"page", "size"})
    with SessionLocal() as session:
        job = job_store.get(session, job_id)
        if job["kind"] != "predict_batch":
            raise AppError(40400, "预测任务不存在")
        total = session.scalar(
            select(func.count()).select_from(Prediction).where(Prediction.job_id == job_id)
        ) or 0
        rows = []
        if total:
            rows = session.scalars(
                select(Prediction)
                .where(Prediction.job_id == job_id)
                .order_by(Prediction.predicted_at, Prediction.commit_hash)
                .offset((page - 1) * size)
                .limit(size)
            ).all()
    if total:
        preview = [{
            "commit_hash": row.commit_hash,
            "model_name": row.model_name,
            "risk_score": row.risk_score,
            "predicted_label": row.predicted_label,
            "decision_threshold": row.decision_threshold,
            "model_version": row.model_version,
            "feature_version": row.feature_version,
            "predicted_at": iso_z(row.predicted_at),
            "is_bug_inducing": row.is_bug_inducing,
        } for row in rows]
        return ok({"columns": list(fc.PREDICTIONS_COLUMNS), "preview": preview,
                   "total": total, "page": page, "size": size})
    reference = job["output_ref_json"] or {}
    names = [item.get("name") for item in reference.get("outputs", [])
             if isinstance(item.get("name"), str) and item["name"].endswith(".csv")]
    name = next((item for item in names if item.startswith("predict_predictions_")), None)
    name = name or (names[0] if names else None)
    if name is None:
        raise AppError(40400, "预测结果不存在")
    path = output_store.read_output("predict", job_id, name)
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames or []
            if tuple(columns) != tuple(fc.PREDICTIONS_COLUMNS):
                fc.invalid("预测结果列与契约不一致")
            records = [{key: (value if value != "" else None) for key, value in row.items()}
                       for row in reader]
    except csv.Error as error:
        fc.invalid(f"无法预览预测结果：{error}")
    total = len(records)
    return ok({"columns": list(fc.PREDICTIONS_COLUMNS),
               "preview": records[(page - 1) * size:(page - 1) * size + size],
               "total": total, "page": page, "size": size})


@router.get("/api/predict/outputs/{job_id}/{name}")
def download_predict(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('predict', job_id, name)
