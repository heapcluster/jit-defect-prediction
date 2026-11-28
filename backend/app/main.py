"""应用入口。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.api import (
    auth,
    clean,
    collect,
    datasets,
    evaluate,
    health,
    jobs,
    page_state,
    predict,
    storage,
    train,
)
from app.cli import seed_algorithms
from app.errors import register_error_handlers
from app.services import artifacts, jobs as job_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    artifacts.ensure_dirs()
    try:
        db.init_db()
        seed_algorithms()
        job_service.manager.recover()
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("backend").warning("数据库初始化失败：%s", exc)
    yield


app = FastAPI(title="JIT 缺陷预测", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

API = "/api"
app.include_router(health.router, prefix=API)
for router in (
    auth.router,
    jobs.router,
    datasets.router,
    storage.router,
    page_state.router,
    collect.router,
    clean.router,
    train.router,
    predict.router,
    evaluate.router,
):
    app.include_router(router, prefix=API)
