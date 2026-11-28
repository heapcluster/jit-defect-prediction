"""数据清洗页接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.collect import _quote, export_result, result_rows
from app.api.deps import current_user
from app.db import get_db
from app.errors import AppError, ok
from app.models import Job, User
from app.schemas import CleanRunRequest
from app.services import artifacts, clean, jobs, uploads
from app.utils import loads

router = APIRouter(prefix="/clean", tags=["clean"])


@router.post("/import")
async def import_file(file: UploadFile = File(...), user: User = Depends(current_user)) -> dict:
    payload = await file.read()
    result = uploads.save_data_upload(
        user.user_id, file.filename or "", payload, "clean", require_unique=False
    )
    columns, rows = result["columns"], result["rows"]
    return ok({
        "file_id": result["meta"]["file_id"],
        "line": result["meta"]["line"],
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "preview": [{name: row.get(name, "") for name in columns} for row in rows[:10]],
    })


@router.post("/run", status_code=202)
def run(payload: CleanRunRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if not payload.operations:
        raise AppError(40001, "至少选择一个清洗操作")
    job = jobs.manager.create(db, user, "clean", payload.model_dump())
    jobs.manager.start(job.job_id, clean.run_clean)
    return ok({"job_id": job.job_id})


def _ref(db: Session, user: User, job_id: str) -> dict:
    job = db.get(Job, job_id)
    if job is None or job.owner_user_id != user.user_id:
        raise AppError(40401, "任务不存在")
    if job.kind != "clean" or job.status != "success":
        raise AppError(40901, "任务尚未成功结束")
    ref = loads(job.output_ref_json, {}) or {}
    if not ref.get("data_path"):
        raise AppError(40901, "结果已失效")
    return ref


@router.get("/results/{job_id}/steps")
def steps(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ref = _ref(db, user, job_id)
    path = artifacts.resolve(ref["data_path"]).parent / "steps.json"
    if not path.is_file():
        raise AppError(40901, "步骤记录已失效")
    return ok(artifacts.read_json(path))


@router.get("/results/{job_id}/rows")
def rows(
    job_id: str, page: int = 1, page_size: int = 20,
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    return ok(result_rows(db, user, job_id, page, page_size, kind="clean"))


@router.get("/results/{job_id}/export")
def export(
    job_id: str, filename: str = Query(...), format: str = "csv",
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response:
    return export_result(db, user, job_id, filename, format, kind="clean")
