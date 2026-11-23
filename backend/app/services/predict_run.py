from __future__ import annotations

import importlib
import json
import logging
import re
import shutil
import sys
import threading
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app import config, db, model_registry
from app.errors import AppError
from app.models import Job, Model
from app.services import config_store, job_store, model_manage, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.predict_batch')
REQUEST_ROOT = config.REPO_ROOT / 'backend' / 'var' / 'predict_inputs'
SYNC_MAX_ROWS = 2000
_executor_lock = threading.Lock()
_wakeup = threading.Event()
_worker = None


def _parse_table(name, content, manifest=None):
    source = str(config.REPO_ROOT / 'data_model')
    if source not in sys.path:
        sys.path.insert(0, source)
    try:
        return importlib.import_module('preparation.clean').parse_input(name, content, manifest)
    except ValueError as error:
        raise AppError(40001, job_store.sanitize_text(str(error))) from error


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def _request_path(reference):
    if not isinstance(reference, str) or not re.fullmatch(r'[0-9a-f]{32}/request\.json', reference):
        fc.invalid('预测输入引用非法')
    directory = REQUEST_ROOT / reference.split('/')[0]
    path = directory / 'request.json'
    if REQUEST_ROOT.is_symlink() or directory.is_symlink() or path.is_symlink() or not path.is_file():
        raise AppError(40400, '预测输入已不可用，无法重试')
    return path


def _save_request(value):
    if REQUEST_ROOT.is_symlink():
        fc.invalid('预测输入目录非法')
    REQUEST_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = REQUEST_ROOT / uuid4().hex
    directory.mkdir(mode=0o700)
    content = _json(value)
    if len(content) > fc.MAX_UPLOAD_BYTES:
        directory.rmdir()
        fc.invalid('预测输入快照超过 64MiB 大小限制')
    try:
        with (directory / 'request.json').open('xb') as target:
            target.write(content)
    except Exception:
        shutil.rmtree(directory)
        raise
    return directory.name + '/request.json', fc.sha256(content)


def _resolve_model(session, settings, zips):
    from app.services import storage
    if zips:
        name, raw = zips[0]
        meta = storage.model_package(name, raw)
        if meta['line'] == 'e2e':
            fc.invalid('e2e 批量暂不支持上传模型包，请使用已登记 codebert_e2e 模型与文本输入')
        model_registry.load_artifact_package(meta['model_name'], raw, line=meta['line'])
        return meta['model_name'], meta['line'], meta.get('feature_version'), meta.get('version_key')
    model_name = settings.get('model_name')
    if not model_name:
        model_name, _ = model_manage.resolve_default(session)
    if not model_name:
        raise AppError(40001, '无可用模型：请上传模型包、指定 model_name 或配置默认模型')
    model_row = session.get(Model, model_name)
    if model_registry.line_of(model_name) == 'e2e':
        return model_name, 'e2e', (model_row.feature_version if model_row else None), (model_row.version_key if model_row else None)
    if not model_registry.has(model_name):
        model_manage.load(session, model_name)
    try:
        entry = model_registry.get_model(model_name)
    except (KeyError, model_registry.ModelUnavailable) as error:
        raise AppError(40001, f'模型不可用：{error}') from error
    return entry.name, entry.line, (model_row.feature_version if model_row else None), (model_row.version_key if model_row else None)


def _dataset_input(session, dataset_id):
    from app.services import storage
    if not isinstance(dataset_id, str) or not dataset_id:
        fc.invalid('dataset_id 非法')
    storage.snapshot(session)
    storage.require_dataset(session, dataset_id)
    members, _ = storage.bounded_rows(session, storage.member_query(dataset_id))
    if not members or any(feature is None for _, feature in members):
        fc.invalid('所选数据集没有完整提交特征')
    records = [dict.fromkeys(fc.COMMITS_COLUMNS, '') | storage.member_record(commit, feature) for commit, feature in members]
    content = fc.encode_table(fc.COMMITS_COLUMNS, records, 'csv')
    rows, metadata = _parse_table('dataset_commits.csv', content)
    return rows, metadata, [{'name': 'dataset_commits.csv', 'sha256': fc.sha256(content), 'rows': len(rows)}]


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    allowed = {'dataset_id', 'model_name', 'decision_threshold', 'batch_size', 'force_recompute', 'format'}
    if set(settings) - allowed:
        fc.invalid('预测配置含未知字段')
    dataset_id = settings.pop('dataset_id', None)
    threshold = settings.get('decision_threshold', config_store.get_value('decision_threshold', session))
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 < threshold < 1:
        fc.invalid('decision_threshold 必须在开区间 (0,1)')
    batch_size = settings.get('batch_size', config_store.get_value('predict.batch_size', session))
    if type(batch_size) is not int or batch_size < 1:
        fc.invalid('batch_size 必须为正整数')
    fmt = settings.get('format', 'csv')
    if fmt not in ('csv', 'xlsx'):
        fc.invalid('format 只支持 csv/xlsx')
    force = settings.get('force_recompute', True)
    if type(force) is not bool:
        fc.invalid('force_recompute 必须为布尔')
    zips, tables, manifests = [], [], []
    if sum(len(c) for _, c in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('预测上传合计不超过 64MiB')
    for name, content in files:
        fc.validate_upload_name(name)
        if name.endswith('.zip'):
            zips.append((name, content))
        elif name.endswith('.manifest.json'):
            manifests.append((name, content))
        elif name.rsplit('.', 1)[-1].lower() in ('csv', 'xlsx'):
            tables.append((name, content))
        else:
            fc.invalid('预测文件格式非法')
    if len(zips) > 1 or len(tables) > 2:
        fc.invalid('预测最多一个模型包、一个特征表与一个可选文本表')
    feature_name = feature_content = text_name = None
    text_rows = None
    for name, content in tables:
        columns, _ = fc.read_table(name, content)
        if columns == list(fc.COMMITS_COLUMNS):
            if feature_name is not None:
                fc.invalid('只能上传一个特征表')
            feature_name, feature_content = name, content
        elif columns == ['commit_hash', 'text']:
            if text_rows is not None:
                fc.invalid('只能上传一个 commit_hash,text 文本表')
            text_name = name
            _, raw_text = fc.read_table(name, content)
            text_rows = {row['commit_hash']: row['text'] for row in raw_text}
        else:
            fc.invalid('预测表格须为 §3.1/§3.2 特征表或 commit_hash,text 文本表')
    if manifests and (feature_name is None or len(manifests) > 1 or manifests[0][0] != feature_name.rsplit('.', 1)[0] + '.manifest.json'):
        fc.invalid('manifest 必须与特征文件同名且唯一')
    if feature_content is not None:
        rows, metadata = _parse_table(feature_name, feature_content, manifests[0][1] if manifests else None)
        inputs = [{'name': feature_name, 'sha256': fc.sha256(feature_content), 'rows': len(rows)}]
        inputs += [{'name': mn, 'sha256': fc.sha256(raw)} for mn, raw in manifests]
    elif dataset_id is not None and not manifests:
        rows, metadata, inputs = _dataset_input(session, dataset_id)
    else:
        rows, metadata, inputs = [], {}, []
    if text_name is not None:
        inputs.append({'name': text_name, 'sha256': fc.sha256(dict(tables)[text_name])})
    model_name, line, feature_version, model_version = _resolve_model(session, settings, zips)
    if line == 'e2e' and zips:
        fc.invalid('e2e 批量暂不支持上传模型包，请使用已登记 codebert_e2e 模型与文本输入')
    if line == 'expert':
        if text_rows is not None:
            fc.invalid('expert 线不接受文本表')
        if not rows:
            fc.invalid('预测输入为空')
    elif line in ('semantic', 'fused'):
        if not rows:
            fc.invalid(f'{line} 线需要特征表提供提交哈希与 Kamei 特征（语义向量按哈希取预计算或在线编码）')
    elif line == 'e2e':
        if not rows and not text_rows:
            fc.invalid('e2e 线需要特征表或 commit_hash,text 文本表')
        if not rows:
            rows = [{'commit_hash': commit_hash, 'is_bug_inducing': None} for commit_hash in text_rows]
    if zips:
        inputs.append({'name': zips[0][0], 'sha256': fc.sha256(zips[0][1])})
    feature_version = feature_version or metadata.get('feature_version')
    config_snapshot = {'model_name': model_name, 'line': line, 'decision_threshold': threshold,
                       'batch_size': batch_size, 'force_recompute': force, 'format': fmt,
                       'feature_version': feature_version, 'model_version': model_version or model_name}
    reference, digest = _save_request({'rows': rows, 'text': text_rows, 'config': config_snapshot, 'inputs': inputs})
    try:
        job = job_store.create(session, 'predict_batch', params={'module': 'predict', 'input_ref': reference,
            'input_sha256': digest, 'config': config_snapshot}, total=len(rows) + 1)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    if len(rows) <= SYNC_MAX_ROWS:
        _execute(job['job_id'], job['retry_count'])
        dispatch()
        current = job_store.get(session, job['job_id'])
        ref = current['output_ref_json'] or {}
        return {'job_id': current['job_id'], 'status': current['status'], 'outputs': ref.get('outputs', []),
                'summary': ref.get('summary'), 'error_log': current['error_log']}
    dispatch()
    return {'job_id': job['job_id'], 'status': job['status']}


def _predict_rows(rows, cfg, progress, job_id, attempt, total, text_map=None):
    line = cfg.get('line', 'expert')
    text_map = text_map or {}
    entry = None if line == 'e2e' else model_registry.get_model(cfg['model_name'])
    threshold = cfg['decision_threshold']
    predicted_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    out, failed = [], []
    for index, row in enumerate(rows):
        if progress:
            progress(row['commit_hash'], index, total)
        try:
            commit_hash = row['commit_hash']
            if line == 'e2e':
                from app import e2e_source
                text = text_map.get(commit_hash)
                raw_risk = e2e_source.predict_proba_text(text) if text is not None else e2e_source.predict_proba(commit_hash)
                if raw_risk is None:
                    raise ValueError('e2e 文本或编码器不可用，无法在线预测')
            else:
                expert = [float(row[field]) for field in config.FEATURE_COLUMNS]
                if line == 'expert':
                    vector = expert
                else:
                    from app import semantic_source
                    embedding = semantic_source.embedding_for(commit_hash)
                    if embedding is None and commit_hash in text_map:
                        embedding = semantic_source._encode_text(text_map[commit_hash])
                    if embedding is None:
                        raise ValueError(f'{line} 语义向量不可用（缺预计算且无法在线编码）')
                    embedding = embedding.tolist()
                    vector = embedding if line == 'semantic' else expert + embedding
                raw_risk = model_registry.predict_proba(entry.model, vector)
            risk = round(raw_risk, 5)
            label = row.get('is_bug_inducing')
            out.append({'commit_hash': commit_hash, 'model_name': cfg['model_name'], 'risk_score': risk,
                        'predicted_label': int(risk >= threshold), 'decision_threshold': threshold,
                        'model_version': cfg['model_version'], 'feature_version': cfg['feature_version'],
                        'predicted_at': predicted_at.isoformat() + 'Z',
                        'is_bug_inducing': '' if label is None else label})
        except Exception as error:
            failed.append({'commit_hash': row['commit_hash'], 'reason': job_store.sanitize_text(str(error))})
    return out, failed, predicted_at


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
            fc.invalid('预测输入快照超过大小限制')
        raw = path.read_bytes()
        if fc.sha256(raw) != params.get('input_sha256'):
            fc.invalid('预测输入 checksum 不一致')
        request = fc.read_json(raw)
        cfg = request['config']

        def progress(phase, done, total):
            with db.SessionLocal() as session:
                job_store.update_progress(session, job_id, attempt=attempt, total=max(total + 1, job['total']),
                                          done=max(done, job['done']), current_item=phase)

        out, failed, _ = _predict_rows(request['rows'], cfg, progress, job_id, attempt, job['total'], text_map=request.get('text'))
        summary = {'input_rows': len(request['rows']), 'success_count': len(out), 'failed_count': len(failed),
                   'model_name': cfg['model_name'], 'model_version': cfg['model_version'],
                   'feature_version': cfg['feature_version'], 'decision_threshold': cfg['decision_threshold'],
                   'failed_samples': failed[:100]}
        primary = cfg['format']
        artifacts = {f'predict_predictions_{job_id}.{primary}': fc.encode_table(fc.PREDICTIONS_COLUMNS, out, primary)}
        other = 'xlsx' if primary == 'csv' else 'csv'
        artifacts[f'predict_predictions_{job_id}.{other}'] = fc.encode_table(fc.PREDICTIONS_COLUMNS, out, other)
        artifacts[f'predict_summary_{job_id}.json'] = _json(summary)
        with db.SessionLocal() as session:
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output('predict', artifacts, inputs=request['inputs'],
                config=job_store.sanitize(cfg), job_id=job_id, code_version=output_store.backend_code_version())
            published = True
            reference.update(summary=summary)
            job_store.finish(session, job_id, attempt=attempt, output_ref=reference)
            finished = True
        return True
    except Exception as error:
        if published and not finished:
            output_store.discard_output('predict', job_id)
        with db.SessionLocal() as session:
            current = job_store.get(session, job_id)
        if current['status'] == 'running' and current['retry_count'] == attempt:
            try:
                with db.SessionLocal() as session:
                    job_store.fail(session, job_id, attempt=attempt, error=error)
            except AppError:
                pass
        if not isinstance(error, (AppError, ValueError)):
            logger.exception('predict executor failed')
        return True


def _drain():
    while True:
        with db.SessionLocal() as session:
            job = session.scalar(select(Job).where(Job.kind == 'predict_batch', Job.status == 'queued',
                Job.params_json.contains('"module": "predict"')).order_by(Job.created_at, Job.job_id).limit(1))
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
            logger.exception('predict queue failed')


def dispatch():
    global _worker
    with _executor_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, daemon=True, name='predict-worker')
            _worker.start()
        _wakeup.set()


def dispatch_retry(data):
    if data['kind'] == 'predict_batch' and (data['params_json'] or {}).get('module') == 'predict':
        dispatch()
