"""模型清单接口：GET /api/models（docs/api/models.md）。

登记源为 `model_artifact` 表（docs/api/models.md §1、docs/database/model_artifact.md）：
`model` 行由工件派生，选择器只列 available 工件，retired 不可选；只读，不触发加载。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app import schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import ModelArtifact
from app.services import model_manage

router = APIRouter(dependencies=[Depends(require_api_key)])

# 架构中文显示名：后端常量映射，不落库（docs/database/model.md）
LINE_LABELS = {"expert": "专家特征", "semantic": "语义"}
LINE_ORDER = ("expert", "semantic")


@router.get("/api/models", response_model=schemas.ModelsResponse)
def list_models(line: str | None = Query(default=None)) -> dict:
    if line is not None and line not in LINE_ORDER:
        raise AppError(40001, "参数非法：line 取值需为 expert / semantic")
    with SessionLocal() as session:
        # 唯一登记源是 model_artifact；model 行只是它的派生结果，不能反向当清单源。
        # retired 工件保留追溯但不可选；load_failed 仍是登记工件，沿用 status 口径由 status 端点暴露失败态。
        stmt = select(ModelArtifact.model_name, ModelArtifact.line).where(
            ModelArtifact.status == "available"
        )
        if line is not None:
            stmt = stmt.where(ModelArtifact.line == line)
        rows = session.execute(stmt).all()
    grouped: dict[str, list[str]] = {name: [] for name in LINE_ORDER}
    for model_name, model_line in rows:
        if model_line in grouped:
            grouped[model_line].append(model_name)
    lines = [
        {"line": name, "label": LINE_LABELS[name], "models": sorted(grouped[name])}
        for name in LINE_ORDER
        if line is None or name == line
    ]
    return ok({"lines": lines})


@router.get("/api/models/status")
def models_status(line: str | None = Query(default=None), model_name: str | None = Query(default=None)) -> dict:
    with SessionLocal() as session:
        return ok(model_manage.status(session, line=line, model_name=model_name))


async def _no_body(request: Request) -> None:
    if request.query_params or await request.body():
        raise AppError(40001, "参数非法：此操作不接受请求体或查询参数")


@router.post("/api/models/{name}/load")
async def load_model(name: str, request: Request) -> dict:
    await _no_body(request)
    with SessionLocal() as session:
        return ok(model_manage.load(session, name))


@router.post("/api/models/{name}/unload")
async def unload_model(name: str, request: Request) -> dict:
    await _no_body(request)
    with SessionLocal() as session:
        return ok(model_manage.unload(session, name))


@router.post("/api/models/{name}/reload")
async def reload_model(name: str, request: Request) -> dict:
    await _no_body(request)
    with SessionLocal() as session:
        return ok(model_manage.reload(session, name))


@router.put("/api/models/selection")
async def set_selection(request: Request) -> dict:
    body = await request.json()
    if not isinstance(body, dict) or set(body) != {"model_name"} or not isinstance(body.get("model_name"), str):
        raise AppError(40001, "参数非法：仅接受 model_name")
    with SessionLocal() as session:
        return ok(model_manage.set_selection(session, body["model_name"]))


@router.put("/api/models/default")
async def set_default_deprecated(request: Request) -> dict:
    raise AppError(40001, "default 端点已废止，请显式选择模型")
