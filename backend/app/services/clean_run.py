from __future__ import annotations

import importlib
import json
import logging
import re
import shutil
import sys
import threading
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import select

from app import config, db
from app.errors import AppError
from app.models import Job
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.clean')
REQUEST_ROOT = config.REPO_ROOT / 'backend' / 'var' / 'clean_inputs'
SYNC_MAX_ROWS = 2000
SYNC_MAX_BYTES = 1024 * 1024
_executor_lock = threading.Lock()
_wakeup = threading.Event()
_worker = None


@lru_cache(maxsize=1)
def _core():
    source = str(config.REPO_ROOT / 'data_model')
    if source not in sys.path:
        sys.path.insert(0, source)
    return importlib.import_module('preparation.clean')


def _call(name, *args, **kwargs):
    try:
        return getattr(_core(), name)(*args, **kwargs)
    except ValueError as error:
        raise AppError(40001, job_store.sanitize_text(str(error))) from error


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def _request_path(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}/request\.json', reference):
        fc.invalid('清洗输入引用非法')
    directory = REQUEST_ROOT / reference.split('/')[0]
    path = directory / 'request.json'
    if REQUEST_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise AppError(40400, '清洗输入已不可用，无法重试')
    return path


def _save_request(value):
    if REQUEST_ROOT.is_symlink():
        fc.invalid('清洗输入目录非法')
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    content = _json(value)
    if len(content) > fc.MAX_UPLOAD_BYTES:
        directory.rmdir()
        fc.invalid('清洗输入快照超过 64MiB 大小限制')
    try:
        with (directory / 'request.json').open('xb') as target:
            target.write(content)
    except Exception:
        shutil.rmtree(directory)
        raise
    return directory.name + '/request.json', fc.sha256(content)


def _dataset_input(session, dataset_id):
    from app.services import storage
    if not isinstance(dataset_id, str) or not dataset_id:
        fc.invalid('dataset_id 非法')
    storage.snapshot(session)
    storage.require_dataset(session, dataset_id)
    members, _ = storage.bounded_rows(session, storage.member_query(dataset_id))
    if not members:
        fc.invalid('所选数据集没有提交成员')
    records = [storage.member_record(member) for member in members]
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, records, 'csv')
    rows, metadata = _call('parse_input', 'dataset_commits.csv', content)
    metadata.update(feature_version='v1', feature_state='log_v1')
    return rows, metadata, [{'name': 'dataset_commits.csv', 'sha256': fc.sha256(content), 'rows': len(rows)}], len(content)


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    dataset_id = settings.pop('dataset_id', None)
    template = settings.pop('template', None)
    if template is not None:
        if not isinstance(template, str) or not template:
            fc.invalid('template 非法')
        templates = config_store.get_value('clean.chain_templates', session)
        if template not in templates:
            raise AppError(40400, '清洗模板不存在')
        settings = {**templates[template], **settings}
    validated = _call('validate_config', settings)
    tables, manifests = [], []
    if len(files) > 2 or sum(len(content) for _, content in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('清洗只接受一个主表和可选同名 manifest，合计不超过 64MiB')
    for name, content in files:
        fc.validate_upload_name(name)
        if name.endswith('.manifest.json'):
            manifests.append((name, content))
        elif name.rsplit('.', 1)[-1].lower() in ('csv', 'xlsx'):
            tables.append((name, content))
        else:
            fc.invalid('清洗文件格式非法')
    if tables:
        if len(tables) != 1 or len(manifests) > 1:
            fc.invalid('清洗须上传一个主表')
        name, content = tables[0]
        if manifests and manifests[0][0] != name.rsplit('.', 1)[0] + '.manifest.json':
            fc.invalid('manifest 必须与主表同名')
        rows, metadata = _call('parse_input', name, content, manifests[0][1] if manifests else None)
        inputs = [{'name': name, 'sha256': fc.sha256(content), 'rows': len(rows)}]
        inputs += [{'name': manifest_name, 'sha256': fc.sha256(raw)} for manifest_name, raw in manifests]
        byte_count = sum(len(raw) for _, raw in files)
    else:
        if manifests or dataset_id is None:
            fc.invalid('请上传提交主表或选择已导入数据集')
        rows, metadata, inputs, byte_count = _dataset_input(session, dataset_id)
    request = {'rows': rows, 'config': validated, 'metadata': metadata, 'inputs': inputs}
    reference, digest = _save_request(request)
    total = len(validated['steps']) + 1
    try:
        job = job_store.create(session, 'clean', params={'module': 'clean', 'input_ref': reference,
            'input_sha256': digest, 'config': validated}, total=total)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    if len(rows) <= SYNC_MAX_ROWS and byte_count <= SYNC_MAX_BYTES:
        _execute(job['job_id'], job['retry_count'])
        dispatch()
        current = job_store.get(session, job['job_id'])
        reference = current['output_ref_json'] or {}
        return {'job_id': current['job_id'], 'status': current['status'], 'mode': validated['mode'],
                'outputs': reference.get('outputs', []), 'summary': reference.get('summary'), 'error_log': current['error_log']}
    dispatch()
    return {'job_id': job['job_id'], 'status': job['status']}


def _execute(job_id, attempt):
    try:
        with db.SessionLocal() as session:
            job = job_store.start(session, job_id, attempt=attempt)
    except AppError as error:
        if error.code == 40001:
            return False
        raise
    published = False
    try:
        params = job['params_json'] or {}
        path = _request_path(params.get('input_ref'))
        if path.stat().st_size > fc.MAX_UNPACKED_BYTES:
            fc.invalid('清洗输入快照超过大小限制')
        raw = path.read_bytes()
        if fc.sha256(raw) != params.get('input_sha256'):
            fc.invalid('清洗输入 checksum 不一致')
        request = fc.read_json(raw)
        def progress(phase, done, total):
            with db.SessionLocal() as session:
                job_store.update_progress(session, job_id, attempt=attempt, total=max(total + 1, job['total']),
                                          done=max(done, job['done']), current_item=phase)
        result = _call('run', request['rows'], request['config'], metadata=request['metadata'], progress=progress)
        progress('publish', job['total'], job['total'] - 1)
        artifacts = _call('artifacts', result, job_id)
        version = output_store.backend_code_version() + '+' + _call('code_version')
        with db.SessionLocal() as session:
            # Keep the kind lock through publication and completion to fence stale attempts.
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output('clean', artifacts, inputs=request['inputs'],
                config=job_store.sanitize(result['config']), job_id=job_id, code_version=version)
            published = True
            reference.update(mode=request['config']['mode'], summary=result['summary'], columns=list(fc.CLEAN_DATASET_COLUMNS))
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
        return True
    except Exception as error:
        if published:
            output_store.discard_output('clean', job_id)
        with db.SessionLocal() as session:
            current = job_store.get(session, job_id)
        if current['status'] == 'running' and current['retry_count'] == attempt:
            with db.SessionLocal() as session:
                job_store.fail(session, job_id, attempt=attempt, error=error)
        if not isinstance(error, (AppError, ValueError)):
            logger.exception('clean executor failed')
        return True


def _drain():
    while True:
        with db.SessionLocal() as session:
            job = session.scalar(select(Job).where(Job.kind == 'clean', Job.status == 'queued',
                Job.params_json.contains('"module": "clean"')).order_by(Job.created_at, Job.job_id).limit(1))
            token = (job.job_id, job.retry_count) if job else None
        if token is None or not _execute(*token):
            return


def _worker_loop():
    while True:
        _wakeup.wait()
        _wakeup.clear()
        try:
            _drain()
        except Exception:
            logger.exception('clean queue failed')


def dispatch():
    global _worker
    with _executor_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True, name='clean-worker')
            _worker.start()
        _wakeup.set()


def dispatch_retry(data):
    if data['kind'] == 'clean' and (data['params_json'] or {}).get('module') == 'clean':
        dispatch()


def validate_templates(value):
    if len(value) > 30:
        fc.invalid('清洗模板最多 30 个')
    for name, template in value.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or any(ord(char) < 32 for char in name):
            fc.invalid('清洗模板名称非法')
        if not isinstance(template, dict):
            fc.invalid('清洗模板必须为配置对象')
        _call('validate_config', {'mode': 'preview', **template})
