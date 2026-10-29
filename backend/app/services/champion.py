"""从已加载模型中解析读写请求共用的有效默认模型。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import model_registry
from app.models import Prediction


def _has_rows(session: Session, model_name: str) -> bool:
    return (
        session.execute(
            select(Prediction.commit_hash).where(Prediction.model_name == model_name).limit(1)
        ).first()
        is not None
    )


def resolve(session: Session) -> str | None:
    champ = model_registry.champion()
    if champ is None:
        return None
    if _has_rows(session, champ.name):
        return champ.name
    for entry in sorted(
        model_registry.all_models(), key=lambda e: model_registry.version_key(e.name), reverse=True
    ):
        if _has_rows(session, entry.name):
            return entry.name
    return champ.name
