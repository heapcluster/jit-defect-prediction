"""应用入口：uvicorn app.main:app（自 backend/ 目录）。"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers

from app import config, db, model_registry
from app.api import (
    clean,
    collect,
    commits,
    datasets,
    evaluate,
    explain,
    figures,
    health,
    jobs,
    models,
    predict,
    source,
    storage,
    storage_catalog,
    sync,
    train,
)
from app.api import config as config_api
from app.auth import MISSING_OR_INVALID_TOKEN
from app.errors import AppError, error_payload, register_error_handlers
from app.services import (
    clean_run,
    collect_run,
    evaluate_run,
    explain_run,
    figure_store,
    job_store,
    model_manage,
    predict_run,
    train_run,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("backend.main")


MAX_IMPORT_BODY_BYTES = 65 * 1024 * 1024


class _ApiAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(("/api/", "/static/")):
            return await self.app(scope, receive, send)
        headers = Headers(scope=scope)
        if not config.API_TOKEN or headers.get("x-api-key") != config.API_TOKEN:
            response = JSONResponse(status_code=401, content=error_payload(40100, MISSING_OR_INVALID_TOKEN))
            return await response(scope, receive, send)
        if scope["path"] not in {"/api/storage/import", "/api/collect/run", "/api/clean/run", "/api/train/run", "/api/predict/run", "/api/evaluate/run", "/api/explain/run", "/api/localize/run"} or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        # 在 multipart 解析与临时文件写入前限制整个请求，包括 chunked 上传。
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > MAX_IMPORT_BODY_BYTES:
                response = JSONResponse(status_code=400, content=error_payload(40001, "上传请求超过总大小限制"))
                return await response(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


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
    # 启动即补齐历史库结构（create_all + 幂等列/索引升级），避免旧库缺列导致任务恢复失败。
    db.init_db()
    with db.SessionLocal() as session:
        job_store.recover_running(session)
    model_registry.load_models()
    model_registry.warmup()
    # 启动时把已加载模型元数据 upsert 进 model 表（供 FK 与查询，空库首启也需补齐）。
    # 在线权重仅 expert 线交付，故 line 恒为 expert（semantic 由数据登记导入）。
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
    collect_run.dispatch()
    clean_run.dispatch()
    with db.SessionLocal() as session:
        train_run.ensure_algorithms(session)
    train_run.dispatch()
    with db.SessionLocal() as session:
        choice = model_manage.selected(session)
        if choice:
            try:
                model_manage.load(session, choice)
            except AppError:
                logger.warning("startup selected model load skipped: %s", choice)
    predict_run.dispatch()
    evaluate_run.dispatch()
    explain_run.dispatch()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JIT 缺陷预测系统 API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)
    app.add_middleware(_ApiAuthMiddleware)
    app.include_router(collect.router)
    app.include_router(clean.router)
    app.include_router(train.router)
    app.include_router(evaluate.router)
    app.include_router(explain.router)
    app.include_router(source.router)
    app.include_router(commits.router)
    app.include_router(models.router)
    app.include_router(predict.router)
    app.include_router(sync.router)
    app.include_router(figures.router)
    app.include_router(health.router)
    app.include_router(config_api.router)
    app.include_router(jobs.router)
    app.include_router(storage_catalog.router)
    app.include_router(storage.router)
    app.include_router(datasets.router)
    # 模型性能图集：<img> 带不了 X-API-Key，前端 fetch（带鉴权头）取二进制转 ObjectURL 渲染。
    # 目录不入库（干净检出为空），启动时先建目录再把仓库内图集落地，避免 mount 直接 RuntimeError。
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure_store.sync_figures()
    app.mount("/static", StaticFiles(directory=str(config.FIGURES_DIR.parent)), name="static")
    return app


app = create_app()
