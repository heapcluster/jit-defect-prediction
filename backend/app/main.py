"""应用入口：uvicorn app.main:app（自 backend/ 目录）。"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app import config, db, model_registry
from app.api import commits, predict, prs, sync, trends
from app.errors import register_error_handlers

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("backend.main")


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
    # 启动时把已加载模型元数据 upsert 进 model 表（供 FK 与查询，空库首启也需补齐）
    entries = []
    for entry in model_registry.all_models():
        entries.append(
            {
                "model_name": entry.name,
                "version_key": "".join(map(str, model_registry.version_key(entry.name))),
                "algo": type(entry.model).__name__,
                "feature_version": None,
                "trained_at": datetime.fromtimestamp(entry.mtime, tz=timezone.utc).replace(
                    tzinfo=None
                ),
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
    app.include_router(commits.router)
    app.include_router(trends.router)
    app.include_router(predict.router)
    app.include_router(sync.router)
    app.include_router(prs.router)
    return app


app = create_app()
