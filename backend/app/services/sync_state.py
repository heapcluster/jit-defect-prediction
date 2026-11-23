"""Local adapter for the old sync orchestration, backed exclusively by Job.

Thread-local data carries a worker's (job_id, retry_count), never job status.
The thread lock is only an optimization; MySQL owns cross-process exclusion.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import func, select

from app.db import SessionLocal
from app.errors import AppError
from app.models import Job
from app.services import job_store

_sync_lock = threading.Lock()
_worker = threading.local()
_PARAM_KEYS = ("phase", "mode", "scope", "line", "model_name", "start_time", "end_time")


def current_attempt() -> tuple[str, int] | None:
    return getattr(_worker, "token", None)


@contextmanager
def bind_job(job_id: str, attempt: int):
    old_token = current_attempt()
    old_bound = getattr(_worker, "bound", False)
    _worker.token = (job_id, attempt)
    _worker.bound = True
    try:
        yield
    finally:
        _worker.token = old_token
        _worker.bound = old_bound


def begin_sync(params: dict | None = None) -> tuple[str, int]:
    with SessionLocal() as session:
        job = job_store.create(session, "predict_batch", params={**(params or {}), "origin": "sync"}, start_immediately=True)
    token = (job["job_id"], job["retry_count"])
    _worker.token = token
    return token


def check_active() -> dict:
    token = current_attempt()
    if token is None:
        raise AppError(40001, "同步执行批次不存在")
    with SessionLocal() as session:
        return job_store.assert_running(session, token[0], attempt=token[1])


def set_state(**kwargs) -> tuple[str, int] | None:
    params = {key: kwargs[key] for key in _PARAM_KEYS if key in kwargs}
    token = current_attempt()
    if kwargs.get("running") is True:
        reusable = False
        if token:
            try:
                check_active()
                reusable = True
            except AppError as exc:
                # A stopped/vanished job can be replaced only by an unbound caller.
                if getattr(_worker, "bound", False) or exc.code not in (40001, 40400):
                    raise
        if not reusable:
            token = begin_sync(params)
    if token is None:
        return None
    with SessionLocal() as session:
        if params or any(key in kwargs for key in ("total", "done", "current_hash")):
            job_store.update_progress(session, token[0], attempt=token[1],
                total=kwargs.get("total"), done=kwargs.get("done"),
                current_item=kwargs.get("current_hash"), params=params or None)
        error = kwargs.get("last_error")
        if error is not None:
            # Only explicitly classified errors retain their safe message.
            job_store.fail(session, token[0], attempt=token[1], error=error)
        elif kwargs.get("running") is False:
            job_store.finish(session, token[0], attempt=token[1])
    return token


def get_sync_state(session=None) -> dict:
    if session is None:
        with SessionLocal() as local:
            return get_sync_state(local)
    with job_store._transaction(session, write=False):
        job = session.scalar(select(Job).where(
            Job.kind == "predict_batch",
            func.json_unquote(func.json_extract(Job.params_json, "$.origin")) == "sync"
        ).order_by(Job.created_at.desc(), Job.job_id.asc()).limit(1).execution_options(populate_existing=True))
        if job is None:
            return {"running": False, "phase": None, "mode": None, "scope": None,
                    "total": 0, "done": 0, "current_hash": None,
                    "started_at": None, "last_error": None}
        data = job_store._record(job)
    params = data["params_json"] or {}
    started = data["started_at"]
    return {"running": data["status"] == "running",
            "phase": params.get("phase") if data["status"] == "running" else None,
            "mode": params.get("mode"), "scope": params.get("scope"),
            "total": data["total"], "done": data["done"],
            "current_hash": data["current_item"],
            "started_at": datetime.fromisoformat(started.replace("Z", "+00:00")).replace(tzinfo=None) if started else None,
            "last_error": data["error_log"]}
