"""查询接口 1–2：风险列表与提交详情（契约三 1.3 第 1、2 节）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config, model_registry, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError
from app.models import Commit, CommitFeature, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

HASH_HEX = "0123456789abcdef"


def _iso_z(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str, param: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AppError(40001, f"参数非法：{param} 需为 ISO 8601 时间") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _check_hash(commit_hash: str) -> None:
    if len(commit_hash) != 40 or any(c not in HASH_HEX for c in commit_hash.lower()):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")


def default_model_in_table(session: Session) -> str | None:
    """「默认最新」单一定义（审 2）：表内模型按 version_key 版本序取最大者。"""
    names = session.execute(select(Prediction.model_name).distinct()).scalars().all()
    return max(names, key=model_registry.version_key) if names else None


def _feature_dict(feature: CommitFeature | None) -> dict | None:
    if feature is None:
        return None
    out = {}
    for name in config.FEATURE_COLUMNS:
        value = getattr(feature, name)
        out[name] = int(value) if name == "fix" else float(value)
    return out


def _explanation_for(model_name: str | None, feature: CommitFeature | None) -> list[dict]:
    if not model_name or feature is None or not model_registry.has(model_name):
        return []
    vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
    return model_registry.explain(model_registry.get_model(model_name), vector)


@router.get("/api/commits", response_model=schemas.CommitsResponse)
def list_commits(
    page: int = Query(default=1),
    size: int = Query(default=20),
    min_risk: float | None = Query(default=None),
    model_name: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
) -> dict:
    if page < 1:
        raise AppError(40001, "参数非法：page 需 >= 1")
    if size < 1 or size > 100:
        raise AppError(40001, "参数非法：size 超过上限 100")
    if min_risk is not None and not 0.0 <= min_risk <= 1.0:
        raise AppError(40001, "参数非法：min_risk 需在 0.0 ~ 1.0")
    start = _parse_time(start_time, "start_time") if start_time else None
    end = _parse_time(end_time, "end_time") if end_time else None

    with SessionLocal() as session:
        model = model_name or default_model_in_table(session)
        stmt = select(Prediction, Commit).join(Commit, Commit.commit_hash == Prediction.commit_hash)
        if model is not None:
            stmt = stmt.where(Prediction.model_name == model)
        if min_risk is not None:
            stmt = stmt.where(Prediction.risk_score >= min_risk)
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        window = session.execute(
            stmt.order_by(Prediction.risk_score.desc()).offset((page - 1) * size).limit(size)
        ).all()
        items = [
            {
                "commit_hash": commit.commit_hash,
                "author_name": commit.author_name,
                "committed_at": _iso_z(commit.committed_at),
                "message": commit.message,
                "risk_score": float(prediction.risk_score),
                "model_name": prediction.model_name,
            }
            for prediction, commit in window
        ]
    return {"code": 0, "message": "ok", "data": {"total": total, "page": page, "size": size, "items": items}}


@router.get("/api/commits/{commit_hash}", response_model=schemas.DetailResponse)
def commit_detail(commit_hash: str) -> dict:
    _check_hash(commit_hash)
    with SessionLocal() as session:
        commit = session.execute(select(Commit).where(Commit.commit_hash == commit_hash)).scalar_one_or_none()
        if commit is None:
            raise AppError(40400, "commit not found")
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()
        prediction = session.execute(
            select(Prediction).where(
                Prediction.commit_hash == commit_hash,
                Prediction.model_name == default_model_in_table(session),
            )
        ).scalar_one_or_none()
        # design D3：提交存在但无预测记录 → code=0 + null 字段（契约三待补记口径）
        data = {
            "commit_hash": commit.commit_hash,
            "author_name": commit.author_name,
            "committed_at": _iso_z(commit.committed_at),
            "message": commit.message,
            "risk_score": float(prediction.risk_score) if prediction else None,
            "model_name": prediction.model_name if prediction else None,
            "features": _feature_dict(feature),
            "explanation": _explanation_for(prediction.model_name if prediction else None, feature),
        }
    return {"code": 0, "message": "ok", "data": data}
