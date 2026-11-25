"""查询接口 1–2：风险列表与提交详情（docs/api/commits.md）。

本文件只做入参校验与响应编排；查询与字段组装收在 `app/services/commits.py`，
时间格式收在 `app/timeutil.py`，哈希校验收在 `app/validate.py`。
查询是只读展示面：不在本接口做预测、解释、定位或修复建议。
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select

from app import model_registry, schemas
from app.api.storage import query_keys
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Commit, CommitFeature, Dataset, DatasetCommit, Prediction
from app.services import commits as commit_service
from app.services import config_store, risk_summary
from app.services.predict import _model_version
from app.timeutil import iso_z, parse_time_param
from app.validate import normalize_commit_hash

router = APIRouter(dependencies=[Depends(require_api_key)])

# 全 hex（1~40 位）输入按哈希前缀查：走 commit_hash 的唯一索引，不做三列全表匹配
_HEX_PREFIX = re.compile(r"^[0-9a-fA-F]{1,40}$")
# LIKE 转义符必须显式声明：不写 escape 等于没转义
_LIKE_ESCAPE = "\\"

_LIST_PARAMS = {
    "page", "size", "model_name", "dataset_id", "start_time", "end_time",
    "q", "with_features", "risk_min", "risk_max",
}
_DETAIL_PARAMS = {"model_name", "dataset_id"}


def _like_term(raw: str) -> str:
    """把用户输入转成 LIKE 模式的安全片段（转义 % _ \\），配 `escape=` 一起用。"""
    escaped = raw.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
    escaped = escaped.replace("%", _LIKE_ESCAPE + "%").replace("_", _LIKE_ESCAPE + "_")
    return f"{escaped}%"


def _sizzle(value: int | None) -> int | None:
    """SZZ 真标签：库内 1 / 0 / NULL 原样对外（NULL 不是 0）。"""
    return int(value) if value is not None else None


def _risk_bound(raw: str | None, name: str) -> float | None:
    """风险区间端点必须是 [0,1] 数值；非法一律 40001，不交给 FastAPI 的 422。"""
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise AppError(40001, f"参数非法：{name} 需为 [0,1] 数值") from error
    if not 0.0 <= value <= 1.0:
        raise AppError(40001, f"参数非法：{name} 需在 [0,1] 区间内")
    return value


@router.get("/api/commits", response_model=schemas.CommitsResponse)
def list_commits(
    request: Request,
    page: int = Query(default=1),
    size: int = Query(default=20),
    model_name: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=64),
    with_features: str | None = Query(default=None),
    risk_min: str | None = Query(default=None),
    risk_max: str | None = Query(default=None),
) -> dict:
    # since/until 与 is_test 都不在契约里：作为未知参数一律 40001
    query_keys(request, _LIST_PARAMS)
    if page < 1:
        raise AppError(40001, "参数非法：page 需 >= 1")
    if size < 1 or size > 100:
        raise AppError(40001, "参数非法：size 超过上限 100")
    if with_features not in (None, "0", "1"):
        raise AppError(40001, "参数非法：with_features 需为 0 或 1")
    low, high = _risk_bound(risk_min, "risk_min"), _risk_bound(risk_max, "risk_max")
    if low is not None and high is not None and low > high:
        raise AppError(40001, "参数非法：risk_min 不能大于 risk_max")
    start = parse_time_param(start_time, "start_time") if start_time else None
    end = parse_time_param(end_time, "end_time", "end") if end_time else None
    if not model_name:
        raise AppError(40001, "参数非法：model_name 必填，不设默认模型")
    want_features = with_features == "1"

    with SessionLocal() as session:
        threshold = float(config_store.get_value("decision_threshold", session))
        # label_method 来自数据集成员表（§3.1），不是 commit_feature；无 dataset 时取该提交任一登记来源。
        label_filter = DatasetCommit.commit_hash == Commit.commit_hash
        if dataset_id:
            if session.get(Dataset, dataset_id) is None:
                raise AppError(40400, "dataset not found")
            label_filter = label_filter & (DatasetCommit.dataset_id == dataset_id)
        label_method_expr = (
            select(DatasetCommit.label_method).where(label_filter).limit(1).scalar_subquery()
        )
        stmt = (
            select(Prediction, Commit, CommitFeature, label_method_expr)
            .join(Commit, Commit.commit_hash == Prediction.commit_hash)
            .outerjoin(CommitFeature, CommitFeature.commit_hash == Prediction.commit_hash)
            .where(Prediction.model_name == model_name)
        )
        if dataset_id:
            # 数据集成员按 (dataset_id, commit_hash) 唯一，join 不产生重复行。
            stmt = stmt.join(
                DatasetCommit, DatasetCommit.commit_hash == Prediction.commit_hash
            ).where(DatasetCommit.dataset_id == dataset_id)
        if start is not None:
            stmt = stmt.where(Commit.committed_at >= start)
        if end is not None:
            stmt = stmt.where(Commit.committed_at <= end)
        if low is not None:
            stmt = stmt.where(Prediction.risk_score >= low)
        if high is not None:
            stmt = stmt.where(Prediction.risk_score <= high)
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
        for prediction, commit, feature, label_method in window:
            risk = float(prediction.risk_score)
            item = {
                "commit_hash": commit.commit_hash,
                "repo_name": commit.repo_name,
                "author_name": commit.author_name,
                "committed_at": iso_z(commit.committed_at),
                "message": commit.message,
                "model_name": prediction.model_name,
                "risk_score": risk,
                # 标签不入库到 prediction：按当前配置的单一决策阈值现算，不改库内概率
                "predicted_label": int(risk >= threshold),
                "predicted_at": iso_z(prediction.predicted_at),
                "is_bug_inducing": _sizzle(feature.is_bug_inducing)
                if feature is not None
                else None,
                "labeled_at": iso_z(feature.labeled_at)
                if feature is not None and feature.labeled_at is not None
                else None,
                "label_method": label_method,
            }
            if want_features:
                item["features"] = commit_service.feature_dict(feature)
            items.append(item)
    return ok({"total": total, "page": page, "size": size, "items": items})


@router.get("/api/commits/{commit_hash}", response_model=schemas.DetailResponse)
def commit_detail(
    request: Request,
    commit_hash: str,
    model_name: str | None = Query(default=None),
    dataset_id: str | None = Query(default=None),
) -> dict:
    query_keys(request, _DETAIL_PARAMS)
    if not model_name:
        raise AppError(40001, "参数非法：model_name 必填，不设默认模型")
    # 库内哈希是小写：校验放行大写形式，查询就必须用归一化值，否则误报 commit not found（D-09）
    commit_hash = normalize_commit_hash(commit_hash)
    with SessionLocal() as session:
        if dataset_id and session.get(Dataset, dataset_id) is None:
            raise AppError(40400, "dataset not found")
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
                Prediction.model_name == model_name,
            )
        ).scalar_one_or_none()
        features = commit_service.feature_dict(feature)
        risk_score = float(prediction.risk_score) if prediction else None
        threshold = float(config_store.get_value("decision_threshold", session))
        model_version = _model_version(session, model_name)
        feature_version = feature.feature_version if feature is not None else None
        stale = prediction is not None and (
            prediction.model_version != model_version
            or prediction.feature_version != feature_version
        )
        # 详情只编排展示字段；解释/定位/修复参考分别走 /api/explain 与 /api/localize/run。
        summary = risk_summary.summary_for(
            commit_hash=commit.commit_hash,
            model_name=model_name,
            model_line=model_registry.line_of(model_name),
            risk_score=risk_score,
            features=features,
            explanation=[],
            localization=None,
            risk_thresholds={
                item["config_key"]: item["value"]
                for item in config_store.read_config(
                    session, ["risk_high_threshold", "risk_mid_threshold"]
                )
            },
        )
        label_filter = DatasetCommit.commit_hash == commit_hash
        if dataset_id:
            label_filter = label_filter & (DatasetCommit.dataset_id == dataset_id)
        label_method = session.scalar(
            select(DatasetCommit.label_method).where(label_filter).limit(1)
        )
        prediction_data = None
        if prediction is not None:
            prediction_data = {
                "model_name": prediction.model_name,
                "risk_score": float(prediction.risk_score),
                "predicted_label": int(float(prediction.risk_score) >= threshold),
                "decision_threshold": threshold,
                "model_version": prediction.model_version,
                "feature_version": prediction.feature_version,
                "predicted_at": iso_z(prediction.predicted_at),
                "stale": bool(stale),
            }
        data = {
            "commit_hash": commit.commit_hash,
            "repo_name": commit.repo_name,
            "author_name": commit.author_name,
            "committed_at": iso_z(commit.committed_at),
            "message": commit.message,
            "risk_score": risk_score,
            "model_name": prediction.model_name if prediction else None,
            "predicted_at": iso_z(prediction.predicted_at) if prediction else None,
            "features": features,
            "summary": summary,
            "is_bug_inducing": _sizzle(feature.is_bug_inducing) if feature is not None else None,
            "labeled_at": iso_z(feature.labeled_at)
            if feature is not None and feature.labeled_at is not None
            else None,
            "label_method": label_method,
            "prediction": prediction_data,
        }
    return ok(data)
