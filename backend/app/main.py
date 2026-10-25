"""应用入口：uvicorn app.main:app（自 backend/ 目录）。"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config, model_registry
from app.api import commits, predict, sync, trends
from app.db import get_engine
from app.errors import register_error_handlers

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("backend.main")


def _startup_sync_if_enabled() -> None:
    """config.SYNC_ON_STARTUP=1 时后台预同步最新提交（失败只记日志，不阻塞启动）。"""
    if not config.SYNC_ON_STARTUP:
        return
    if not config.SOURCE_REPO:
        logger.warning("SYNC_ON_STARTUP=1 but SOURCE_REPO is not configured")
        return

    def _run() -> None:
        try:
            data = sync.sync_recent(limit=10)
            logger.info("startup sync: new=%s skipped=%s", data["new"], len(data["skipped"]))
        except Exception:
            logger.exception("startup sync failed")

    threading.Thread(target=_run, daemon=True, name="startup-sync").start()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    get_engine()
    model_registry.load_models()
    _startup_sync_if_enabled()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JIT 缺陷预测系统 API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)
    app.include_router(commits.router)
    app.include_router(trends.router)
    app.include_router(predict.router)
    app.include_router(sync.router)
    return app


app = create_app()
