import csv
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import collect_run
from app.services import file_contracts as fc

router = APIRouter(prefix='/api/collect', dependencies=[Depends(require_api_key)])


@router.get('/branches')
def list_branches(request: Request, repo_source: str = Query(...)):
    query_keys(request, {'repo_source'})
    with collect_run.db.SessionLocal() as session:
        return ok(collect_run.branches(session, repo_source))


@router.post('/source-columns')
async def source_columns(request: Request):
    query_keys(request, set())
    payload = fc.read_json(await request.body())
    if set(payload) != {'source_url'}:
        fc.invalid('只接受 source_url')
    with collect_run.db.SessionLocal() as session:
        return ok(collect_run.source_columns(session, payload['source_url']))


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
def preview_collect(request: Request, job_id: str, page: int = Query(default=1, ge=1),
                    size: int = Query(default=20, ge=1, le=100)):
    query_keys(request, {'page', 'size'})
    path = collect_run.output_store.read_output('collect', job_id, f'collected_commits_{job_id}.csv')
    try:
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            columns = reader.fieldnames
            if tuple(columns or ()) != tuple(fc.COLLECTED_COMMITS_COLUMNS):
                fc.invalid('输出预览列与契约不一致')
            records = [{key: (value if value != '' else None) for key, value in row.items()}
                       for row in reader]
    except csv.Error as error:
        fc.invalid(f'无法预览表格：{error}')
    total = len(records)
    start = (page - 1) * size
    return ok({'columns': columns, 'preview': records[start:start + size],
               'total': total, 'page': page, 'size': size})


@router.post('/resave/{job_id}')
async def resave_collect(request: Request, job_id: str):
    query_keys(request, set())

    def resave():
        with collect_run.db.SessionLocal() as session:
            return collect_run.resave(session, job_id)

    return ok(await run_in_threadpool(resave))


@router.get('/outputs/{job_id}/{name}')
def download_collect(request: Request, job_id: str, name: str, format: str = Query(default='csv')):
    query_keys(request, {'format'})
    if format not in ('csv', 'xlsx'):
        fc.invalid('format 仅支持 csv/xlsx')
    if format == 'csv':
        return download('collect', job_id, name)
    # 新契约不预生成 XLSX；仅对核心 CSV 即时转换，不写入产物目录、不登记新产物。
    core = f'collected_commits_{job_id}.csv'
    if name != core:
        fc.invalid('仅核心 CSV 支持导出格式转换')
    path = collect_run.output_store.read_output('collect', job_id, core)
    columns, rows = fc.read_table(core, path.read_bytes())
    if tuple(columns) != tuple(fc.COLLECTED_COMMITS_COLUMNS):
        fc.invalid('输出列与契约不一致')
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows, 'xlsx')
    return Response(content=content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="collected_commits_{job_id}.xlsx"'})
