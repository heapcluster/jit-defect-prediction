from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, ConfigDict
from starlette.concurrency import run_in_threadpool

from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import explain_run
from app.services import file_contracts as fc

router = APIRouter(prefix="/api/explain", dependencies=[Depends(require_api_key)])


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    commit_hash: str
    model_name: str
    technique: str | None = None
    params: dict | None = None


@router.get("/techniques")
def techniques(request: Request, line: str | None = None, model_name: str | None = None):
    query_keys(request, {"line", "model_name"})
    with explain_run.db.SessionLocal() as session:
        return ok(explain_run.techniques_payload(session, line, model_name))


@router.post("")
def single(body: ExplainRequest):
    with explain_run.db.SessionLocal() as session:
        return ok(
            explain_run.explain_single(
                session, body.commit_hash, body.model_name, body.technique, body.params
            )
        )


@router.post("/run")
async def run_explain(
    request: Request,
    config: Annotated[str, Form()] = "{}",
    files: Annotated[list[UploadFile] | None, File(alias="files[]")] = None,
):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {"config", "files[]"} or len(form.getlist("config")) > 1 or len(files or []) > 6:
        fc.invalid("解释上传字段重复、未知或文件过多")
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid("解释上传合计超过 64MiB")
        uploaded.append((file.filename or "", content))
        remaining -= len(content)

    def submit():
        with explain_run.db.SessionLocal() as session:
            return explain_run.submit(session, config, uploaded)

    return ok(await run_in_threadpool(submit))


@router.get("/outputs/{job_id}/{name}")
def output(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download("explain", job_id, name)
