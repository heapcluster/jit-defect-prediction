"""模型清单接口：GET /api/models（docs/api/models.md）。

数据来源 `model` 表（model_name / line），按 line 分组，只读；「架构 → 模型」两级
级联选择器的唯一数据源，前端不写死清单。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Model

router = APIRouter(dependencies=[Depends(require_api_key)])

# 架构中文显示名：后端常量映射，不落库（docs/database/model.md）
LINE_LABELS = {"expert": "专家特征", "semantic": "语义", "fused": "融合", "e2e": "端到端"}
LINE_ORDER = ("expert", "semantic", "fused", "e2e")


@router.get("/api/models", response_model=schemas.ModelsResponse)
def list_models(line: str | None = Query(default=None)) -> dict:
    if line is not None and line not in LINE_ORDER:
        raise AppError(40001, "参数非法：line 取值需为 expert / semantic / fused / e2e")
    with SessionLocal() as session:
        stmt = select(Model.model_name, Model.line)
        if line is not None:
            stmt = stmt.where(Model.line == line)
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
