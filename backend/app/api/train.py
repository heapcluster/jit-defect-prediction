from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import file_contracts as fc
from app.services import train_run

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get('/api/algorithms')
def algorithms(request: Request, line: str | None = None, enabled_only: int = Query(default=0)):
    query_keys(request, {'line', 'enabled_only'})
    if enabled_only not in (0, 1):
        fc.invalid('enabled_only 只允许 0/1')
    with train_run.db.SessionLocal() as session:
        return ok({'algorithms': train_run.list_algorithms(session, line=line, enabled_only=bool(enabled_only))})


@router.post('/api/train/run')
async def run_train(request: Request, config: Annotated[str, Form()] = '{}',
                    files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]'} or len(form.getlist('config')) > 1:
        fc.invalid('未知或重复的表单字段')
    if len(files or []) > 2:
        fc.invalid('训练只接受一个主表和可选同名 manifest')
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid('训练上传文件超过合计大小限制')
        remaining -= len(content)
        uploaded.append((file.filename or '', content))

    def submit():
        with train_run.db.SessionLocal() as session:
            return train_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get('/api/train/outputs/{job_id}/{name}')
def download_train(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('train', job_id, name)
