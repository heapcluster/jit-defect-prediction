"""路由公共依赖：当前用户与分页。"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.models import User


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    return auth.current_user(request, db)


def pagination(page: int = 1, page_size: int = 20) -> tuple[int, int]:
    return max(page, 1), min(max(page_size, 1), 100)


def export_filename(filename: str | None, default: str) -> str:
    from app.errors import AppError

    name = (filename or default or "").strip()
    if not name:
        raise AppError(40001, "文件名不能为空")
    if any(char in name for char in '\\/:*?"<>|\r\n\t') or len(name) > 100:
        raise AppError(40001, "文件名含非法字符")
    return name
