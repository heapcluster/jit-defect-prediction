"""查询接口 3：缺陷引入趋势（契约三 v1.2 第 3 节）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import config, schemas
from app.api.commits import _parse_time, latest_model_in_table
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError
from app.models import Commit, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])


def _period(committed_at, granularity: str) -> str:
    if granularity == "week":
        year, week, _ = committed_at.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{committed_at.year:04d}-{committed_at.month:02d}"


@router.get("/api/trends", response_model=schemas.TrendsResponse)
def trends(
    granularity: str = Query(default="week"),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
) -> dict:
    if granularity not in ("week", "month"):
        raise AppError(40001, "参数非法：granularity 取值需为 week 或 month")
    start = _parse_time(start_time, "start_time") if start_time else None
    end = _parse_time(end_time, "end_time") if end_time else None

    with SessionLocal() as session:
        model = model_name or latest_model_in_table(session)
        stmt = select(Prediction, Commit).join(Commit, Commit.commit_hash == Prediction.commit_hash)
        if model is not None:
            stmt = stmt.where(Prediction.model_name == model)
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        rows = session.execute(stmt).all()

    buckets: dict[str, list[float]] = {}
    for prediction, commit in rows:
        buckets.setdefault(_period(commit.committed_at, granularity), []).append(float(prediction.risk_score))
    series = [
        {
            "period": period,
            "commit_count": len(scores),
            "avg_risk": round(sum(scores) / len(scores), 4),
            "high_risk_count": sum(1 for score in scores if score >= config.HIGH_RISK_THRESHOLD),
        }
        for period, scores in sorted(buckets.items())
    ]
    return {
        "code": 0,
        "message": "ok",
        "data": {"granularity": granularity, "model_name": model, "series": series},
    }
