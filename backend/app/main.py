"""应用入口：uvicorn app.main:app（自 backend/ 目录）。"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app import config, db, model_registry
from app.api import commits, figures, health, models, predict, sync, trends
from app.auth import MISSING_OR_INVALID_TOKEN
from app.errors import error_payload, register_error_handlers

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("backend.main")


class _StaticAuthMiddleware(BaseHTTPMiddleware):
    """`/static/figures` 图集也要求 X-API-Key（docs/api/figures.md：不许为 `<img>` 开免鉴权）。"""

    async def dispatch(self, request, call_next):
        if request.url.path.startswith("/static/"):
            if request.headers.get("x-api-key") != config.API_TOKEN:
                return JSONResponse(
                    status_code=401, content=error_payload(40100, MISSING_OR_INVALID_TOKEN)
                )
        return await call_next(request)


def _startup_sync_if_enabled() -> None:
    """config.SYNC_ON_STARTUP=1 时后台同步（失败只记日志，不阻塞启动）。

    首启（prediction 空）建基线（SYNC_INITIAL_LIMIT 条）；否则追到 HEAD。
    """
    if not config.SYNC_ON_STARTUP:
        return
    if not config.SOURCE_REPO:
        logger.warning("SYNC_ON_STARTUP=1 but SOURCE_REPO is not configured")
        return

    def _run() -> None:
        try:
            data = sync.run_startup_sync()
            logger.info(
                "startup sync done: mode=%s new=%s skipped=%s",
                data.get("mode"),
                data.get("new"),
                len(data.get("skipped", [])),
            )
        except Exception:
            logger.exception("startup sync failed")

    threading.Thread(target=_run, daemon=True, name="startup-sync").start()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    db.get_engine()
    model_registry.load_models()
    # 启动时把已加载模型元数据 upsert 进 model 表（供 FK 与查询，空库首启也需补齐）。
    # 在线权重仅 expert 线交付，故 line 恒为 expert（语义/融合/e2e 由 data_init.sql 导入）。
    entries = []
    for entry in model_registry.all_models():
        entries.append(
            {
                "model_name": entry.name,
                "line": "expert",
                "version_key": "".join(map(str, model_registry.version_key(entry.name))),
                "algo": type(entry.model).__name__,
                "feature_version": None,
                "trained_at": datetime.fromtimestamp(entry.mtime, tz=UTC).replace(tzinfo=None),
            }
        )
    try:
        db.ensure_model_rows(entries)
    except Exception:
        logger.exception("ensure model rows failed")
    _startup_sync_if_enabled()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JIT 缺陷预测系统 API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)
    app.add_middleware(_StaticAuthMiddleware)
    app.include_router(commits.router)
    app.include_router(models.router)
    app.include_router(trends.router)
    app.include_router(predict.router)
    app.include_router(sync.router)
    app.include_router(figures.router)
    app.include_router(health.router)
    # 模型性能图集：<img> 带不了 X-API-Key，前端 fetch（带鉴权头）取二进制转 ObjectURL 渲染
    app.mount("/static", StaticFiles(directory=str(config.FIGURES_DIR.parent)), name="static")
    return app


app = create_app()
