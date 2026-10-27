"""预测质量与标签回流路由（change quality-loop）。

业务在 `app/services/quality.py`；本文件只做参数校验与响应包络。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app import schemas
from app.auth import require_api_key
from app.errors import AppError, ok
from app.services import quality as quality_service
from app.timeutil import parse_time_param

router = APIRouter(dependencies=[Depends(require_api_key)])


class CalibrateRequest(BaseModel):
    model_name: str | None = None


@router.get("/api/quality", response_model=schemas.QualityResponse)
def quality(
    model_name: str | None = Query(default=None),
    threshold: float | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    label_source: str = Query(default="manual"),
) -> dict:
    """标签 vs 预测的质量指标；无样本时返回 evaluated=0 而非报错。"""
    if threshold is not None and not 0.0 <= threshold <= 1.0:
        raise AppError(40001, "参数非法：threshold 需在 0.0 ~ 1.0")
    if label_source not in quality_service.LABEL_SOURCES:
        # 文案由枚举生成：新增口径时不会漏改提示
        choices = " 或 ".join(quality_service.LABEL_SOURCES)
        raise AppError(40001, f"参数非法：label_source 取值需为 {choices}")
    start = parse_time_param(start_time, "start_time") if start_time else None
    end = parse_time_param(end_time, "end_time", "end") if end_time else None
    return ok(quality_service.report(model_name, threshold, start, end, label_source))


@router.get("/api/quality/dataset", response_model=schemas.QualityDatasetResponse)
def quality_dataset() -> dict:
    """导出人工标签样本（含 14 维特征），供离线再训练消费；不触发任何预测。"""
    return ok(quality_service.dataset())


@router.post("/api/quality/calibrate", response_model=schemas.CalibrateResponse)
def quality_calibrate(body: CalibrateRequest | None = None) -> dict:
    """按人工标签校准高风险阈值并落库；样本不足时只报告不写入。"""
    model_name = body.model_name if body is not None else None
    return ok(quality_service.calibrate(model_name))
