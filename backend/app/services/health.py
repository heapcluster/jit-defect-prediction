"""运行状态聚合（observability capability）。

只返回进程内可算的指标；DB 不可达时降级为 `degraded`，细节只进服务端日志，
响应 `MUST NOT` 回显连接串、口令或堆栈。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select, text

from app import model_registry
from app.db import SessionLocal
from app.models import Commit, CommitLabel, Prediction
from app.timeutil import iso_z, now_naive_utc

logger = logging.getLogger("backend.health")


def liveness() -> dict:
    """liveness 探针：只证明进程活着，**不碰 DB**（DB 挂了不该重启进程）。"""
    return {"status": "ok", "server_time": iso_z(now_naive_utc())}


def readiness() -> dict:
    """readiness 探针：DB 通 + 至少加载一个模型才算就绪。"""
    db_up = True
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 —— 探针不能抛错，只报告状态
        logger.exception("readiness: database unreachable")
        db_up = False
    models_loaded = len(model_registry.all_models())
    return {
        "status": "ok" if (db_up and models_loaded) else "degraded",
        "db": "up" if db_up else "down",
        "models_loaded": models_loaded,
        "server_time": iso_z(now_naive_utc()),
    }


def snapshot() -> dict:
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
        logger.exception("health check: database unreachable")
        db_up = False
    model_names = [entry.name for entry in model_registry.all_models()]
    # last_sync_at 取同步状态快照（进程重启后为 null）
    from app.api.sync import get_sync_state

    return {
        "status": "ok" if (db_up and model_names) else "degraded",
        "db": "up" if db_up else "down",
        "models_loaded": len(model_names),
        "model_names": model_names,
        "commit_count": int(commit_count),
        "prediction_count": int(prediction_count),
        "labeled_count": int(labeled_count),
        "last_sync_at": iso_z(get_sync_state().get("started_at")),
        "server_time": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
