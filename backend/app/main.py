"""应用入口：uvicorn app.main:app（自 backend/ 目录）。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import model_registry
from app.api import commits, predict, trends
from app.db import get_engine
from app.errors import register_error_handlers

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    get_engine()
    model_registry.load_models()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JIT 缺陷预测系统 API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)
    app.include_router(commits.router)
    app.include_router(trends.router)
    app.include_router(predict.router)
    return app


app = create_app()
