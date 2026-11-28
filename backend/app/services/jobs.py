"""异步任务：DB 持久化状态、单用户单运行中任务、取消与重新调度。"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.errors import AppError
from app.models import Job, User
from app.utils import dumps, iso, loads, new_id, now

logger = logging.getLogger("backend.jobs")

RUNNING_STATUSES = ("queued", "running")


class JobCancelled(Exception):
    pass


class JobContext:
    def __init__(self, job_id: str, user_id: str, params: dict, cancel_event: threading.Event) -> None:
        self.job_id = job_id
        self.user_id = user_id
        self.params = params
        self._cancel = cancel_event
        self._done = 0
        self._total = 0
        self._stage: str | None = None
        self._last_flush = 0.0

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    def check(self) -> None:
        if self._cancel.is_set():
            raise JobCancelled()

    def set_total(self, total: int) -> None:
        self._total = int(total)
        self.update()

    def set_stage(self, stage: str) -> None:
        self._stage = stage[:64]
        self.update(force=True)

    def advance(self, n: int = 1, stage: str | None = None) -> None:
        self._done += n
        if stage:
            self._stage = stage[:64]
        self.update()

    def set_done(self, done: int) -> None:
        self._done = int(done)
        self.update()

    def update(self, *, force: bool = False) -> None:
        self.check()
        current = time.monotonic()
        if not force and current - self._last_flush < 0.5:
            return
        self._last_flush = current
        with SessionLocal() as db:
            job = db.get(Job, self.job_id)
            if job is None or job.status == "cancelled":
                raise JobCancelled()
            job.done = self._done
            job.total = self._total
            job.current_stage = self._stage
            db.commit()

    def set_output(self, payload: dict) -> None:
        with SessionLocal() as db:
            job = db.get(Job, self.job_id)
            if job is None:
                raise JobCancelled()
            job.output_ref_json = dumps(payload)
            db.commit()


class JobManager:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jit-job")
        self._events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def create(self, db: Session, user: User, kind: str, params: dict, total: int = 0) -> Job:
        running = db.scalar(
            select(Job).where(
                Job.owner_user_id == user.user_id, Job.status.in_(RUNNING_STATUSES)
            )
        )
        if running is not None:
            raise AppError(42901, "当前已有运行中的任务，请稍后再试")
        job = Job(
            job_id=new_id("job"),
            owner_user_id=user.user_id,
            kind=kind,
            status="queued",
            params_json=dumps(params),
            total=total,
            done=0,
            created_at=now(),
        )
        db.add(job)
        db.commit()
        return job

    def start(self, job_id: str, handler: Callable[[JobContext], None]) -> None:
        event = threading.Event()
        with self._lock:
            self._events[job_id] = event
        self._executor.submit(self._run, job_id, handler, event)

    def _run(self, job_id: str, handler: Callable[[JobContext], None], event: threading.Event) -> None:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            if job is None:
                return
            if job.status == "cancelled":
                return
            job.status = "running"
            job.started_at = now()
            db.commit()
            params = loads(job.params_json, {}) or {}
            user_id = job.owner_user_id
        context = JobContext(job_id, user_id, params, event)
        try:
            handler(context)
            context.check()
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                if job is not None and job.status != "cancelled":
                    job.status = "success"
                    if job.total:
                        job.done = job.total
                    job.current_stage = "完成"
                    job.finished_at = now()
                    db.commit()
        except JobCancelled:
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                if job is not None:
                    job.status = "cancelled"
                    job.finished_at = now()
                    db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("job %s failed", job_id)
            with SessionLocal() as db:
                job = db.get(Job, job_id)
                if job is not None and job.status != "cancelled":
                    job.status = "failed"
                    job.error_message = str(exc)[:1000] or "任务执行失败"
                    job.finished_at = now()
                    db.commit()
        finally:
            with self._lock:
                self._events.pop(job_id, None)

    def cancel(self, db: Session, user: User, job_id: str) -> dict:
        job = db.get(Job, job_id)
        if job is None or job.owner_user_id != user.user_id:
            raise AppError(40401, "任务不存在")
        if job.status not in RUNNING_STATUSES:
            raise AppError(40901, "任务已结束，无法取消")
        job.status = "cancelled"
        job.finished_at = now()
        db.commit()
        with self._lock:
            event = self._events.get(job_id)
        if event:
            event.set()
        return {"status": "cancelled"}

    def recover(self) -> None:
        with SessionLocal() as db:
            stale = db.scalars(select(Job).where(Job.status == "running")).all()
            for job in stale:
                job.status = "failed"
                job.error_message = "服务重启导致中断"
                job.finished_at = now()
            db.commit()

    def redispatch(self) -> None:
        """重新调度 queued 任务（本进程内无对应 handler 时留给后续启动）。"""
        return


manager = JobManager()


def serialize(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "status": job.status,
        "params": loads(job.params_json, {}) or {},
        "done": job.done,
        "total": job.total,
        "current_stage": job.current_stage,
        "error_message": job.error_message,
        "created_at": iso(job.created_at),
        "started_at": iso(job.started_at),
        "finished_at": iso(job.finished_at),
    }
