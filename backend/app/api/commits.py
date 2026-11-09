"""查询接口 1–2：风险列表与提交详情（docs/api/commits.md）。

本文件只做入参校验与响应编排；查询与字段组装收在 `app/services/commits.py`，
时间格式收在 `app/timeutil.py`，哈希校验收在 `app/validate.py`。
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app import config, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Commit, CommitFeature, Prediction
from app.services import commits as commit_service
from app.timeutil import iso_z, parse_time_param
from app.validate import normalize_commit_hash

router = APIRouter(dependencies=[Depends(require_api_key)])

# 全 hex（1~40 位）输入按哈希前缀查：走 commit_hash 的唯一索引，不做三列全表匹配
_HEX_PREFIX = re.compile(r"^[0-9a-fA-F]{1,40}$")
# LIKE 转义符必须显式声明：不写 escape 等于没转义
_LIKE_ESCAPE = "\\"


def _like_term(raw: str) -> str:
    """把用户输入转成 LIKE 模式的安全片段（转义 % _ \\），配 `escape=` 一起用。"""
    escaped = raw.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
    escaped = escaped.replace("%", _LIKE_ESCAPE + "%").replace("_", _LIKE_ESCAPE + "_")
    return f"{escaped}%"


def _sizzle(value: int | None) -> int | None:
    """SZZ 真标签：库内 1 / 0 / NULL 原样对外（NULL 不是 0）。"""
    return int(value) if value is not None else None


@router.get("/api/commits", response_model=schemas.CommitsResponse)
def list_commits(
    page: int = Query(default=1),
    size: int = Query(default=20),
    model_name: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=64),
    with_features: str | None = Query(default=None),
    is_test: str | None = Query(default=None),
) -> dict:
    if page < 1:
        raise AppError(40001, "参数非法：page 需 >= 1")
    if size < 1 or size > 100:
        raise AppError(40001, "参数非法：size 超过上限 100")
    if with_features not in (None, "0", "1"):
        raise AppError(40001, "参数非法：with_features 需为 0 或 1")
    if is_test not in (None, "0", "1"):
        raise AppError(40001, "参数非法：is_test 需为 0 或 1")
    # 查看过滤：since/until 与 start_time/end_time 同为按 committed_at 过滤的别名，均不触发预测
    start = parse_time_param((since or start_time), "start_time") if (since or start_time) else None
    end = parse_time_param((until or end_time), "end_time", "end") if (until or end_time) else None
    want_features = with_features == "1"
    want_test = is_test == "1"

    with SessionLocal() as session:
        model = model_name or commit_service.default_model_in_table(session)
        stmt = (
            select(Prediction, Commit, CommitFeature)
            .join(Commit, Commit.commit_hash == Prediction.commit_hash)
            .outerjoin(CommitFeature, CommitFeature.commit_hash == Prediction.commit_hash)
        )
        if model is not None:
            stmt = stmt.where(Prediction.model_name == model)
        if want_test:
            stmt = stmt.where(CommitFeature.is_test == 1)
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        if q and q.strip():
            # 搜索：哈希前缀 / 作者 / 提交信息，三者取并集；纯查看过滤，不触发预测
            keyword = q.strip()
            term = _like_term(keyword)
            if _HEX_PREFIX.match(keyword):
                stmt = stmt.where(Commit.commit_hash.like(term, escape=_LIKE_ESCAPE))
            else:
                stmt = stmt.where(
                    or_(
                        Commit.commit_hash.like(term, escape=_LIKE_ESCAPE),
                        Commit.author_name.like(term, escape=_LIKE_ESCAPE),
                        Commit.message.like(term, escape=_LIKE_ESCAPE),
                    )
                )
        total = session.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        window = session.execute(
            # risk_score 相同时按 commit_hash 兜底排序：等值分页跨页才不会重复/漏行
            stmt.order_by(Prediction.risk_score.desc(), Prediction.commit_hash.asc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        items = []
        for prediction, commit, feature in window:
            item = {
                "commit_hash": commit.commit_hash,
                "author_name": commit.author_name,
                "committed_at": iso_z(commit.committed_at),
                "message": commit.message,
                "risk_score": float(prediction.risk_score),
                "model_name": prediction.model_name,
                "is_bug_inducing": _sizzle(feature.is_bug_inducing) if feature is not None else None,
            }
            if want_features:
                item["features"] = commit_service.feature_dict(feature)
            items.append(item)
    return ok({"total": total, "page": page, "size": size, "items": items})


@router.get("/api/commits/{commit_hash}", response_model=schemas.DetailResponse)
def commit_detail(commit_hash: str) -> dict:
    # 库内哈希是小写：校验放行大写形式，查询就必须用归一化值，否则误报 commit not found（D-09）
    commit_hash = normalize_commit_hash(commit_hash)
    with SessionLocal() as session:
        commit = session.execute(
            select(Commit).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if commit is None:
            raise AppError(40400, "commit not found")
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()
        default_model = commit_service.default_model_in_table(session)
        prediction = (
            session.execute(
                select(Prediction).where(
                    Prediction.commit_hash == commit_hash,
                    Prediction.model_name == default_model,
                )
            ).scalar_one_or_none()
            if default_model
            else None
        )
        # 提交存在但无预测记录 → code=0 + null 字段（risk_score / predicted_at）
        explanation = commit_service.explanation_for(
            prediction.model_name if prediction else None, feature
        )
        localization = commit_service.localization_for(explanation)
        diff_loc = commit_service.diff_localization_for(config.SOURCE_REPO, commit_hash)
        if diff_loc is not None:
            localization["level"] = "line"
            localization["files"] = diff_loc["files"]
            localization["truncated"] = diff_loc["truncated"]
            localization["notice"] = (
                "按提交级缺陷概率对新增代码行着色（无 per-line 模型，新增行即可疑行）"
            )
        data = {
            "commit_hash": commit.commit_hash,
            "author_name": commit.author_name,
            "committed_at": iso_z(commit.committed_at),
            "message": commit.message,
            "risk_score": float(prediction.risk_score) if prediction else None,
            "model_name": prediction.model_name if prediction else None,
            "predicted_at": iso_z(prediction.predicted_at) if prediction else None,
            "features": commit_service.feature_dict(feature),
            "explanation": explanation,
            "is_bug_inducing": _sizzle(feature.is_bug_inducing) if feature is not None else None,
            "localization": localization,
            "fix_references": commit_service.fix_references_for(
                session, commit.repo_name, commit_hash
            ),
        }
    return ok(data)
