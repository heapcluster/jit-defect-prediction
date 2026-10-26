"""预测接口 4：POST /api/predict 在线预测（契约三 1.5 第 4 节）。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import config, feature_source, model_registry, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError
from app.models import Commit, CommitFeature, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

HASH_HEX = "0123456789abcdef"
logger = logging.getLogger("backend.predict")


class PredictRequest(BaseModel):
    commit_hash: str
    model_name: str | None = None


def predict_commit(body: PredictRequest, repo=None) -> dict:
    # 校验口径与 predict_commit_all_models 共用一份（_normalize_hash），
    # 避免两处各写一遍导致行为漂移（大写归一化、40 位十六进制 → 40001）。
    commit_hash = _normalize_hash(body.commit_hash)

    with SessionLocal() as session:
        commit = session.execute(select(Commit).where(Commit.commit_hash == commit_hash)).scalar_one_or_none()
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if commit is None or feature is None:
            missing_message = "commit not found" if commit is None else "features not found for this commit"
            if config.SOURCE_REPO is None:
                raise AppError(40400, missing_message)
            try:
                extracted = feature_source.extract(commit_hash, repo=repo)
            except ValueError as exc:
                raise AppError(40400, missing_message) from exc
            except Exception as exc:
                logger.exception("single-commit feature extraction failed")
                raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc

            committed_at = datetime.fromisoformat(extracted["committed_at"])
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
                commit = session.execute(select(Commit).where(Commit.commit_hash == commit_hash)).scalar_one_or_none()
                feature = session.execute(
                    select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
                ).scalar_one_or_none()
                if commit is None or feature is None:
                    raise AppError(50000, INTERNAL_ERROR_MESSAGE) from None

        if body.model_name is not None and not model_registry.has(body.model_name):
            # 契约三错误码表：枚举值不存在 → 40001；注册表整体为空才是 50000
            raise AppError(40001, "参数非法：model_name 不在已加载模型清单")
        entry = model_registry.get_model(body.model_name) if body.model_name else model_registry.default_model()
        if entry is None:
            raise AppError(50000, INTERNAL_ERROR_MESSAGE)

        vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
        risk = model_registry.predict_proba(entry.model, vector)
        explanation = model_registry.explain(entry, vector)
        predicted_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # design D7：聊天第三条「A 与 C 写同一张 prediction 表」+ 契约三「只保留最新一行」
        row = session.execute(
            select(Prediction)
            .where(Prediction.commit_hash == commit_hash, Prediction.model_name == entry.name)
        ).scalar_one_or_none()
        if row is None:
            row = Prediction(commit_hash=commit_hash, model_name=entry.name)
            session.add(row)
        row.risk_score = risk
        row.predicted_at = predicted_at
        row.feature_version = feature.feature_version
        try:
            session.commit()
        except IntegrityError:
            # 审 4：并发双插被唯一索引挡住时回落为 update，保证幂等成功而非 500
            session.rollback()
            row = session.execute(
                select(Prediction)
                .where(Prediction.commit_hash == commit_hash, Prediction.model_name == entry.name)
            ).scalar_one()
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
        "code": 0,
        "message": "ok",
        "data": {
            "commit_hash": commit_hash,
            "model_name": entry.name,
            "risk_score": round(risk, 5),
            "predicted_at": stored_predicted_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "features": features,
            "explanation": explanation,
        },
    }


def _normalize_hash(commit_hash: str) -> str:
    if not commit_hash or len(commit_hash) != 40 or any(c not in HASH_HEX for c in commit_hash.lower()):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")
    return commit_hash.lower()


def predict_commit_all_models(commit_hash: str, repo=None) -> list[dict]:
    """现算一次特征，对全部已加载模型各写一行 prediction（供 PR 同步批量落库、支撑前端 8 种切换）。

    与 `predict_commit` 共用同一套「缺失即现算 + 幂等 upsert」逻辑，但只提取一次特征、
    逐模型打分，避免对同一条提交重复跑 `git log --numstat`。
    """
    commit_hash = _normalize_hash(commit_hash)
    with SessionLocal() as session:
        commit = session.execute(select(Commit).where(Commit.commit_hash == commit_hash)).scalar_one_or_none()
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if commit is None or feature is None:
            missing = "commit not found" if commit is None else "features not found for this commit"
            if config.SOURCE_REPO is None:
                raise AppError(40400, missing)
            try:
                extracted = feature_source.extract(commit_hash, repo=repo)
            except ValueError as exc:
                raise AppError(40400, missing) from exc
            except Exception as exc:
                logger.exception("single-commit feature extraction failed")
                raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc

            committed_at = datetime.fromisoformat(extracted["committed_at"])
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
                commit = session.execute(select(Commit).where(Commit.commit_hash == commit_hash)).scalar_one_or_none()
                feature = session.execute(
                    select(CommitFeature).where(CommitFeature.commit_hash == commit_hash)
                ).scalar_one_or_none()
                if commit is None or feature is None:
                    raise AppError(50000, INTERNAL_ERROR_MESSAGE) from None

        vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
        predicted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        entries = model_registry.all_models()
        results: list[dict] = []
        for entry in entries:
            risk = model_registry.predict_proba(entry.model, vector)
            row = session.execute(
                select(Prediction).where(
                    Prediction.commit_hash == commit_hash, Prediction.model_name == entry.name
                )
            ).scalar_one_or_none()
            if row is None:
                row = Prediction(commit_hash=commit_hash, model_name=entry.name)
                session.add(row)
            row.risk_score = risk
            row.predicted_at = predicted_at
            row.feature_version = feature.feature_version
            results.append({"model_name": entry.name, "risk_score": round(risk, 5)})
        try:
            session.commit()
        except IntegrityError:
            # 并发双插被唯一索引挡住时回落为 update，保证幂等成功而非 500
            session.rollback()
            results = []
            for entry in entries:
                risk = model_registry.predict_proba(entry.model, vector)
                row = session.execute(
                    select(Prediction).where(
                        Prediction.commit_hash == commit_hash, Prediction.model_name == entry.name
                    )
                ).scalar_one_or_none()
                if row is None:
                    row = Prediction(commit_hash=commit_hash, model_name=entry.name)
                    session.add(row)
                row.risk_score = risk
                row.predicted_at = predicted_at
                row.feature_version = feature.feature_version
                results.append({"model_name": entry.name, "risk_score": round(risk, 5)})
            session.commit()
    return results


@router.post("/api/predict", response_model=schemas.PredictResponse)
def predict(body: PredictRequest) -> dict:
    """对单条提交现算特征并预测（runbook §6 第 5 条）。"""
    return predict_commit(body)
