"""鉴权依赖：请求头 X-API-Key，固定令牌（契约三 v1.2 鉴权细则）。"""

from __future__ import annotations

from fastapi import Header

from app import config
from app.errors import AppError

MISSING_OR_INVALID_TOKEN = "missing or invalid token"


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # 令牌未配置时一律拒绝（fail closed），避免误开无鉴权服务
    if not config.API_TOKEN or x_api_key != config.API_TOKEN:
        raise AppError(40100, MISSING_OR_INVALID_TOKEN)
