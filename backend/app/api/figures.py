"""模型性能图与指标接口：GET /api/figures?model_name=（docs/api/figures.md）。

返回该模型的指标数值（model_metrics.csv）+ 逐模型图清单（model_figure 表）；
图片本体由 StaticFiles 挂载在 /static/figures/... 下，前端带鉴权头 fetch 后转 ObjectURL。
"""

from __future__ import annotations

import csv

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


@router.get("/api/figures", response_model=schemas.FiguresResponse)
def figures(model_name: str = Query(default=...)) -> dict:
    if not model_name:
        raise AppError(40001, "参数非法：缺少 model_name")
    with SessionLocal() as session:
        model = session.execute(
            select(Model).where(Model.model_name == model_name)
        ).scalar_one_or_none()
        rows = session.execute(
            select(ModelFigure).where(ModelFigure.model_name == model_name)
        ).scalars().all()
    if model is None or not rows:
        raise AppError(40400, "model figures not found")
    by_type = {f.figure_type: f for f in rows}
    figures_list = [
        {"figure_type": t, "title": by_type[t].title, "file_path": by_type[t].file_path}
        for t in _FIGURE_ORDER
        if t in by_type
    ]
    data = {
        "model_name": model_name,
        "line": model.line,
        "metrics": _load_metrics().get(model_name),
        "figures": figures_list,
    }
    return ok(data)
