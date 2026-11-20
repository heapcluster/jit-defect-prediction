"""模型性能图与指标接口：GET /api/figures?model_name=（docs/api/figures.md）。

返回该模型的指标数值（model_metrics.csv）+ 逐模型图清单（model_figure 表）；
图片本体由 StaticFiles 挂载在 /static/figures/... 下，前端带鉴权头 fetch 后转 ObjectURL。
"""

from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import config, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Model, ModelFigure

router = APIRouter(dependencies=[Depends(require_api_key)])

# 图集固定展示顺序（docs/api/figures.md）
_FIGURE_ORDER = ("roc", "pr", "confusion", "calibration", "effort", "feat_importance")


def _load_metrics() -> dict[str, dict]:
    """逐模型指标数值（data_model/evaluation/out/model_metrics.csv）；文件缺失时返回空表。"""
    path = config.MODEL_METRICS_CSV
    if not path.is_file():
        return {}
    out: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("model_name") or "").strip()
            if not name:
                continue
            out[name] = {
                "auc": float(row["auc"]),
                "ap": float(row["ap"]),
                "f1": float(row["f1"]),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "accuracy": float(row["accuracy"]),
                "n": int(row["n"]),
                "pos_rate": float(row["pos_rate"]),
            }
    return out


def _local_file(file_path: str) -> Path | None:
    """把契约里的 `/static/...` URL 还原成磁盘路径；越界路径一律视为不存在。"""
    prefix = "/static/"
    if not file_path.startswith(prefix):
        return None
    relative = Path(file_path[len(prefix) :])
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return config.FIGURES_DIR.parent / relative


@router.get("/api/figures", response_model=schemas.FiguresResponse)
def figures(model_name: str = Query(default=...)) -> dict:
    if not model_name:
        raise AppError(40001, "参数非法：缺少 model_name")
    with SessionLocal() as session:
        model = session.execute(
            select(Model).where(Model.model_name == model_name)
        ).scalar_one_or_none()
        rows = (
            session.execute(select(ModelFigure).where(ModelFigure.model_name == model_name))
            .scalars()
            .all()
        )
    if model is None or not rows:
        raise AppError(40400, "model figures not found")
    by_type = {f.figure_type: f for f in rows}
    figures_list = []
    missing: list[str] = []
    for figure_type in _FIGURE_ORDER:
        row = by_type.get(figure_type)
        if row is None:
            continue
        local = _local_file(row.file_path)
        if local is None or not local.is_file():
            missing.append(row.file_path)
            continue
        figures_list.append(
            {"figure_type": figure_type, "title": row.title, "file_path": row.file_path}
        )
    data = {
        "model_name": model_name,
        "line": model.line,
        "metrics": _load_metrics().get(model_name),
        "figures": figures_list,
        "missing": missing,
    }
    return ok(data)
