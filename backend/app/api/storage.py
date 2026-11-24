from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.db import get_db
from app.errors import ok
from app.services import file_contracts as fc
from app.services import output_store, storage

router = APIRouter(prefix="/api/storage", dependencies=[Depends(require_api_key)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def query_keys(request: Request, allowed):
    if set(request.query_params) - set(allowed) or any(len(request.query_params.getlist(key)) > 1 for key in request.query_params):
        fc.invalid("unknown or duplicate query filters")


def download(module, job_id, name):
    path = output_store.read_output(module, job_id, name)
    return FileResponse(path, filename=name, headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'"})


@router.post("/import")
async def import_storage(session: DatabaseSession, files: Annotated[list[UploadFile], File(alias="files[]")], config: Annotated[str, Form()] = "{}"):
    if len(files) > 100:
        fc.invalid("too many uploaded files")
    uploaded, total = [], 0
    for file in files:
        content = await file.read(fc.MAX_UPLOAD_BYTES + 1)
        total += len(content)
        if total > fc.MAX_UPLOAD_BYTES:
            fc.invalid("batch upload exceeds size limit")
        uploaded.append((file.filename or "", content))
    return ok(storage.import_files(session, uploaded, config))


@router.get("/export")
def export_storage(request: Request, session: DatabaseSession, table: str, format: str = "csv", dataset_id: str | None = None,
                   model_name: str | None = None, start_time: str | None = None, end_time: str | None = None,
                   limit: int | None = Query(default=None, ge=1, le=100000)):
    query_keys(request, {"table", "format", "dataset_id", "model_name", "start_time", "end_time", "limit"})
    return ok(storage.export_table(session, table, format, dataset_id, model_name, start_time, end_time, limit))


@router.get("/outputs/{job_id}/{name}")
def download_storage(job_id: str, name: str):
    return download("storage", job_id, name)
