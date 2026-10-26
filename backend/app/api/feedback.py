"""人工反馈闭环：PUT /api/commits/{commit_hash}/label（feedback capability）。

工业级 JIT 的核心闭环：把「这条提交到底有没有引入缺陷」以人工确认的方式回流成标签，
供后续效果评估 / 阈值校准 / 再训练使用。人工标签以 `label_method="manual"` 与 SZZ
自动标签（其它 label_method）共存，靠唯一约束 `(commit_hash, label_method)` 隔离，
`MUST NOT` 覆盖或删除自动标签。

错误码只用契约三规定的 5 个（0 / 40001 / 40100 / 40400 / 50000）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app import schemas
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Commit, CommitLabel

router = APIRouter(dependencies=[Depends(require_api_key)])

MANUAL_METHOD = "manual"
HASH_HEX = "0123456789abcdef"


class LabelRequest(BaseModel):
    is_defect: bool


def normalize_hash(commit_hash: str) -> str:
    if (
        not commit_hash
        or len(commit_hash) != 40
        or any(c not in HASH_HEX for c in commit_hash.lower())
    ):
        raise AppError(40001, "参数非法：commit_hash 需为 40 位十六进制")
    return commit_hash.lower()


def iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


@router.put("/api/commits/{commit_hash}/label", response_model=schemas.LabelResponse)
def put_commit_label(commit_hash: str, body: LabelRequest) -> dict:
    """写入或更新人工标签：撤销 = 再次提交 `is_defect=false`（保留「已确认非缺陷」事实）。"""
    commit_hash = normalize_hash(commit_hash)
    with SessionLocal() as session:
        exists = session.execute(
            select(Commit.commit_hash).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if exists is None:
            raise AppError(40400, "commit not found")
        row = session.execute(
            select(CommitLabel).where(
                CommitLabel.commit_hash == commit_hash,
                CommitLabel.label_method == MANUAL_METHOD,
            )
        ).scalar_one_or_none()
        if row is None:
            row = CommitLabel(
                commit_hash=commit_hash,
                is_bug_inducing=1 if body.is_defect else 0,
                label_method=MANUAL_METHOD,
                bug_fix_hash=None,
                labeled_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(row)
        else:
            row.is_bug_inducing = 1 if body.is_defect else 0
            row.labeled_at = datetime.now(UTC).replace(tzinfo=None)
        session.commit()
        stored = row.labeled_at
        is_defect = bool(row.is_bug_inducing)
    return ok(
        {
            "commit_hash": commit_hash,
            "is_defect": is_defect,
            "labeled_at": iso_z(stored),
        }
    )
