import csv
from itertools import islice
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import collect_run
from app.services import file_contracts as fc

router = APIRouter(prefix='/api/collect', dependencies=[Depends(require_api_key)])


@router.post('/run')
async def run_collect(request: Request, config: Annotated[str, Form()] = '{}',
                      files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]'} or len(form.getlist('config')) > 1:
        fc.invalid('未知或重复的表单字段')
    uploaded = []
    for file in files or []:
        content = await file.read(fc.MAX_UPLOAD_BYTES + 1)
        if len(content) > fc.MAX_UPLOAD_BYTES:
            fc.invalid('上传提交清单超过大小限制')
        uploaded.append((file.filename or '', content))

    def submit():
        with collect_run.db.SessionLocal() as session:
            return collect_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get('/preview/{job_id}')
def preview_collect(request: Request, job_id: str):
    query_keys(request, set())
    path = collect_run.output_store.read_output('collect', job_id, f'collect_commits_{job_id}.csv')
    try:
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames
            if columns != list(fc.COMMITS_COLUMNS):
                fc.invalid('输出预览列与契约不一致')
            rows = [{key: (value if value != '' else None) for key, value in row.items()}
                    for row in islice(reader, 20)]
    except csv.Error as error:
        fc.invalid(f'无法预览表格：{error}')
    return ok({'columns': columns, 'preview': rows})


@router.get('/outputs/{job_id}/{name}')
def download_collect(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('collect', job_id, name)
