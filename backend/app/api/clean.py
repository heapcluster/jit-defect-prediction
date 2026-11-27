import csv
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app import config
from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import AppError, ok
from app.services import clean_run
from app.services import file_contracts as fc

router = APIRouter(prefix='/api/clean', dependencies=[Depends(require_api_key)])


@router.get('/operations')
def operations(request: Request):
    query_keys(request, set())
    return ok({'operations': clean_run._call('operations'), 'features': list(config.FEATURE_COLUMNS)})


@router.post('/run')
async def run_clean(request: Request, config: Annotated[str, Form()] = '{}',
                    files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]'} or len(form.getlist('config')) > 1:
        fc.invalid('未知或重复的表单字段')
    if len(files or []) > 2:
        fc.invalid('清洗只接受一个主表和可选同名 manifest')
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid('清洗上传文件超过合计大小限制')
        remaining -= len(content)
        uploaded.append((file.filename or '', content))
    def submit():
        with clean_run.db.SessionLocal() as session:
            return clean_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get('/preview/{job_id}')
def preview_clean(request: Request, job_id: str, page: int = Query(default=1, ge=1),
                  size: int = Query(default=20, ge=1, le=100)):
    query_keys(request, {'page', 'size'})
    with clean_run.db.SessionLocal() as session:
        job = clean_run.job_store.get(session, job_id)
    reference = job['output_ref_json'] or {}
    if job['kind'] != 'clean' or reference.get('mode') != 'apply':
        fc.invalid('仅成功 apply 任务提供 cleaned 主表预览')
    csv_name = next((item['name'] for item in reference.get('outputs', []) if item['name'].endswith('.csv')), None)
    if csv_name is None:
        fc.invalid('输出缺少清洗主表')
    path = clean_run.output_store.read_output('clean', job_id, csv_name)
    try:
        with path.open(encoding='utf-8-sig', newline='') as source:
            reader = csv.DictReader(source)
            if tuple(reader.fieldnames or ()) != tuple(fc.CLEAN_DATASET_COLUMNS):
                fc.invalid('输出预览列与契约不一致')
            records = [{key: value if value != '' else None for key, value in row.items()} for row in reader]
    except csv.Error as error:
        raise AppError(40001, '输出表格无法预览') from error
    total = len(records)
    start = (page - 1) * size
    return ok({'columns': list(fc.CLEAN_DATASET_COLUMNS), 'preview': records[start:start + size],
               'total': total, 'page': page, 'size': size})


@router.get('/outputs/{job_id}/{name}')
def download_clean(request: Request, job_id: str, name: str, format: str = Query(default='csv')):
    query_keys(request, {'format'})
    if format not in ('csv', 'xlsx'):
        fc.invalid('format 仅支持 csv/xlsx')
    if format == 'csv':
        return download('clean', job_id, name)
    # 清洗数据只保存一份 CSV；Excel 在下载时按需转换，不落产物目录、不登记新产物。
    if not name.endswith('.csv'):
        fc.invalid('仅清洗后的 CSV 支持导出格式转换')
    path = clean_run.output_store.read_output('clean', job_id, name)
    columns, rows = fc.read_table(name, path.read_bytes())
    if tuple(columns) != tuple(fc.CLEAN_DATASET_COLUMNS):
        fc.invalid('输出列与契约不一致')
    content = fc.encode_table(fc.CLEAN_DATASET_COLUMNS, rows, 'xlsx')
    return Response(content=content, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': f'attachment; filename="{name[:-4]}.xlsx"'})
