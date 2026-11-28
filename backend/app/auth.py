"""会话鉴权：Cookie 只放原始令牌，库内存 SHA-256 摘要。"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.errors import AppError
from app.models import User, UserSession
from app.utils import now


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    timestamp = now()
    db.add(
        UserSession(
            session_id=_digest(token),
            user_id=user.user_id,
            created_at=timestamp,
            last_seen_at=timestamp,
            expires_at=timestamp + timedelta(days=config.SESSION_TTL_DAYS),
        )
    )
    db.commit()
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=config.SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=config.SESSION_TTL_DAYS * 24 * 3600,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE, path="/")


def current_user(request: Request, db: Session) -> User:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        raise AppError(40101, "未登录或会话已失效")
    session = db.get(UserSession, _digest(token))
    if session is None or session.expires_at <= now():
        raise AppError(40101, "未登录或会话已失效")
    user = db.get(User, session.user_id)
    if user is None or user.status != "active":
        raise AppError(40101, "未登录或会话已失效")
    session.last_seen_at = now()
    db.commit()
    return user


def logout(request: Request, db: Session) -> None:
    token = request.cookies.get(config.SESSION_COOKIE)
    if not token:
        return
    session = db.get(UserSession, _digest(token))
    if session is not None:
        db.delete(session)
        db.commit()


def purge_expired(db: Session, user_id: str) -> None:
    timestamp = now()
    stale = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user_id, UserSession.expires_at <= timestamp
        )
    ).all()
    for row in stale:
        db.delete(row)
