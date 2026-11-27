"""Authenticated job state management; no module execution or file access."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.db import get_db
from app.errors import AppError, ok
from app.services import (
    clean_run,
    collect_run,
    evaluate_run,
    explain_run,
    job_store,
    predict_run,
    train_run,
)

router = APIRouter(dependencies=[Depends(require_api_key)])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/api/jobs")
def list_jobs(session: DatabaseSession, kind: str | None = None, status: str | None = None,
              chain_id: str | None = None,
              page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100)) -> dict:
    return ok(job_store.list_jobs(session, kind=kind, status=status, chain_id=chain_id, page=page, size=size))


@router.get("/api/jobs/{job_id}")
def detail(job_id: str, session: DatabaseSession) -> dict:
    return ok(job_store.get(session, job_id))


async def _no_overrides(request: Request) -> None:
    if request.query_params or await request.body():
        raise AppError(40001, "参数非法：此操作不接受请求体或覆盖参数")


def _transition_response(data: dict) -> dict:
    return ok({key: data[key] for key in ("job_id", "status", "retry_count")})


@router.post("/api/jobs/{job_id}/retry")
async def retry(job_id: str, request: Request, session: DatabaseSession) -> dict:
    await _no_overrides(request)
    data = job_store.retry(session, job_id)
    collect_run.dispatch_retry(data)
    clean_run.dispatch_retry(data)
    train_run.dispatch_retry(data)
    predict_run.dispatch_retry(data)
    evaluate_run.dispatch_retry(data)
    explain_run.dispatch_retry(data)
    return _transition_response(data)


@router.post("/api/jobs/{job_id}/cancel")
async def cancel(job_id: str, request: Request, session: DatabaseSession) -> dict:
    await _no_overrides(request)
    return _transition_response(job_store.cancel(session, job_id))
