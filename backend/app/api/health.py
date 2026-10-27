"""健康检查路由（observability capability + ops-hardening 拆探针）。

三个端点职责严格区分：
- `GET /api/health`：完整运行状态（人看的），含计数与同步时间；
- `GET /api/health/live`：liveness，只证明进程活着，**不碰 DB**（DB 挂了不该重启进程）；
- `GET /api/health/ready`：readiness，DB 通 + 模型已加载才就绪（K8s 用它摘流量）。

三者都不抛 50000：探测失败是「状态」，不是「错误」。
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


@router.get("/api/health/live", response_model=schemas.LiveResponse)
def health_live() -> dict:
    return ok(health_service.liveness())


@router.get("/api/health/ready", response_model=schemas.ReadyResponse)
def health_ready() -> dict:
    return ok(health_service.readiness())
