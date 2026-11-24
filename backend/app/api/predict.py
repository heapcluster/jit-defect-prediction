"""预测接口：POST /api/predict 单条在线预测；POST /api/predict/run 文件批量预测。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app import schemas
from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import file_contracts as fc
from app.services import predict_run
from app.services.predict import predict_single

router = APIRouter(dependencies=[Depends(require_api_key)])


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_hash: str
    model_name: str | None = None
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


@router.get("/api/predict/outputs/{job_id}/{name}")
def download_predict(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('predict', job_id, name)
