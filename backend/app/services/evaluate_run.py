from __future__ import annotations

import importlib
import json
import logging
import re
import shutil
import sys
import threading
from uuid import uuid4

from sqlalchemy import select

from app import config, db
from app.errors import AppError
from app.models import Job
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.evaluate')
REQUEST_ROOT = config.TEMP_ROOT / 'evaluate_inputs'
SYNC_MAX_ROWS = 5000
_executor_lock = threading.Lock()
_wakeup = threading.Event()
_worker = None


def _module(name):
    source = str(config.REPO_ROOT / 'data_model')
    if source not in sys.path:
        sys.path.insert(0, source)
    return importlib.import_module(name)


def _core():
    return _module('evaluation.evaluate')


def _metrics():
    return _module('evaluation.metrics')


def _call(name, *args, **kwargs):
    try:
        return getattr(_core(), name)(*args, **kwargs)
    except ValueError as error:
        raise AppError(40001, job_store.sanitize_text(str(error))) from error


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def registry_payload(session):
    metrics = _metrics()
    return {'metrics': metrics.registry(),
            'defaults': {'metrics_selected': config_store.get_value('metrics_selected', session),
                         'primary_metric': config_store.get_value('primary_metric', session),
                         'effort_enabled': config_store.get_value('effort_enabled', session)}}


def _request_path(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}/request\.json', reference):
        fc.invalid('评估输入引用非法')
    directory = REQUEST_ROOT / reference.split('/')[0]
    path = directory / 'request.json'
    if REQUEST_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise AppError(40400, '评估输入已不可用，无法重试')
    return path


def _save_request(value):
    if REQUEST_ROOT.is_symlink():
        fc.invalid('评估输入目录非法')
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    content = _json(value)
    if len(content) > fc.MAX_UPLOAD_BYTES:
        directory.rmdir()
        fc.invalid('评估输入快照超过 64MiB 大小限制')
    try:
        with (directory / 'request.json').open('xb') as target:
            target.write(content)
    except Exception:
        shutil.rmtree(directory)
        raise
    return directory.name + '/request.json', fc.sha256(content)


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    settings.pop('dataset_id', None)
    defaults = {'threshold': config_store.get_value('decision_threshold', session),
                'metrics': config_store.get_value('metrics_selected', session),
                'primary_metric': config_store.get_value('primary_metric', session),
                'effort_enabled': config_store.get_value('effort_enabled', session)}
    merged = {**defaults, **settings}
    cfg = _call('validate_config', merged)
    predictions, effort, inputs = None, None, []
    if sum(len(c) for _, c in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('评估上传合计不超过 64MiB')
    for name, content in files:
        fc.validate_upload_name(name)
        columns, _ = fc.read_table(name, content)
        if columns == list(fc.PREDICTIONS_COLUMNS):
            if predictions is not None:
                fc.invalid('只能上传一个 predictions 文件')
            predictions = _call('parse_predictions', name, content)
            inputs.append({'name': name, 'sha256': fc.sha256(content), 'rows': len(predictions)})
        elif set(columns) <= set(fc.CLEAN_DATASET_COLUMNS) and set(fc.COLLECTED_COMMITS_REQUIRED) <= set(columns):
            if effort is not None:
                fc.invalid('只能上传一个 effort 来源（train_testset/clean_dataset）文件')
            effort = _call('parse_effort', name, content)
            inputs.append({'name': name, 'sha256': fc.sha256(content)})
        else:
            fc.invalid('评估文件须为 predictions 或 train_testset（clean_dataset schema）effort 来源；labels.csv 已废止')
    if predictions is None:
        fc.invalid('必须上传 predictions 文件')
    reference, digest = _save_request({'predictions': predictions, 'effort': effort, 'config': cfg, 'inputs': inputs})
    try:
        job = job_store.create(session, 'evaluate', params={'module': 'evaluate', 'input_ref': reference,
            'input_sha256': digest, 'config': cfg}, total=len(predictions) + 1)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    if len(predictions) <= SYNC_MAX_ROWS:
        _execute(job['job_id'], job['retry_count'])
        dispatch()
        current = job_store.get(session, job['job_id'])
        ref = current['output_ref_json'] or {}
        return {'job_id': current['job_id'], 'status': current['status'], 'outputs': ref.get('outputs', []),
                'summary': ref.get('summary'), 'error_log': current['error_log']}
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
    finished = False
    try:
        params = job['params_json'] or {}
        path = _request_path(params.get('input_ref'))
        if path.stat().st_size > fc.MAX_UPLOAD_BYTES:
            fc.invalid('评估输入快照超过大小限制')
        raw = path.read_bytes()
        if fc.sha256(raw) != params.get('input_sha256'):
            fc.invalid('评估输入 checksum 不一致')
        request = fc.read_json(raw)

        def progress(phase, done, total):
            with db.SessionLocal() as session:
                job_store.update_progress(session, job_id, attempt=attempt, total=max(total + 1, job['total']),
                                          done=max(done, job['done']), current_item=phase)

        result = _call('run', request['predictions'], request['config'], effort=request.get('effort'), progress=progress)
        artifacts = _call('artifacts', result, job_id)
        with db.SessionLocal() as session:
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output('evaluate', artifacts, inputs=request['inputs'],
                config=job_store.sanitize(result['config']), job_id=job_id,
                code_version=output_store.backend_code_version() + '+' + _call('code_version'))
            published = True
            reference.update(summary=result['summary'])
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
            finished = True
        return True
    except Exception as error:
        if published and not finished:
            output_store.discard_output('evaluate', job_id)
        with db.SessionLocal() as session:
            current = job_store.get(session, job_id)
        if current['status'] == 'running' and current['retry_count'] == attempt:
            try:
                with db.SessionLocal() as session:
                    job_store.fail(session, job_id, attempt=attempt, error=error)
            except AppError:
                pass
        if not isinstance(error, (AppError, ValueError)):
            logger.exception('evaluate executor failed')
        return True


def _drain():
    while True:
        with db.SessionLocal() as session:
            job = session.scalar(select(Job).where(Job.kind == 'evaluate', Job.status == 'queued',
                Job.params_json.contains('"module": "evaluate"')).order_by(Job.created_at, Job.job_id).limit(1))
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
            logger.exception('evaluate queue failed')


def dispatch():
    global _worker
    with _executor_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True, name='evaluate-worker')
            _worker.start()
        _wakeup.set()


def dispatch_retry(data):
    if data['kind'] == 'evaluate' and (data['params_json'] or {}).get('module') == 'evaluate':
        dispatch()
