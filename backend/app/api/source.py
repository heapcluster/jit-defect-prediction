from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app import db
from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import file_contracts as fc
from app.services import localize_run

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get('/api/source/tree')
def tree(request: Request, commit_hash: str, path: str = '', search: str | None = None,
         repo_source: str | None = None, dataset_id: str | None = None):
    query_keys(request, {'commit_hash', 'path', 'search', 'repo_source', 'dataset_id'})
    with db.SessionLocal() as session:
        return ok(localize_run.source(session, 'tree', repo_source=repo_source, dataset_id=dataset_id,
                                     commit_hash=commit_hash, path=path, search=search))


@router.get('/api/source/file')
def file(request: Request, commit_hash: str, path: str, repo_source: str | None = None, dataset_id: str | None = None,
         start_line: int = Query(default=1, ge=1), end_line: int | None = Query(default=None, ge=1)):
    query_keys(request, {'commit_hash', 'path', 'repo_source', 'dataset_id', 'start_line', 'end_line'})
    with db.SessionLocal() as session:
        return ok(localize_run.source(session, 'file', repo_source=repo_source, dataset_id=dataset_id,
                                     commit_hash=commit_hash, path=path, start_line=start_line, end_line=end_line))


@router.post('/api/localize/run')
async def run_localize(request: Request, config: Annotated[str, Form()] = '{}',
                       files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]'} or len(form.getlist('config')) > 1 or len(files or []) > 4:
        fc.invalid('定位上传字段重复、未知或文件过多')
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid('定位上传合计超过 64MiB')
        remaining -= len(content)
        uploaded.append((file.filename or '', content))
    def submit():
        with db.SessionLocal() as session:
            return localize_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get('/api/localize/outputs/{job_id}/{name}')
def output(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('localize', job_id, name)
