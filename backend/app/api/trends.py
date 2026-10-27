"""查询接口 3：缺陷引入趋势（契约三 1.5 第 3 节）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select

from app import schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Commit, Prediction
from app.services import settings as runtime_settings
from app.services.commits import default_model_in_table
from app.timeutil import parse_time_param

router = APIRouter(dependencies=[Depends(require_api_key)])

# MySQL 的 ISO 周（%x=ISO 年、%v=ISO 周）与自然月，都是零填充，字典序即时间序
_PERIOD_FORMAT = {"week": "%x-W%v", "month": "%Y-%m"}


def _period(committed_at, granularity: str) -> str:
    """非 MySQL 方言（仅单测兼容）的回退实现：Python 侧分桶。"""
    if granularity == "week":
        year, week, _ = committed_at.isocalendar()
        return f"{year}-W{week:02d}"
    return f"{committed_at.year:04d}-{committed_at.month:02d}"


def build_aggregate_stmt(base, granularity: str, high: float):
    """MySQL 侧的聚合语句：分桶 / 计数 / 均值 / 高风险计数全部下推到 SQL。

    单测跑 SQLite（不支持 `date_format`）走不到这条路径，故抽成纯函数，
    由 `test_trends_sql.py` 用 MySQL 方言编译后断言 SQL 结构 —— 否则生产唯一
    使用的那条 SQL 在 CI 里一次都不会被执行。
    """
    period = func.date_format(Commit.committed_at, _PERIOD_FORMAT[granularity])
    return (
        base.with_only_columns(
            period.label("period"),
            func.count().label("cnt"),
            func.avg(Prediction.risk_score).label("avg_risk"),
            func.sum(case((Prediction.risk_score >= high, 1), else_=0)).label("high_cnt"),
        )
        .group_by(period)
        .order_by(period)
    )


@router.get("/api/trends", response_model=schemas.TrendsResponse)
def trends(
    granularity: str = Query(default="week"),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
) -> dict:
    if granularity not in ("week", "month"):
        raise AppError(40001, "参数非法：granularity 取值需为 week 或 month")
    start = parse_time_param(start_time, "start_time") if start_time else None
    end = parse_time_param(end_time, "end_time", "end") if end_time else None
    # 阈值只读一次（此前在逐行循环里反复取）
    high = runtime_settings.high_threshold()

    with SessionLocal() as session:
        model = model_name or default_model_in_table(session)
        is_mysql = session.bind is not None and session.bind.dialect.name == "mysql"

        base = select(Prediction.risk_score, Commit.committed_at).join(
            Commit, Commit.commit_hash == Prediction.commit_hash
        )
        if model is not None:
            base = base.where(Prediction.model_name == model)
        if start is not None:
            base = base.where(Commit.committed_at >= start)
        if end is not None:
            base = base.where(Commit.committed_at <= end)

        if is_mysql:
            # 聚合下推到 SQL：不把整表（8.4 万行 × 单模型）搬进 Python 再分桶，
            # 也不套派生表（MySQL 8 虽能合并，直接 GROUP BY 表达式执行计划更可控）
            stmt = build_aggregate_stmt(base, granularity, high)
            series = [
                {
                    "period": row.period,
                    "commit_count": int(row.cnt),
                    "avg_risk": round(float(row.avg_risk), 4),
                    "high_risk_count": int(row.high_cnt or 0),
                }
                for row in session.execute(stmt).all()
            ]
        else:
            buckets: dict[str, list[float]] = {}
            for risk_score, committed_at in session.execute(base).all():
                buckets.setdefault(_period(committed_at, granularity), []).append(float(risk_score))
            series = [
                {
                    "period": period_key,
                    "commit_count": len(scores),
                    "avg_risk": round(sum(scores) / len(scores), 4),
                    "high_risk_count": sum(1 for score in scores if score >= high),
                }
                for period_key, scores in sorted(buckets.items())
            ]
    return ok({"granularity": granularity, "model_name": model, "series": series})
