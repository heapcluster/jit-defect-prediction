"""预测接口 4：POST /api/predict 在线预测（契约三 1.5 第 4 节）。

路由层只做入参校验与响应包络；预测业务收在 `app.services.predict`。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import schemas
from app.auth import require_api_key
from app.errors import ok
from app.services.predict import predict_single, resolve_model_name

router = APIRouter(dependencies=[Depends(require_api_key)])


class PredictRequest(BaseModel):
    commit_hash: str
    model_name: str | None = None


@router.post("/api/predict", response_model=schemas.PredictResponse)
def predict(body: PredictRequest) -> dict:
    """对单条提交现算特征并预测（runbook §6 第 5 条）。

    未指定 model_name 时取全站冠军模型（`champion_model`，未配置则 version_key 最大者）；
    指定时仅对该模型打分。默认模型解析统一在 `services.predict.resolve_model_name`。
    """
    return ok(predict_single(body.commit_hash, resolve_model_name(body.model_name)))
