"""统一响应包络与错误码（契约三 v1.2 第二节）：只用 0/40001/40100/40400/50000。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("backend.errors")

HTTP_BY_CODE = {
    0: 200,
    40001: 400,
    40100: 401,
    40400: 404,
    50000: 500,
}

INTERNAL_ERROR_MESSAGE = "internal error"


class AppError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def ok(data: Any) -> dict:
    return {"code": 0, "message": "ok", "data": data}


def error_payload(code: int, message: str) -> dict:
    return {"code": code, "message": message, "data": None}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=HTTP_BY_CODE[exc.code], content=error_payload(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = [str(part) for part in first.get("loc", []) if part not in ("query", "body", "path")]
        param = loc[-1] if loc else "parameter"
        return JSONResponse(
            status_code=400,
            content=error_payload(40001, f"参数非法：{param}"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        # 契约三：50000 的 message 不得回显堆栈、SQL、文件路径；细节只写服务端日志
        logger.exception("unhandled internal error: %s", exc)
        return JSONResponse(status_code=500, content=error_payload(50000, INTERNAL_ERROR_MESSAGE))
