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
from app.models import Algorithm, Job
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.train')
REQUEST_ROOT = config.REPO_ROOT / 'backend' / 'var' / 'train_inputs'
SYNC_MAX_ROWS = 2000
SYNC_ALGOS = {'lr', 'nb', 'dt', 'knn', 'rf', 'et'}
_executor_lock = threading.Lock()
_wakeup = threading.Event()
_worker = None


def _path_module(name):
    source = str(config.REPO_ROOT / 'data_model')
    if source not in sys.path:
        sys.path.insert(0, source)
    return importlib.import_module(name)


@lru_cache(maxsize=1)
def _core():
    return _path_module('pipelines.train')


@lru_cache(maxsize=1)
def _registry():
    return _path_module('pipelines.registry')


def _call(name, *args, **kwargs):
    try:
        return getattr(_core(), name)(*args, **kwargs)
    except ValueError as error:
        raise AppError(40001, job_store.sanitize_text(str(error))) from error


def _parse_table(name, content, manifest=None):
    try:
        return _path_module('preparation.clean').parse_input(name, content, manifest)
    except ValueError as error:
        raise AppError(40001, job_store.sanitize_text(str(error))) from error


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def ensure_algorithms(session):
    snapshot = _registry().algorithms()
    inserted = False
    for item in snapshot:
        if session.get(Algorithm, (item['line'], item['algo'])) is None:
            session.add(Algorithm(line=item['line'], algo=item['algo'], family=item['family'],
                hyperparams_json=json.dumps(item['hyperparams_schema'], ensure_ascii=False),
                enabled=int(item['enabled']), description=item['description']))
            inserted = True
    if inserted:
        session.commit()


def list_algorithms(session, line=None, enabled_only=False):
    if line is not None and line not in ('expert', 'semantic'):
        fc.invalid('line 非法')
    ensure_algorithms(session)
    query = select(Algorithm)
    if line:
        query = query.where(Algorithm.line == line)
    if enabled_only:
        query = query.where(Algorithm.enabled == 1)
    rows = session.scalars(query.order_by(Algorithm.line, Algorithm.algo)).all()
    return [{'line': r.line, 'algo': r.algo, 'family': r.family, 'enabled': bool(r.enabled),
             'description': r.description, 'hyperparams_schema': json.loads(r.hyperparams_json),
             'input_requirements': next((s['input_requirements'] for s in _registry().algorithms()
                                         if s['line'] == r.line and s['algo'] == r.algo), '')} for r in rows]


def validate_templates(value):
    if len(value) > 30:
        fc.invalid('训练模板最多 30 个')
    for name, template in value.items():
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or any(ord(c) < 32 for c in name):
            fc.invalid('训练模板名称非法')
        if not isinstance(template, dict) or 'line' not in template or 'algos' not in template:
            fc.invalid('训练模板必须含 line 与 algos')
        allowed = {'line', 'algos', 'hyperparams', 'split', 'seed', 'decision_threshold', 'register', 'auto_load'}
        if set(template) - allowed:
            fc.invalid('训练模板含未知字段')
        _call('validate_config', {'line': template['line'], 'algos': template['algos'],
            'hyperparams': template.get('hyperparams', {}), 'split': template.get('split', {'ratio': 0.7}),
            'seed': template.get('seed', 42), 'decision_threshold': template.get('decision_threshold', 0.5),
            'register': template.get('register', False), 'auto_load': template.get('auto_load', False)})


def _request_path(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}/request\.json', reference):
        fc.invalid('训练输入引用非法')
    directory = REQUEST_ROOT / reference.split('/')[0]
    path = directory / 'request.json'
    if REQUEST_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise AppError(40400, '训练输入已不可用，无法重试')
    return path


def _save_request(value):
    if REQUEST_ROOT.is_symlink():
        fc.invalid('训练输入目录非法')
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    content = _json(value)
    if len(content) > fc.MAX_UPLOAD_BYTES:
        directory.rmdir()
        fc.invalid('训练输入快照超过 64MiB 大小限制')
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
    dataset = storage.require_dataset(session, dataset_id)
    members, _ = storage.bounded_rows(session, storage.member_query(dataset_id))
    if not members:
        fc.invalid('所选数据集没有提交成员')
    records = [storage.member_record(member) for member in members]
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, records, 'csv')
    rows, metadata = _parse_table('dataset_commits.csv', content)
    # 训练内核从绑定仓库现算 14 维；仓库来源取数据集登记的本地路径或 URL。
    source = dataset.source_url or dataset.repo_source
    if not source or '://' in source:
        fc.invalid('dataset 未绑定可读取的本地仓库，无法在训练内现算特征')
    metadata.update(feature_version='v1', repo=source)
    return rows, metadata, [{'name': 'dataset_commits.csv', 'sha256': fc.sha256(content), 'rows': len(rows)}], len(content)


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    dataset_id = settings.pop('dataset_id', None)
    template_name = settings.pop('template_name', None)
    if template_name is not None:
        if not isinstance(template_name, str) or not template_name:
            fc.invalid('template_name 非法')
        templates = config_store.get_value('train.templates', session)
        if template_name not in templates:
            raise AppError(40400, '训练模板不存在')
        settings = {**templates[template_name], **settings}
    if 'decision_threshold' not in settings:
        settings['decision_threshold'] = config_store.get_value('decision_threshold', session)
    validated = _call('validate_config', settings)
    tables, manifests = [], []
    if len(files) > 2 or sum(len(c) for _, c in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('训练只接受一个主表和可选同名 manifest，合计不超过 64MiB')
    for name, content in files:
        fc.validate_upload_name(name)
        if name.endswith('.manifest.json'):
            manifests.append((name, content))
        elif name.rsplit('.', 1)[-1].lower() in ('csv', 'xlsx'):
            tables.append((name, content))
        else:
            fc.invalid('训练文件格式非法')
    if tables:
        if len(tables) != 1 or len(manifests) > 1:
            fc.invalid('训练须上传一个主表')
        name, content = tables[0]
        if manifests and manifests[0][0] != name.rsplit('.', 1)[0] + '.manifest.json':
            fc.invalid('manifest 必须与主表同名')
        rows, metadata = _parse_table(name, content, manifests[0][1] if manifests else None)
        # 新契约：训练特征从绑定仓库现算；上传文件场景使用系统配置的仓库。
        metadata['repo'] = str(config.SOURCE_REPO) if config.SOURCE_REPO else ''
        inputs = [{'name': name, 'sha256': fc.sha256(content), 'rows': len(rows)}]
        inputs += [{'name': mn, 'sha256': fc.sha256(raw)} for mn, raw in manifests]
        byte_count = sum(len(raw) for _, raw in files)
    else:
        if manifests or dataset_id is None:
            fc.invalid('请上传训练主表或选择已导入数据集')
        rows, metadata, inputs, byte_count = _dataset_input(session, dataset_id)
    reference, digest = _save_request({'rows': rows, 'config': validated, 'metadata': metadata, 'inputs': inputs})
    total = len(validated['algos']) + 1
    try:
        job = job_store.create(session, 'train', params={'module': 'train', 'input_ref': reference,
            'input_sha256': digest, 'config': validated}, total=total)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    if len(rows) <= SYNC_MAX_ROWS and set(validated['algos']) <= SYNC_ALGOS:
        _execute(job['job_id'], job['retry_count'])
        dispatch()
        current = job_store.get(session, job['job_id'])
        ref = current['output_ref_json'] or {}
        return {'job_id': current['job_id'], 'status': current['status'], 'outputs': ref.get('outputs', []),
                'models': ref.get('models', []), 'summary': ref.get('summary'), 'error_log': current['error_log']}
    dispatch()
    return {'job_id': job['job_id'], 'status': job['status']}


def _register_and_load(result, artifacts, validated):
    from app.services import storage
    for sub in result['models']:
        if sub['status'] != 'success':
            continue
        zip_name = f'train_{sub["algo"]}_model_package_{result["job_id"]}.zip'
        if validated.get('register'):
            try:
                with db.SessionLocal() as session:
                    storage.import_files(session, [(zip_name, artifacts[zip_name])])
                sub['register_status'] = 'registered'
            except Exception as error:
                sub['register_status'] = 'failed: ' + job_store.sanitize_text(str(error))
        if validated.get('auto_load'):
            try:
                from app import model_registry
                members = fc.read_zip(zip_name, artifacts[zip_name])
                model_registry.load_trained(sub['model_name'], members[f'{sub["algo"]}.pkl'])
                sub['load_status'] = 'loaded'
            except Exception as error:
                sub['load_status'] = 'failed: ' + job_store.sanitize_text(str(error))


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
            fc.invalid('训练输入快照超过大小限制')
        raw = path.read_bytes()
        if fc.sha256(raw) != params.get('input_sha256'):
            fc.invalid('训练输入 checksum 不一致')
        request = fc.read_json(raw)

        def progress(phase, done, total):
            with db.SessionLocal() as session:
                job_store.update_progress(session, job_id, attempt=attempt, total=max(total + 1, job['total']),
                                          done=max(done, job['done']), current_item=phase)

        result = _call('run', request['rows'], request['config'], metadata=request['metadata'], progress=progress)
        result['job_id'] = job_id
        artifacts = _call('artifacts', result, job_id)
        version = output_store.backend_code_version() + '+' + _call('code_version')
        with db.SessionLocal() as session:
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output('train', artifacts, inputs=request['inputs'],
                config=job_store.sanitize(result['config']), job_id=job_id, code_version=version)
            published = True
            reference.update(models=result['models'], summary=result['summary'],
                             comparison_name=f'train_comparison_{job_id}.json')
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
            finished = True
        # 登记/热加载只在 finish 成功后执行，失败任务不会留下在线模型或已登记工件。
        _register_and_load(result, artifacts, request['config'])
        reference['models'] = result['models']
        try:
            with db.SessionLocal() as session:
                job_store.update_output_ref(session, job_id, attempt=attempt, output_ref=reference)
        except AppError:
            logger.warning('train output annotation skipped job=%s', job_id)
        return True
    except Exception as error:
        if published and not finished:
            output_store.discard_output('train', job_id)
        with db.SessionLocal() as session:
            current = job_store.get(session, job_id)
        if current['status'] == 'running' and current['retry_count'] == attempt:
            try:
                with db.SessionLocal() as session:
                    job_store.fail(session, job_id, attempt=attempt, error=error)
            except AppError:
                pass
        if not isinstance(error, (AppError, ValueError)):
            logger.exception('train executor failed')
        return True


def compare(session, job_id):
    job = job_store.get(session, job_id)
    if job['kind'] != 'train' or job['status'] != 'success':
        raise AppError(40400, '训练比较仅对成功任务可用')
    name = (job['output_ref_json'] or {}).get('comparison_name')
    if not name:
        raise AppError(40400, '比较产物未登记')
    data = fc.read_json(output_store.read_output('train', job_id, name).read_bytes())
    metric = config_store.get_value('primary_metric', session)
    data['primary_metric'] = metric
    data['models'] = sorted(data.get('models', []),
        key=lambda m: ((m.get('metrics') or {}).get(metric) is None, -((m.get('metrics') or {}).get(metric) or 0)))
    return data


def _drain():
    while True:
        with db.SessionLocal() as session:
            job = session.scalar(select(Job).where(Job.kind == 'train', Job.status == 'queued',
                Job.params_json.contains('"module": "train"')).order_by(Job.created_at, Job.job_id).limit(1))
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
            logger.exception('train queue failed')


def dispatch():
    global _worker
    with _executor_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True, name='train-worker')
            _worker.start()
        _wakeup.set()


def dispatch_retry(data):
    if data['kind'] == 'train' and (data['params_json'] or {}).get('module') == 'train':
        dispatch()
