"""人工反馈闭环路由：PUT /api/commits/{commit_hash}/label（feedback capability）。

业务与数据访问在 `app/services/feedback.py`，本文件只做入参校验与响应包络。
错误码只用契约三规定的 5 个（0 / 40001 / 40100 / 40400 / 50000）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import schemas
from app.auth import require_api_key
from app.errors import ok
from app.services import feedback as feedback_service
from app.validate import normalize_commit_hash

router = APIRouter(dependencies=[Depends(require_api_key)])


class LabelRequest(BaseModel):
    is_defect: bool


@router.put("/api/commits/{commit_hash}/label", response_model=schemas.LabelResponse)
def put_commit_label(commit_hash: str, body: LabelRequest) -> dict:
    """写入或更新人工标签：撤销 = 再次提交 `is_defect=false`（保留「已确认非缺陷」事实）。"""
    return ok(feedback_service.put_label(normalize_commit_hash(commit_hash), body.is_defect))
