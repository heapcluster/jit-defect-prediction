"""预测接口 4：POST /api/predict 在线预测（契约三 v1.2 第 4 节）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app import config, model_registry, schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError
from app.models import Commit, CommitFeature, Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

HASH_HEX = "0123456789abcdef"


class PredictRequest(BaseModel):
    commit_hash: str
    model_name: str | None = None


@router.post("/api/predict", response_model=schemas.PredictResponse)
def predict(body: PredictRequest) -> dict:
    if not body.commit_hash or len(body.commit_hash) != 40 or any(
        c not in HASH_HEX for c in body.commit_hash.lower()
    ):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")

    with SessionLocal() as session:
        commit = session.execute(select(Commit).where(Commit.commit_hash == body.commit_hash)).scalar_one_or_none()
        if commit is None:
            raise AppError(40400, "commit not found")
        feature = session.execute(
            select(CommitFeature).where(CommitFeature.commit_hash == body.commit_hash)
        ).scalar_one_or_none()
        if feature is None:
            raise AppError(40400, "features not found for this commit")

        if body.model_name is not None and not model_registry.has(body.model_name):
            # 契约三错误码表：枚举值不存在 → 40001；注册表整体为空才是 50000
            raise AppError(40001, "参数非法：model_name 不在已加载模型清单")
        entry = model_registry.get_model(body.model_name) if body.model_name else model_registry.default_model()
        if entry is None:
            raise AppError(50000, INTERNAL_ERROR_MESSAGE)

        vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
        risk = model_registry.predict_proba(entry.model, vector)
        explanation = model_registry.explain(entry.model, vector)
        predicted_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # design D7：聊天第三条「A 与 C 写同一张 prediction 表」+ 契约三 v1.2「只保留最新一行」
        row = session.execute(
            select(Prediction)
            .where(Prediction.commit_hash == body.commit_hash, Prediction.model_name == entry.name)
        ).scalar_one_or_none()
        if row is None:
            row = Prediction(commit_hash=body.commit_hash, model_name=entry.name)
            session.add(row)
        row.risk_score = risk
        row.predicted_at = predicted_at
        row.feature_version = feature.feature_version
        session.commit()

        features = {
            name: (int(getattr(feature, name)) if name == "fix" else float(getattr(feature, name)))
            for name in config.FEATURE_COLUMNS
        }
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "commit_hash": body.commit_hash,
            "model_name": entry.name,
            "risk_score": round(risk, 5),
            "predicted_at": predicted_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            "features": features,
            "explanation": explanation,
        },
    }
