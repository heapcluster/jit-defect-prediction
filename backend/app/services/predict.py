"""预测业务逻辑共享服务（供 predict / sync / prs 路由复用）。

此前特征抽取、Commit/Feature 幂等入库、全模型/单模型打分的代码散落在
`app.api.predict` 并被 `sync.py` / `prs.py` 直接调用，层次被破坏。
本模块统一为唯一定义点；路由层只做 HTTP 入参校验与响应包络。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import config, feature_source, model_registry
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError
from app.explain import with_labels
from app.models import Commit, CommitFeature, Prediction
from app.services import champion
from app.timeutil import iso_z
from app.validate import normalize_commit_hash

logger = logging.getLogger("backend.predict.service")


def resolve_model_name(model_name: str | None) -> str:
    """确定本次打分使用的模型名：显式给定时校验存在，否则走全站唯一入口。

    未显式指定时**不再单独读 `model_registry.champion()`**，而是与列表 / 详情 / 趋势 /
    PR 门禁共用 `services.champion.resolve()`（契约三 §17）：冠军在 `prediction` 表里
    还没有行时，两边会各自降级到不同模型，同一提交就得到两份分、两个模型名。
    共用之后，降级规则只有一处实现，响应里的 `model_name` 回显即真实所用模型。
    """
    if model_name:
        if not model_registry.has(model_name):
            # 契约三错误码表：枚举值不存在 → 40001；注册表整体为空才是 50000
            raise AppError(40001, "参数非法：model_name 不在已加载模型清单")
        return model_name
    with SessionLocal() as session:
        name = champion.resolve(session)
    if name is None:
        entry = model_registry.champion()
        if entry is None:
            raise AppError(50000, INTERNAL_ERROR_MESSAGE)
        return entry.name
    return name


def _missing_message(commit: Commit | None) -> str:
    """40400 文案按缺的是 commit 还是 feature 区分（契约三 message 逐字对齐）。"""
    return "commit not found" if commit is None else "features not found for this commit"


def _extract_feature(
    commit_hash: str, repo=None, missing_message: str = "commit not found"
) -> dict:
    """现算单条提交的 14 项特征；抽取失败按异常类型映射为 40400/50000。

    `missing_message` 由调用方传入：git 里也找不到该提交时，文案需与「库里缺哪一半」保持一致。
    """
    try:
        return feature_source.extract(commit_hash, repo=repo)
    except ValueError as exc:
        raise AppError(40400, missing_message) from exc
    except Exception as exc:
        logger.exception("single-commit feature extraction failed")
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc


def _upsert_commit_feature(
    session, commit_hash: str, extracted: dict
) -> tuple[Commit, CommitFeature]:
    """幂等写入 commit 与 commit_feature 行；并发双插时回落为查库。

    返回 (commit, feature) 元组。
    """
    committed_at = datetime.fromisoformat(extracted["committed_at"])
    commit = session.execute(
        select(Commit).where(Commit.commit_hash == commit_hash)
    ).scalar_one_or_none()
    feature = session.execute(
        select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
    ).scalar_one_or_none()

    if commit is None:
        commit = Commit(
            commit_hash=commit_hash,
            repo_name=extracted["repo_name"],
            author_name=extracted["author_name"],
            author_email=extracted["author_email"],
            committed_at=committed_at,
            message=extracted["message"],
            parent_hash=extracted["parent_hash"] or None,
        )
        session.add(commit)
    if feature is None:
        feature = CommitFeature(
            commit_hash=commit_hash,
            committed_at=committed_at,
            feature_version=extracted["feature_version"],
            **extracted["features"],
        )
        session.add(feature)

    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        commit = session.execute(
            select(Commit).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if commit is None or feature is None:
            raise AppError(50000, INTERNAL_ERROR_MESSAGE) from None

    return commit, feature


def _write_predictions(
    session,
    commit_hash: str,
    feature: CommitFeature,
    scores: list[tuple[str, float]],
    predicted_at: datetime,
) -> None:
    """把 [(model_name, risk_score)] 幂等写入 prediction 表（缺行则插，有行则更新）。"""
    for name, risk in scores:
        row = session.execute(
            select(Prediction).where(
                Prediction.commit_hash == commit_hash,
                Prediction.model_name == name,
            )
        ).scalar_one_or_none()
        if row is None:
            row = Prediction(commit_hash=commit_hash, model_name=name)
            session.add(row)
        row.risk_score = risk
        row.predicted_at = predicted_at
        row.feature_version = feature.feature_version


def _upsert_predictions(session, commit_hash: str, feature: CommitFeature) -> list[dict]:
    """对全部已加载模型逐模型打分并幂等写入 prediction 表。

    返回 [{model_name, risk_score}]。并发双插被唯一索引挡住时回落为 update，
    保证幂等成功而非 500 —— 回落只重跑写入，不重复推理（分数已算好）。
    """
    vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
    predicted_at = datetime.now(UTC).replace(tzinfo=None)
    scores = [
        (entry.name, model_registry.predict_proba(entry.model, vector))
        for entry in model_registry.all_models()
    ]

    try:
        _write_predictions(session, commit_hash, feature, scores, predicted_at)
        session.commit()
    except IntegrityError:
        session.rollback()
        _write_predictions(session, commit_hash, feature, scores, predicted_at)
        session.commit()

    return [{"model_name": name, "risk_score": round(risk, 5)} for name, risk in scores]


def predict_commit_all_models(commit_hash: str, repo=None) -> list[dict]:
    """对单条提交现算特征并对全部已加载模型打分，结果写入库。

    `commit_hash` 允许大写，内部归一化为小写后查库。
    `repo` 为 None 时取 `config.SOURCE_REPO`；批量同步可传入临时 worktree 路径。
    """
    commit_hash = normalize_commit_hash(commit_hash)

    with SessionLocal() as session:
        commit = session.execute(
            select(Commit).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()

        if commit is None or feature is None:
            missing_message = _missing_message(commit)
            if config.SOURCE_REPO is None:
                raise AppError(40400, missing_message)
            extracted = _extract_feature(commit_hash, repo=repo, missing_message=missing_message)
            commit, feature = _upsert_commit_feature(session, commit_hash, extracted)

        return _upsert_predictions(session, commit_hash, feature)


def predict_single(commit_hash: str, model_name: str, repo=None) -> dict:
    """对单条提交用指定模型打分，返回契约三 1.5 第 4 节的完整响应体。

    错误码：`model_name` 不在已加载清单 → 40001；提交/特征缺失且
    `SOURCE_REPO` 未配置 → 40400；注册表整体为空 → 50000。
    """
    commit_hash = normalize_commit_hash(commit_hash)

    with SessionLocal() as session:
        commit = session.execute(
            select(Commit).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()

        if commit is None or feature is None:
            missing_message = _missing_message(commit)
            if config.SOURCE_REPO is None:
                raise AppError(40400, missing_message)
            extracted = _extract_feature(commit_hash, repo=repo, missing_message=missing_message)
            commit, feature = _upsert_commit_feature(session, commit_hash, extracted)

        model_name = resolve_model_name(model_name)
        entry = model_registry.get_model(model_name)

        vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
        risk = model_registry.predict_proba(entry.model, vector)
        explanation = with_labels(model_registry.explain(entry, vector))
        predicted_at = datetime.now(UTC).replace(tzinfo=None)

        row = session.execute(
            select(Prediction).where(
                Prediction.commit_hash == commit_hash,
                Prediction.model_name == model_name,
            )
        ).scalar_one_or_none()
        if row is None:
            row = Prediction(commit_hash=commit_hash, model_name=model_name)
            session.add(row)
        row.risk_score = risk
        row.predicted_at = predicted_at
        row.feature_version = feature.feature_version
        session.commit()

        # 读回落库值再进响应：MySQL DATETIME 是秒级精度，in-memory 里的微秒会被截断，
        # 若直接返回本地值，「重复预测」时响应与库内行会对不上账（集成测试实测过）。
        stored_predicted_at = row.predicted_at

        features = {
            name: (int(getattr(feature, name)) if name == "fix" else float(getattr(feature, name)))
            for name in config.FEATURE_COLUMNS
        }

    return {
        "commit_hash": commit_hash,
        "model_name": entry.name,
        "risk_score": round(risk, 5),
        "predicted_at": iso_z(stored_predicted_at),
        "features": features,
        "explanation": explanation,
    }
