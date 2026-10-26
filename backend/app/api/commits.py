"""查询接口 1–2：风险列表与提交详情（契约三 1.5 第 1、2 节）。"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config, model_registry, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Commit, CommitFeature, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

HASH_HEX = "0123456789abcdef"


def _iso_z(value: datetime) -> str:
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str, param: str, role: str = "start") -> datetime:
    # 紧凑基本格式一律拒（含 Z/偏移后缀变体，#62 复审 1+3）：头 8 位数字后接 T 或
    # 结束即基本格式；fromisoformat 收但它绕过纯日期串判定，end 会静默停 00:00
    if re.fullmatch(r"\d{8}(T\S*)?", value):
        raise AppError(
            40001, f"参数非法：{param} 不接受紧凑基本格式，请用 YYYY-MM-DD 或带分隔符的 ISO 8601"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AppError(40001, f"参数非法：{param} 需为 ISO 8601 时间") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    # 契约三 1.5 区间语义（#61）：闭区间；end 侧纯日期串含结束日全天，
    # start 侧纯日期串仍是当天 00:00:00（不能一刀切）；带时间分量按原样
    if role == "end" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    return parsed


def _check_hash(commit_hash: str) -> str:
    """校验并归一化 40 位十六进制哈希；调用方必须用返回值查库（D-09）。"""
    if len(commit_hash) != 40 or any(c not in HASH_HEX for c in commit_hash.lower()):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")
    return commit_hash.lower()


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
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
) -> dict:
    if page < 1:
        raise AppError(40001, "参数非法：page 需 >= 1")
    if size < 1 or size > 100:
        raise AppError(40001, "参数非法：size 超过上限 100")
    if min_risk is not None and not 0.0 <= min_risk <= 1.0:
        raise AppError(40001, "参数非法：min_risk 需在 0.0 ~ 1.0")
    # 查看过滤：since/until 与 start_time/end_time 同为按 committed_at 过滤的别名，均不触发预测
    start = _parse_time((since or start_time), "start_time") if (since or start_time) else None
    end = _parse_time((until or end_time), "end_time", "end") if (until or end_time) else None

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
            # risk_score 相同时按 commit_hash 兜底排序：等值分页跨页才不会重复/漏行
            stmt.order_by(Prediction.risk_score.desc(), Prediction.commit_hash.asc())
            .offset((page - 1) * size)
            .limit(size)
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
    return ok({"total": total, "page": page, "size": size, "items": items})


@router.get("/api/commits/coverage")
def commits_coverage() -> dict:
    """已预测时间覆盖区间：每个 model_name 的 [min_committed_at, max_committed_at]，供前端展示缺口。

    纯只读、不触发预测；前端据此显示「已预测覆盖：起 ~ 止」并引导用户用「补齐到最新」补齐缺口。
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Prediction.model_name,
                func.min(Commit.committed_at),
                func.max(Commit.committed_at),
            )
            .join(Commit, Commit.commit_hash == Prediction.commit_hash)
            .group_by(Prediction.model_name)
        ).all()
        items = [
            {
                "model_name": m,
                "start": _iso_z(mn) if mn else None,
                "end": _iso_z(mx) if mx else None,
            }
            for m, mn, mx in rows
        ]
    return ok({"items": items})


@router.get("/api/commits/{commit_hash}", response_model=schemas.DetailResponse)
def commit_detail(commit_hash: str) -> dict:
    # 库内哈希是小写：校验放行大写形式，查询就必须用归一化值，否则误报 commit not found（D-09）
    commit_hash = _check_hash(commit_hash)
    with SessionLocal() as session:
        commit = session.execute(
            select(Commit).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
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
        if prediction is None:
            # 新提交可能只由在线模型预测，而历史表默认模型不同；详情不能因此假装未预测。
            available = (
                session.execute(select(Prediction).where(Prediction.commit_hash == commit_hash))
                .scalars()
                .all()
            )
            prediction = (
                max(available, key=lambda row: model_registry.version_key(row.model_name))
                if available
                else None
            )
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
    return ok(data)
