"""健康检查与运行状态：GET /api/health（observability capability）。

供容器编排 readiness / liveness 与人工排障使用。只返回进程内可算的指标，
`MUST NOT` 回显连接串、口令、堆栈或文件路径（沿用契约三对内部错误的要求）。
健康检查本身不抛 50000：DB 不可达时降级为 `degraded` 且 HTTP 仍为 200。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text

from app import model_registry, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import ok
from app.models import Commit, CommitLabel, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger("backend.health")


def _iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


@router.get("/api/health", response_model=schemas.HealthResponse)
def health() -> dict:
    db_up = True
    commit_count = prediction_count = labeled_count = 0
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            commit_count = session.scalar(select(func.count()).select_from(Commit)) or 0
            prediction_count = (
                session.scalar(select(func.count()).select_from(Prediction)) or 0
            )
            labeled_count = session.scalar(select(func.count()).select_from(CommitLabel)) or 0
    except Exception:
        # 细节只进服务端日志；响应只说 down，绝不回显连接串
        logger.exception("health check: database unreachable")
        db_up = False
    model_names = [entry.name for entry in model_registry.all_models()]
    status = "ok" if (db_up and model_names) else "degraded"
    # last_sync_at 取同步状态快照（进程重启后为 null）
    from app.api.sync import get_sync_state

    return ok(
        {
            "status": status,
            "db": "up" if db_up else "down",
            "models_loaded": len(model_names),
            "model_names": model_names,
            "commit_count": int(commit_count),
            "prediction_count": int(prediction_count),
            "labeled_count": int(labeled_count),
            "last_sync_at": _iso_z(get_sync_state().get("started_at")),
            "server_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
