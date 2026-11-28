"""页面进度：user_page_state 持久化与重置清理。"""

from __future__ import annotations

import shutil

from sqlalchemy.orm import Session

from app import config
from app.constants import PAGES
from app.errors import AppError
from app.models import User, UserPageState
from app.services import uploads
from app.utils import dumps, iso, loads, now


def _page(page: str) -> str:
    if page not in PAGES:
        raise AppError(40001, "页面标识非法")
    return page


def get_state(db: Session, user: User, page: str) -> dict | None:
    page = _page(page)
    row = db.get(UserPageState, (user.user_id, page))
    if row is None:
        return None
    return {"page": page, "state": loads(row.state_json, {}) or {}, "updated_at": iso(row.updated_at)}


def put_state(db: Session, user: User, page: str, state: dict) -> dict:
    page = _page(page)
    if not isinstance(state, dict):
        raise AppError(40001, "进度必须是对象")
    payload = dumps(state)
    if len(payload.encode("utf-8")) > config.MAX_PAGE_STATE_BYTES:
        raise AppError(40001, "页面进度超过 64KB 上限")
    row = db.get(UserPageState, (user.user_id, page))
    if row is None:
        row = UserPageState(user_id=user.user_id, page=page, state_json=payload, updated_at=now())
        db.add(row)
    else:
        row.state_json = payload
        row.updated_at = now()
    db.commit()
    return {"updated_at": iso(row.updated_at)}


def delete_state(db: Session, user: User, page: str) -> None:
    page = _page(page)
    row = db.get(UserPageState, (user.user_id, page))
    state = loads(row.state_json, {}) if row else {}
    job_ids = set()
    for key in ("job_id",):
        if state.get(key):
            job_ids.add(state[key])
    result_ref = state.get("result_ref") or {}
    if result_ref.get("job_id"):
        job_ids.add(result_ref["job_id"])
    uploads.cleanup_page(user.user_id, page)
    for job_id in job_ids:
        shutil.rmtree(config.OUTPUTS_DIR / user.user_id / str(job_id), ignore_errors=True)
    if row is not None:
        db.delete(row)
        db.commit()
