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
from uuid import NAMESPACE_URL, uuid4, uuid5

from sqlalchemy import select

from app import config, db
from app.errors import AppError
from app.models import Dataset, DatasetCommit, Job
from app.services import config_store, job_store, output_store
from app.services import file_contracts as fc
from app.timeutil import now_naive_utc

logger = logging.getLogger('backend.collect')
REQUEST_ROOT = config.TEMP_ROOT / 'collect_inputs'
CACHE_ROOT = config.TEMP_ROOT / 'collect_cache'
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


def branches(session, repo_source):
    policy = _policy(session)
    return _call('list_branches', repo_source, allow_roots=policy['allow_roots'],
                 protocol_whitelist=policy['protocol_whitelist'])


def source_columns(session, source_url):
    return _call('source_columns', source_url,
                 protocol_whitelist=_policy(session)['protocol_whitelist'])


def _quality_report(result, settings):
    """Only project values already present in the collector result; never invent metrics."""
    summary = job_store.sanitize(result.get('summary') or {})
    audit = job_store.sanitize(result.get('audit') or {})
    total = summary.get('rows', summary.get('total_rows'))
    unlabeled = summary.get('unlabeled_rows')
    missing_rate = (unlabeled / total) if isinstance(total, int) and total > 0 and isinstance(unlabeled, int) else None
    checks = {
        'missing_rate': missing_rate,
        'duplicate_rows': audit.get('deduplicated'),
        'skipped_rows': audit.get('skipped'),
        'label_conflicts': None,
        'time_anomalies': None,
        'field_mapping': settings.get('field_mapping'),
        'anomaly_samples': None,
        'handling_note': '采集内核未上报的指标保持 null，不做推测。',
    }
    return {'summary': summary, 'audit': audit, 'checks': checks}


def _quality_cell(value):
    if value is None:
        return 'null'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).replace('|', '\\|')
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _quality_markdown(report):
    lines = ['# 采集质量报告', '', '> 仅由采集结果的 summary/audit 派生，未上报指标标记为 null。', '']
    for section in ('summary', 'audit', 'checks'):
        value = report.get(section) or {}
        lines.append(f'## {section}')
        lines.append('')
        lines.append('| 字段 | 值 |')
        lines.append('|---|---|')
        for key in sorted(value):
            lines.append(f'| {key} | {_quality_cell(value[key])} |')
        lines.append('')
    return ('\n'.join(lines)).encode('utf-8')


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
    policy = _policy(session)
    if settings.get('source_type') == 'public_dataset':
        if files or settings.get('dataset_id') is not None:
            fc.invalid('公开数据集模式不接受上传清单或 dataset_id')
        validated = _call('validate_public_config', settings,
                          protocol_whitelist=policy['protocol_whitelist'])
        reference, digest = _save_request({'config': validated, 'commit_hashes': None, 'inputs': []})
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
    validated = _call('validate_config', settings, **policy)
    available = _call('list_branches', validated['repo_source'], allow_roots=policy['allow_roots'],
                      protocol_whitelist=policy['protocol_whitelist'])
    if validated['branch'] not in available['branches']:
        fc.invalid('所选分支不存在，请刷新分支后重试')
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

        result = (
            _call('run_public', request['config'], protocol_whitelist=policy['protocol_whitelist'],
                  progress=progress)
            if request['config'].get('source_type') == 'public_dataset'
            else _call('run', request['config'], **policy, commit_hashes=request['commit_hashes'],
                       progress=progress, cache_dir=CACHE_ROOT)
        )
        progress('publish', 5, 5)
        settings = job_store.sanitize(result['config'])
        settings['source_fingerprint'] = fc.sha256(_json(request['config']))
        base = f'collected_commits_{job_id}'
        quality = _quality_report(result, settings)
        artifacts = {base + '.csv': _call('encode_rows', result['rows'], 'csv'),
                     f'collect_summary_{job_id}.json': _json(job_store.sanitize(result['summary'])),
                     f'collect_audit_{job_id}.json': _json(job_store.sanitize(result['audit'])),
                     f'collect_quality_{job_id}.json': _json(quality),
                     f'collect_quality_{job_id}.md': _quality_markdown(quality)}
        if result.get('metadata'):
            artifacts[f'collect_public_metadata_{job_id}.json'] = _json(
                job_store.sanitize(result['metadata']))
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


def resave(session, job_id):
    """Re-import an already published collected_commits artifact; never re-run collect/SZZ."""
    job = job_store.get(session, job_id)
    if job['kind'] != 'collect' or job['status'] != 'success':
        raise AppError(40400, '采集任务不存在或未成功')
    reference = job['output_ref_json'] or {}
    candidates = (f'collected_commits_{job_id}.csv', f'collected_commits_{job_id}.xlsx')
    entry = next((item for item in reference.get('outputs', []) if item.get('name') in candidates), None)
    if entry is None:
        raise AppError(40400, '采集产物未登记')
    name = entry['name']
    try:
        path = output_store.read_output('collect', job_id, name)
    except AppError as error:
        if error.code == 40400:
            raise AppError(40001, '输入产物 checksum 不一致') from error
        raise
    content = path.read_bytes()
    if fc.sha256(content) != entry.get('sha256'):
        raise AppError(40001, '输入产物 checksum 不一致')
    columns, rows = fc.read_table(name, content)
    if tuple(columns) != tuple(fc.COLLECTED_COMMITS_COLUMNS):
        fc.invalid('采集产物列与契约不一致')
    from app.services import storage

    validated = storage.table_rows('collected_commits', rows, None)
    for row in validated:
        if row.get('author_name') is None:
            row['author_name'] = ''
    settings = (job['params_json'] or {}).get('config') or {}
    # 任务参数会脱敏，重存数据集时优先读回原始请求快照，保住仓库路径与分支绑定。
    try:
        snapshot = json.loads(_request_path((job['params_json'] or {}).get('input_ref')).read_text('utf-8'))
        settings = snapshot.get('config') or settings
    except (OSError, ValueError):
        pass
    summary = reference.get('summary') or {}
    head = summary.get('head_hash')
    head_hash = head if isinstance(head, str) and re.fullmatch(r'[0-9a-f]{40}', head) else None
    source = settings.get('repo_source') or ''
    source_type = settings.get('source_type') or ('git_repo' if source else 'public_dataset')
    dataset_id = str(uuid5(NAMESPACE_URL, 'collect-resave:' + job_id))
    dataset = session.get(Dataset, dataset_id, with_for_update=True)
    if dataset is None:
        session.add(Dataset(
            dataset_id=dataset_id,
            name=str(settings.get('dataset_name') or f'collected_{job_id}')[:128],
            source_type=source_type,
            source_url=str(settings.get('source_url') or (source if '://' in source else ''))[:512] or None,
            repo_name=str(settings.get('dataset_name') or '')[:128],
            repo_source=source[:255],
            branch=settings.get('branch'),
            head_hash=head_hash,
            mode=settings.get('mode') or 'full',
            status='ready',
            job_id=job_id,
            created_at=now_naive_utc().replace(microsecond=0),
        ))
        session.flush()
    storage.import_table(session, 'collected_commits', validated, {'dataset_id': dataset_id}, None)
    session.commit()
    return {'job_id': job_id, 'dataset_id': dataset_id, 'status': 'success'}
