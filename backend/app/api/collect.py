"""数据收集页接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, export_filename
from app.db import get_db
from app.errors import AppError, ok
from app.models import Job, User
from app.schemas import CollectPrecheckRequest, CollectRunRequest
from app.services import artifacts, collect, jobs, storage
from app.utils import loads

router = APIRouter(prefix="/collect", tags=["collect"])


def _job(db: Session, user: User, job_id: str, kind: str = "collect") -> tuple[Job, dict]:
    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    if job.kind != kind:
        raise AppError(40001, "任务类型不匹配")
    if job.status != "success":
        raise AppError(40901, "任务尚未成功结束")
    ref = loads(job.output_ref_json, {}) or {}
    if not ref.get("data_path"):
        raise AppError(40901, "结果已失效")
    return job, ref


def _core_columns(ref: dict) -> list[str]:
    columns = ref.get("columns") or []
    features = [name for name in columns if name not in ("project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "bug")]
    return ["commit_id", "commit_time", "author_name", "bug"] + features[:6]


def result_rows(db: Session, user: User, job_id: str, page: int, page_size: int, kind: str = "collect") -> dict:
    _, ref = _job(db, user, job_id, kind)
    _, rows = artifacts.read_table(artifacts.resolve(ref["data_path"]))
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    start = (page - 1) * page_size
    columns = _core_columns(ref)
    items = [{name: row.get(name, "") for name in columns} for row in rows[start : start + page_size]]
    summary = ref.get("summary") or {"total": len(rows), "pos": 0, "neg": 0}
    return {"summary": summary, "columns": columns, "items": items, "total": len(rows), "page": page, "page_size": page_size}


def export_result(db: Session, user: User, job_id: str, filename: str, fmt: str, kind: str = "collect") -> Response:
    _, ref = _job(db, user, job_id, kind)
    columns, rows = artifacts.read_table(artifacts.resolve(ref["data_path"]))
    name = export_filename(filename, f"{kind}-{job_id[4:12]}")
    if fmt not in ("csv", "excel"):
        raise AppError(40001, "导出格式非法")
    if fmt == "excel":
        return Response(
            content=artifacts.table_bytes(columns, rows, "excel"),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}.xlsx"},
        )
    return Response(
        content=artifacts.table_bytes(columns, rows, "csv"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}.csv"},
    )


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")


@router.get("/branches")
def branches(repo_url: str = Query(...), user: User = Depends(current_user)) -> dict:
    return ok(collect.branch_list(repo_url))


@router.post("/precheck")
def precheck(
    payload: CollectPrecheckRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    conf = storage.effective_config(db, user)
    return ok(collect.precheck(
        payload.repo_url, payload.branch, payload.mode,
        int(conf["estimate_warn_minutes"]), int(conf["estimate_danger_minutes"]),
    ))


@router.post("/run", status_code=202)
def run(payload: CollectRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if payload.mode not in ("expert", "semantic"):
        raise AppError(40001, "解析方式非法")
    collect.parse_repo(payload.repo_url)
    if not payload.branch:
        raise AppError(40001, "分支不能为空")
    job = jobs.manager.create(db, user, "collect", payload.model_dump())
    jobs.manager.start(job.job_id, collect.run_collect)
    return ok({"job_id": job.job_id})


@router.get("/results/{job_id}/rows")
def rows(
    job_id: str,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ok(result_rows(db, user, job_id, page, page_size))


@router.get("/results/{job_id}/export")
def export(
    job_id: str,
    filename: str = Query(...),
    format: str = "csv",
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    return export_result(db, user, job_id, filename, format)
