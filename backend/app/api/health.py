"""健康检查路由：GET /api/health（observability capability）。

数据聚合在 `app/services/health.py`，本文件只做响应包络。健康检查本身不抛 50000：
DB 不可达时降级为 `degraded`，HTTP 仍为 200。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import schemas
from app.auth import require_api_key
from app.errors import ok
from app.services import health as health_service

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/api/health", response_model=schemas.HealthResponse)
def health() -> dict:
    return ok(health_service.snapshot())
