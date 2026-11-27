import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.storage import download, query_keys
from app.auth import require_api_key
from app.errors import ok
from app.services import evaluate_run
from app.services import file_contracts as fc

router = APIRouter(prefix='/api/evaluate', dependencies=[Depends(require_api_key)])


@router.get('/metrics')
def metrics(request: Request):
    query_keys(request, set())
    with evaluate_run.db.SessionLocal() as session:
        return ok(evaluate_run.registry_payload(session))


@router.post('/run')
async def run_evaluate(request: Request, config: Annotated[str, Form()] = '{}',
                       prediction_job_id: Annotated[str | None, Form()] = None,
                       files: Annotated[list[UploadFile] | None, File(alias='files[]')] = None):
    query_keys(request, set())
    form = await request.form()
    if set(form) - {'config', 'files[]', 'prediction_job_id'} or len(form.getlist('config')) > 1:
        fc.invalid('未知或重复的表单字段')
    if prediction_job_id:
        # 页面按文档把预测任务作为独立 part 提交；合并进 config 供服务层统一校验。
        settings = fc.read_json(config.encode('utf-8'))
        settings['prediction_job_id'] = prediction_job_id
        config = json.dumps(settings, ensure_ascii=False)
    uploaded, remaining = [], fc.MAX_UPLOAD_BYTES
    for file in files or []:
        content = await file.read(remaining + 1)
        if len(content) > remaining:
            fc.invalid('评估上传文件超过合计大小限制')
        remaining -= len(content)
        uploaded.append((file.filename or '', content))

    def submit():
        with evaluate_run.db.SessionLocal() as session:
            return evaluate_run.submit(session, config, uploaded)
    return ok(await run_in_threadpool(submit))


@router.get('/outputs/{job_id}/{name}')
def download_evaluate(request: Request, job_id: str, name: str):
    query_keys(request, set())
    return download('evaluate', job_id, name)
