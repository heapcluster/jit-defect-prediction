"""人工反馈标签的读写（feedback capability）。

业务与数据访问在这里，路由只做入参校验与包络。错误码只用契约三的 5 个。
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal
from app.errors import AppError
from app.models import Commit, CommitLabel
from app.services.commits import MANUAL_LABEL_METHOD
from app.timeutil import iso_z, now_naive_utc


def put_label(commit_hash: str, is_defect: bool) -> dict:
    """写入或更新人工标签。

    - commit 不存在 → 40400（MUST NOT 静默创建孤立标签行）
    - 撤销 = 再次以 `is_defect=False` 提交（保留「已确认非缺陷」的事实），不删行
    """
    with SessionLocal() as session:
        exists = session.execute(
            select(Commit.commit_hash).where(Commit.commit_hash == commit_hash)
        ).scalar_one_or_none()
        if exists is None:
            raise AppError(40400, "commit not found")
        row = session.execute(
            select(CommitLabel).where(
                CommitLabel.commit_hash == commit_hash,
                CommitLabel.label_method == MANUAL_LABEL_METHOD,
            )
        ).scalar_one_or_none()
        if row is None:
            row = CommitLabel(
                commit_hash=commit_hash,
                is_bug_inducing=1 if is_defect else 0,
                label_method=MANUAL_LABEL_METHOD,
                bug_fix_hash=None,
                labeled_at=now_naive_utc(),
            )
            session.add(row)
        else:
            row.is_bug_inducing = 1 if is_defect else 0
            row.labeled_at = now_naive_utc()
        session.commit()
        return {
            "commit_hash": commit_hash,
            "is_defect": bool(row.is_bug_inducing),
            "labeled_at": iso_z(row.labeled_at),
        }
