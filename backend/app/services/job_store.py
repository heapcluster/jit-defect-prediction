"""Persisted job lifecycle primitives; module executors own business work.

Mutations commit their own transaction. Workers must retain the retry_count
returned by start and pass it to every progress/terminal update.
"""
from __future__ import annotations

import json
import re
from contextlib import contextmanager
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Job
from app.timeutil import iso_z, now_naive_utc

KINDS = ("collect", "clean", "train", "predict_batch", "evaluate", "explain")
STATUSES = ("queued", "running", "success", "failed", "cancelled")
ERROR_LIMIT = 2000
_SECRET = re.compile(r"password|passwd|pwd|secret|token|credential|authorization|api[_-]?key|llm[_-]?key|private[_-]?key", re.I)
_URL = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>\"']+")
_PATH = re.compile(r"(?<![\w:])(?:[A-Za-z]:[\\/]|/|~[/\\]|\.\.[/\\])[^\s,;<>\"']+")


def _safe_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https", "ssh", "git") or not parts.hostname:
            return "[redacted]"
        host = parts.hostname
        if ":" in host:
            host = f"[{host}]"
        if parts.port:
            host += f":{parts.port}"
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _SECRET.search(k)])
        return urlunsplit((parts.scheme, host, parts.path, query, ""))
    except ValueError:
        return "[redacted]"


def sanitize_text(value: str) -> str:
    # Hide URLs while removing local paths, then restore credential-free URLs.
    urls = []
    def save_url(match):
        urls.append(_safe_url(match.group()))
        return f"URLPLACEHOLDER{len(urls) - 1}END"
    value = _URL.sub(save_url, value)
    value = re.sub(rf"(?i)(?:{_SECRET.pattern})\s*[:=]\s*[^\s,;]+", "[redacted]", value)
    value = re.sub(r"(?i)bearer\s+[^\s,;]+", "[redacted]", value)
    value = _PATH.sub("[redacted]", value)
    for index, url in enumerate(urls):
        value = value.replace(f"URLPLACEHOLDER{index}END", url)
    return value


def sanitize(value):
    """Remove credentials and filesystem escape paths before any persistence."""
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items() if not _SECRET.search(str(k))}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        if "://" in value or _SECRET.search(value):
            return sanitize_text(value)
        normalized = value.replace("\\", "/")
        if normalized.startswith(("/", "~/")) or re.match(r"^[A-Za-z]:/", normalized) or ".." in normalized.split("/"):
            return "[redacted]"
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise AppError(40001, "参数非法：JSON snapshot")


def _dump(value):
    if value is None:
        return None
    try:
        encoded = json.dumps(sanitize(value), ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError):
        raise AppError(40001, "参数非法：JSON snapshot") from None
    if len(encoded.encode("utf-8")) > 65535:
        raise AppError(40001, "任务快照超过存储大小限制")
    return encoded


def _decode(value):
    return None if value is None else json.loads(value)


def _record(job: Job) -> dict:
    return {
        "job_id": job.job_id, "kind": job.kind, "status": job.status,
        "params_json": _decode(job.params_json), "total": job.total, "done": job.done,
        "current_item": job.current_item, "created_at": iso_z(job.created_at),
        "started_at": iso_z(job.started_at), "finished_at": iso_z(job.finished_at),
        "error_log": job.error_log, "retry_count": job.retry_count,
        "output_ref_json": _decode(job.output_ref_json),
    }


@contextmanager
def _transaction(session: Session, *, write=True):
    try:
        yield
        if write:
            session.commit()
    except AppError:
        session.rollback()
        raise
    except SQLAlchemyError as exc:
        session.rollback()
        number = getattr(getattr(exc, "orig", None), "args", (None,))[0]
        if number in (1213, 1205):
            raise AppError(40001, "任务状态冲突，请稍后重试") from None
        raise AppError(50000, "internal error") from None


def _fresh(session: Session, job_id: str) -> Job:
    job = session.scalar(select(Job).where(Job.job_id == job_id).execution_options(populate_existing=True))
    if job is None:
        raise AppError(40400, "job not found")
    return job


def _lock_kind(session: Session, kind: str) -> list[Job]:
    # MySQL current read, not an RR snapshot. Every transition takes these same
    # common kind rows before its target. No fake row or process lock is needed.
    return list(session.scalars(
        select(Job).with_hint(Job, "FORCE INDEX (ix_job_kind_status)", dialect_name="mysql")
        .where(Job.kind == kind).order_by(Job.job_id.asc()).with_for_update()
        .execution_options(populate_existing=True)
    ))


def _locked(session: Session, job_id: str) -> tuple[Job, list[Job]]:
    # Kind is immutable; this nonlocking lookup only selects the lock domain.
    kind = session.scalar(select(Job.kind).where(Job.job_id == job_id))
    if kind is None:
        raise AppError(40400, "job not found")
    rows = _lock_kind(session, kind)
    target = next((row for row in rows if row.job_id == job_id), None)
    if target is None:
        raise AppError(40400, "job not found")
    return target, rows


def _cas(session: Session, job: Job, statuses, values, attempt=None) -> dict:
    conditions = [Job.job_id == job.job_id, Job.status.in_(statuses)]
    if attempt is not None:
        conditions.append(Job.retry_count == attempt)
    result = session.execute(update(Job).where(*conditions).values(**values).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise AppError(40001, "任务状态冲突")
    return _record(_fresh(session, job.job_id))


def _active(job: Job, attempt: int) -> None:
    if job.status != "running" or job.retry_count != attempt:
        raise AppError(40001, "任务已停止或执行批次已失效")


def create(session: Session, kind: str, *, params=None, total=0, start_immediately=False) -> dict:
    if kind not in KINDS or not isinstance(total, int) or total < 0:
        raise AppError(40001, "参数非法：kind/total")
    if params is not None and not isinstance(params, dict):
        raise AppError(40001, "参数非法：params")
    with _transaction(session):
        job = Job(job_id=str(uuid4()), kind=kind, status="queued", params_json=_dump(params),
                  total=total, done=0, retry_count=0, created_at=now_naive_utc())
        session.add(job)
        session.flush()
        if start_immediately:
            job, rows = _locked(session, job.job_id)
            if any(row.status == "running" for row in rows):
                raise AppError(40001, "同类任务正在运行")
            data = _cas(session, job, ("queued",), {"status": "running", "started_at": now_naive_utc()}, 0)
        else:
            data = _record(job)
    return data


def get(session: Session, job_id: str) -> dict:
    with _transaction(session, write=False):
        return _record(_fresh(session, job_id))


def list_jobs(session: Session, *, kind=None, status=None, page=1, size=20) -> dict:
    if kind is not None and kind not in KINDS or status is not None and status not in STATUSES:
        raise AppError(40001, "参数非法：kind/status")
    if page < 1 or not 1 <= size <= 100:
        raise AppError(40001, "参数非法：page/size")
    conditions = []
    if kind is not None:
        conditions.append(Job.kind == kind)
    if status is not None:
        conditions.append(Job.status == status)
    with _transaction(session, write=False):
        total = session.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0
        rows = session.scalars(select(Job).where(*conditions).order_by(Job.created_at.desc(), Job.job_id.asc())
                               .offset((page - 1) * size).limit(size).execution_options(populate_existing=True))
        return {"total": total, "page": page, "size": size, "items": [_record(row) for row in rows]}


def start(session: Session, job_id: str, *, attempt: int) -> dict:
    with _transaction(session):
        job, rows = _locked(session, job_id)
        if any(row.status == "running" for row in rows):
            raise AppError(40001, "同类任务正在运行")
        data = _cas(session, job, ("queued",), {"status": "running", "started_at": now_naive_utc(),
                    "finished_at": None, "error_log": None}, attempt)
    return data


def assert_running(session: Session, job_id: str, *, attempt: int) -> dict:
    with _transaction(session, write=False):
        job, _ = _locked(session, job_id)
        _active(job, attempt)
        return _record(job)


def update_progress(session: Session, job_id: str, *, attempt: int, total=None, done=None, current_item=None, params=None) -> dict:
    with _transaction(session):
        job, _ = _locked(session, job_id)
        _active(job, attempt)
        new_total = job.total if total is None else total
        new_done = job.done if done is None else done
        if not isinstance(new_total, int) or not isinstance(new_done, int) or new_total < 0 or not 0 <= new_done <= new_total or new_done < job.done:
            raise AppError(40001, "参数非法：progress")
        values = {"total": new_total, "done": new_done}
        if current_item is not None:
            values["current_item"] = sanitize_text(str(current_item))[:64]
        if params is not None:
            values["params_json"] = _dump({**(_decode(job.params_json) or {}), **params})
        data = _cas(session, job, ("running",), values, attempt)
    return data


def finish(session: Session, job_id: str, *, attempt: int, output_ref=None) -> dict:
    with _transaction(session):
        job, _ = _locked(session, job_id)
        _active(job, attempt)
        values = {"status": "success", "finished_at": now_naive_utc(), "error_log": None}
        if output_ref is not None:
            values["output_ref_json"] = _dump(output_ref)
        data = _cas(session, job, ("running",), values, attempt)
    return data


def update_output_ref(session: Session, job_id: str, *, attempt: int, output_ref: dict) -> dict:
    with _transaction(session):
        job, _ = _locked(session, job_id)
        data = _cas(session, job, ("success",), {"output_ref_json": _dump(output_ref)}, attempt)
    return data


def fail(session: Session, job_id: str, *, attempt: int, error, output_ref=None) -> dict:
    message = sanitize_text(error.message)[:ERROR_LIMIT] if isinstance(error, AppError) else "internal error"
    with _transaction(session):
        job, _ = _locked(session, job_id)
        _active(job, attempt)
        values = {"status": "failed", "finished_at": now_naive_utc(), "error_log": message}
        if output_ref is not None:
            values["output_ref_json"] = _dump(output_ref)
        data = _cas(session, job, ("running",), values, attempt)
    return data


def retry(session: Session, job_id: str) -> dict:
    with _transaction(session):
        job, rows = _locked(session, job_id)
        if any(row.status == "running" for row in rows):
            raise AppError(40001, "同类任务正在运行")
        data = _cas(session, job, ("failed",), {"status": "queued", "retry_count": Job.retry_count + 1,
                    "started_at": None, "finished_at": None, "error_log": None, "current_item": None})
    return data


def cancel(session: Session, job_id: str) -> dict:
    with _transaction(session):
        job, _ = _locked(session, job_id)
        data = _cas(session, job, ("queued", "running"), {"status": "cancelled", "finished_at": now_naive_utc()})
    return data


def recover_running(session: Session) -> int:
    """Call only in real startup lifespan, before launching module workers."""
    with _transaction(session):
        count = 0
        for kind in sorted(KINDS):
            _lock_kind(session, kind)
            result = session.execute(update(Job).where(Job.kind == kind, Job.status == "running").values(
                status="failed", error_log="进程重启中断", finished_at=now_naive_utc()
            ).execution_options(synchronize_session=False))
            count += result.rowcount
    return count
