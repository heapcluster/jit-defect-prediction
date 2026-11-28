"""统一响应信封与错误码（docs/接口/conventions.md）。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("backend.errors")

HTTP_BY_CODE = {
    40001: 400,
    40101: 401,
    40401: 404,
    40901: 409,
    41301: 413,
    42201: 422,
    42901: 429,
    50001: 500,
    50301: 503,
}


class AppError(Exception):
    def __init__(self, code: int, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def ok(data: Any = None) -> dict:
    return {"code": 0, "message": "ok", "data": data}


def error_payload(code: int, message: str, detail: Any = None) -> dict:
    return {"code": code, "message": message, "data": detail}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_BY_CODE.get(exc.code, 500),
            content=error_payload(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = [str(p) for p in first.get("loc", []) if p not in ("query", "body", "path")]
        param = loc[-1] if loc else "parameter"
        return JSONResponse(status_code=400, content=error_payload(40001, f"参数非法：{param}"))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled internal error: %s", exc)
        return JSONResponse(status_code=500, content=error_payload(50001, "内部错误"))
