"""任务轮询与取消。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.errors import AppError, ok
from app.models import Job, User
from app.services import jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job(db: Session, user: User, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    return job


@router.get("/{job_id}")
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return ok(jobs.serialize(_job(db, user, job_id)))


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    _job(db, user, job_id)
    return ok(jobs.manager.cancel(db, user, job_id))
