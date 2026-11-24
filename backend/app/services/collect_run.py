from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import re
import shutil
import sys
import threading
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from app import config, db
from app.errors import AppError
from app.models import Dataset, DatasetCommit, Job
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.collect')
REQUEST_ROOT = config.REPO_ROOT / 'backend' / 'var' / 'collect_inputs'
CACHE_ROOT = config.REPO_ROOT / 'backend' / 'var' / 'collect_cache'
_executor_lock = threading.Lock()


@lru_cache(maxsize=1)
def _core():
    source = str(config.REPO_ROOT / 'data_model')
    if source not in sys.path:
        sys.path.insert(0, source)
    path = config.REPO_ROOT / 'data_model' / 'preparation' / 'collect.py'
    spec = importlib.util.spec_from_file_location('jit_collect', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _call(name, *args, **kwargs):
    module = _core()
    try:
        return getattr(module, name)(*args, **kwargs)
    except module.CollectError as error:
        raise AppError(error.code, job_store.sanitize_text(error.message)) from error


def _policy(session):
    values = config_store.read_config(session, ['collect.allow_roots', 'collect.protocol_whitelist'])
    return {item['config_key'].split('.', 1)[1]: item['value'] for item in values}


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def _request_path(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}/request\.json', reference):
        raise AppError(40001, '收集输入引用非法')
    directory = REQUEST_ROOT / reference.split('/')[0]
    path = directory / 'request.json'
    if REQUEST_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise AppError(40400, '收集输入已不可用，无法重试')
    return path


def _save_request(value):
    if REQUEST_ROOT.is_symlink():
        raise AppError(40001, '收集输入目录非法')
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    content = _json(value)
    try:
        with (directory / 'request.json').open('xb') as target:
            target.write(content)
    except Exception:
        shutil.rmtree(directory)
        raise
    return directory.name + '/request.json', fc.sha256(content)


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    hashes, inputs = [], []
    if len(files) > 1:
        fc.invalid('收集只接受一个 CSV/XLSX 提交清单')
    for name, content in files:
        columns, records = fc.read_table(name, content)
        if columns != ['commit_hash'] or not records:
            fc.invalid('提交清单必须仅含 commit_hash 列且至少一行')
        for row in records:
            value = row['commit_hash']
            if not re.fullmatch(r'[0-9a-fA-F]{40}', value):
                fc.invalid('提交清单含非法哈希')
            hashes.append(value.lower())
        inputs.append({'name': name, 'sha256': fc.sha256(content), 'rows': len(records)})
    dataset_id = settings.pop('dataset_id', None)
    if dataset_id is not None:
        if not isinstance(dataset_id, str) or not dataset_id:
            fc.invalid('dataset_id 非法')
        dataset = session.get(Dataset, dataset_id)
        if dataset is None:
            raise AppError(40400, '数据集未登记')
        if 'repo_source' not in settings:
            settings['repo_source'] = dataset.repo_source
        if 'branch' not in settings and dataset.branch:
            settings['branch'] = dataset.branch
        if not hashes:
            hashes = list(session.scalars(select(DatasetCommit.commit_hash).where(DatasetCommit.dataset_id == dataset_id)))
            if not hashes:
                fc.invalid('所选数据集没有提交')
            inputs.append({'name': 'dataset_commits.json', 'sha256': fc.sha256(_json(sorted(hashes))), 'rows': len(hashes)})
    validated = _call('validate_config', settings, **_policy(session))
    reference, digest = _save_request({'config': validated, 'commit_hashes': hashes or None, 'inputs': inputs})
    try:
        job = job_store.create(session, 'collect', params={
            'module': 'collect', 'input_ref': reference, 'input_sha256': digest,
            'config': validated,
        }, total=5)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    dispatch()
    return {'job_id': job['job_id'], 'status': job['status']}


def _code_version():
    digest = hashlib.sha256()
    directory = config.REPO_ROOT / 'data_model' / 'preparation'
    for path in sorted(directory.glob('*.py')):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return output_store.backend_code_version() + '+collect.' + digest.hexdigest()[:16]


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
        raw = path.read_bytes()
        if len(raw) > fc.MAX_UPLOAD_BYTES or fc.sha256(raw) != params.get('input_sha256'):
            raise AppError(40001, '收集输入 checksum 不一致')
        request = fc.read_json(raw)
        with db.SessionLocal() as session:
            policy = _policy(session)

        def progress(phase, done, total):
            with db.SessionLocal() as session:
                job_store.update_progress(session, job_id, attempt=attempt, total=max(total, job['total']),
                                          done=max(done, job['done']), current_item=phase)

        result = _call('run', request['config'], **policy, commit_hashes=request['commit_hashes'],
                       progress=progress, cache_dir=CACHE_ROOT)
        progress('publish', 5, 5)
        settings = job_store.sanitize(result['config'])
        settings['source_fingerprint'] = fc.sha256(_json(request['config']))
        base = f'collect_commits_{job_id}'
        artifacts = {base + '.csv': _call('encode_rows', result['rows'], 'csv'),
                     base + '.xlsx': _call('encode_rows', result['rows'], 'xlsx'),
                     f'collect_summary_{job_id}.json': _json(job_store.sanitize(result['summary'])),
                     f'collect_audit_{job_id}.json': _json(job_store.sanitize(result['audit']))}
        inputs = []
        for item in result['inputs']:
            if item.get('name') == 'repository_snapshot.json' and item.get('path'):
                content = Path(item['path']).read_bytes()
                if fc.sha256(content) != item['sha256']:
                    fc.invalid('仓库输入快照 checksum 不一致')
                artifacts[f'collect_repository_snapshot_{job_id}.json'] = content
            inputs.append({key: value for key, value in item.items() if key != 'path'})
        reference = output_store.publish_output('collect', artifacts,
            inputs=inputs + request['inputs'], config=settings, job_id=job_id, code_version=_code_version())
        published = True
        reference['summary'] = result['summary']
        reference['columns'] = list(fc.COLLECTED_COMMITS_COLUMNS)
        with db.SessionLocal() as session:
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
        return True
    except Exception as error:
        if published:
            output_store.discard_output('collect', job_id)
        with db.SessionLocal() as session:
            current = job_store.get(session, job_id)
        if current['status'] == 'running' and current['retry_count'] == attempt:
            with db.SessionLocal() as session:
                job_store.fail(session, job_id, attempt=attempt, error=error)
        if not isinstance(error, AppError):
            logger.exception('collect executor failed')
        return True


def _drain():
    with _executor_lock:
        while True:
            with db.SessionLocal() as session:
                job = session.scalar(select(Job).where(
                    Job.kind == 'collect', Job.status == 'queued',
                    Job.params_json.contains('"module": "collect"'),
                ).order_by(Job.created_at, Job.job_id).limit(1))
                token = (job.job_id, job.retry_count) if job is not None else None
            if token is None or not _execute(*token):
                return


def dispatch():
    threading.Thread(target=_drain, daemon=True, name='collect-worker').start()


def dispatch_retry(data):
    if data['kind'] == 'collect' and (data['params_json'] or {}).get('module') == 'collect':
        dispatch()
