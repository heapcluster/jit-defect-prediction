"""页面进度读写与重置。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db import get_db
from app.errors import ok
from app.models import User
from app.services import page_state

router = APIRouter(prefix="/page-state", tags=["page-state"])


@router.get("/{page}")
def get_state(page: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return ok(page_state.get_state(db, user, page))


@router.put("/{page}")
async def put_state(
    page: str,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        state = await request.json()
    except Exception:  # noqa: BLE001
        state = None
    return ok(page_state.put_state(db, user, page, state))


@router.delete("/{page}")
def delete_state(page: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    page_state.delete_state(db, user, page)
    return ok(None)
