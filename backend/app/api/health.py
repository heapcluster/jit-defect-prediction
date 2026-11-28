"""健康检查。"""

from __future__ import annotations

from fastapi import APIRouter

from app.errors import ok

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return ok({"status": "ok"})
