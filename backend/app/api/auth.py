"""登录、登出与当前用户。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import auth
from app.api.deps import current_user
from app.db import get_db
from app.errors import AppError, ok
from app.models import Dataset, Model, User
from app.schemas import LoginRequest
from app.utils import iso, now

router = APIRouter(prefix="/auth", tags=["auth"])


def user_payload(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "display_name": user.display_name,
        "created_at": iso(user.created_at),
    }


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    username = (payload.username or "").strip()
    password = payload.password or ""
    if not username or not password or len(username) > 64 or len(password) > 128:
        raise AppError(40001, "用户名或密码非法")
    user = db.scalar(select(User).where(User.username == username))
    if user is None or user.password != password:
        raise AppError(40101, "用户名或密码错误")
    token = auth.create_session(db, user)
    auth.set_session_cookie(response, token)
    user.last_login_at = now()
    db.commit()
    return ok({"user": user_payload(user)})


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    auth.logout(request, db)
    auth.clear_session_cookie(response)
    return ok(None)


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    datasets = db.scalar(select(func.count()).select_from(Dataset).where(Dataset.owner_user_id == user.user_id)) or 0
    models = db.scalar(select(func.count()).select_from(Model).where(Model.owner_user_id == user.user_id)) or 0
    return ok({
        **user_payload(user),
        "last_login_at": iso(user.last_login_at),
        "counts": {"datasets": datasets, "models": models},
    })
