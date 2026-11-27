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
from sqlalchemy.dialects.mysql import insert as mysql_insert

from app import config, db, model_registry
from app.errors import AppError
from app.models import Commit, Job, Model, ModelArtifact, Prediction
from app.services import config_store, job_store, model_manage, output_store
from app.services import file_contracts as fc

logger = logging.getLogger('backend.predict_batch')
REQUEST_ROOT = config.TEMP_ROOT / 'predict_inputs'
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
        # 上传模型包即登记 Model/ModelArtifact，保证 save_to_db 默认 true 时预测结果可落库。
        storage.import_model(session, raw, meta, {}, [], extension='zip')
        session.flush()
        model_registry.load_artifact_package(meta['model_name'], raw, line=meta['line'])
        return meta['model_name'], meta['line'], meta.get('feature_version'), meta.get('version_key')
    model_name = settings.get('model_name')
    if not model_name:
        raise AppError(40001, '参数非法：必须上传模型包或显式指定 model_name，不设默认模型')
    model_row = session.get(Model, model_name)
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
    if not members:
        fc.invalid('所选数据集没有提交成员')
    records = [storage.member_record(member) for member in members]
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, records, 'csv')
    rows, metadata = _parse_table('dataset_commits.csv', content)
    return rows, metadata, [{'name': 'dataset_commits.csv', 'sha256': fc.sha256(content), 'rows': len(rows)}]


def _testset_input(session, testset_ref):
    """Web 页面的测试集只能来自训练成功任务产出的 train_testset。"""
    job = job_store.get(session, testset_ref)
    if job['kind'] != 'train' or job['status'] != 'success':
        raise AppError(40400, '测试集所属训练任务不存在或未成功')
    reference = job['output_ref_json'] or {}
    names = [item.get('name') for item in reference.get('outputs', []) if isinstance(item.get('name'), str)]
    name = next((item for item in names if item.startswith('train_testset_') and item.endswith('.csv')), None)
    if name is None:
        raise AppError(40400, '测试集产物未登记')
    content = output_store.read_output('train', testset_ref, name).read_bytes()
    manifest_name = next((item for item in names if name.endswith('.manifest.json')), None)
    manifest = (output_store.read_output('train', testset_ref, manifest_name).read_bytes()
                if manifest_name else None)
    rows, metadata = _parse_table(name, content, manifest)
    inputs = [{'name': name, 'sha256': fc.sha256(content), 'rows': len(rows)}]
    if manifest_name:
        inputs.append({'name': manifest_name, 'sha256': fc.sha256(manifest)})
    return rows, metadata, inputs


def _output_base(output_name, job_id):
    base = output_name or f'predict_predictions_{job_id}'
    if not isinstance(base, str) or not base.strip() or len(base) > 64 or base.startswith('.') \
            or any(char in base for char in '/\\:*?"<>|') or any(ord(char) < 32 for char in base):
        fc.invalid('output_name 非法')
    base = base.strip()
    if base.lower().endswith(('.csv', '.xlsx')):
        base = base.rsplit('.', 1)[0]
    return base


def submit(session, raw_config, files):
    settings = fc.read_json(raw_config.encode('utf-8'))
    allowed = {'dataset_id', 'model_name', 'decision_threshold', 'batch_size', 'force_recompute',
               'testset_ref', 'output_name', 'save_to_db'}
    if set(settings) - allowed:
        fc.invalid('预测配置含未知字段')
    dataset_id = settings.pop('dataset_id', None)
    testset_ref = settings.pop('testset_ref', None)
    if testset_ref is not None and (not isinstance(testset_ref, str) or not testset_ref):
        fc.invalid('testset_ref 非法')
    output_name = settings.pop('output_name', None)
    if output_name is not None:
        _output_base(output_name, '')
    save_to_db = settings.pop('save_to_db', True)
    if type(save_to_db) is not bool:
        fc.invalid('save_to_db 必须为布尔')
    if dataset_id is not None and testset_ref is not None:
        fc.invalid('dataset_id 与 testset_ref 只能二选一')
    threshold = settings.get('decision_threshold', config_store.get_value('decision_threshold', session))
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 < threshold < 1:
        fc.invalid('decision_threshold 必须在开区间 (0,1)')
    batch_size = settings.get('batch_size', config_store.get_value('predict.batch_size', session))
    if type(batch_size) is not int or batch_size < 1:
        fc.invalid('batch_size 必须为正整数')
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
    if len(zips) > 1 or len(tables) > 1:
        fc.invalid('预测最多一个模型包与一个 collected_commits/clean_dataset 表')
    feature_name = feature_content = None
    for name, content in tables:
        columns, _ = fc.read_table(name, content)
        if tuple(columns) in (tuple(fc.COLLECTED_COMMITS_COLUMNS), tuple(fc.CLEAN_DATASET_COLUMNS)):
            if feature_name is not None:
                fc.invalid('只能上传一个输入表')
            feature_name, feature_content = name, content
        else:
            fc.invalid('预测表格须为 collected_commits / clean_dataset 契约表')
    if manifests and (feature_name is None or len(manifests) > 1 or manifests[0][0] != feature_name.rsplit('.', 1)[0] + '.manifest.json'):
        fc.invalid('manifest 必须与特征文件同名且唯一')
    if feature_content is not None:
        rows, metadata = _parse_table(feature_name, feature_content, manifests[0][1] if manifests else None)
        inputs = [{'name': feature_name, 'sha256': fc.sha256(feature_content), 'rows': len(rows)}]
        inputs += [{'name': mn, 'sha256': fc.sha256(raw)} for mn, raw in manifests]
    elif testset_ref is not None and not manifests:
        rows, metadata, inputs = _testset_input(session, testset_ref)
    elif dataset_id is not None and not manifests:
        rows, metadata, inputs = _dataset_input(session, dataset_id)
    else:
        rows, metadata, inputs = [], {}, []
    model_name, line, feature_version, model_version = _resolve_model(session, settings, zips)
    if line == 'expert':
        if not rows:
            fc.invalid('预测输入为空')
    elif line == 'semantic':
        if not rows:
            fc.invalid('semantic 线需要特征表提供提交哈希（语义向量按哈希取预计算或在线编码）')
    if zips:
        inputs.append({'name': zips[0][0], 'sha256': fc.sha256(zips[0][1])})
    feature_version = feature_version or metadata.get('feature_version')
    config_snapshot = {'model_name': model_name, 'line': line, 'decision_threshold': threshold,
                       'batch_size': batch_size, 'force_recompute': force,
                       'testset_ref': testset_ref, 'output_name': output_name, 'save_to_db': save_to_db,
                       'feature_version': feature_version, 'model_version': model_version or model_name,
                       'external': bool(metadata.get('external'))}
    reference, digest = _save_request({'rows': rows, 'config': config_snapshot, 'inputs': inputs})
    artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == model_name))
    parent_ids = [testset_ref] if testset_ref else []
    if artifact and artifact.train_job_id and artifact.train_job_id not in parent_ids:
        parent_ids.append(artifact.train_job_id)
    parents = [{'kind': 'train', 'job_id': item} for item in parent_ids] or None
    try:
        job = job_store.create(session, 'predict_batch', params={'module': 'predict', 'input_ref': reference,
            'input_sha256': digest, 'config': config_snapshot}, total=len(rows) + 1, parents=parents)
    except Exception:
        shutil.rmtree(_request_path(reference).parent)
        raise
    if len(rows) <= SYNC_MAX_ROWS:
        session.commit()
        _execute(job['job_id'], job['retry_count'])
        dispatch()
        current = job_store.get(session, job['job_id'])
        ref = current['output_ref_json'] or {}
        return {'job_id': current['job_id'], 'status': current['status'], 'outputs': ref.get('outputs', []),
                'summary': ref.get('summary'), 'error_log': current['error_log']}
    dispatch()
    return {'job_id': job['job_id'], 'status': job['status']}


def _predict_rows(rows, cfg, progress, job_id, attempt, total):
    line = cfg.get('line', 'expert')
    entry = model_registry.get_model(cfg['model_name'])
    threshold = cfg['decision_threshold']
    predicted_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    out, failed = [], []
    external = bool(cfg.get('external')) or (bool(rows) and not all(field in rows[0] for field in config.FEATURE_COLUMNS))
    computed = {}
    if external and line == 'expert':
        from app import feature_source
        try:
            computed = {item['commit_hash']: item for item in
                        feature_source.extract_many([row['commit_hash'] for row in rows])}
        except Exception as error:
            raise AppError(40001, f'特征现算失败：{error}') from error
    for index, row in enumerate(rows):
        if progress:
            # 已完成条数从 1 开始计数，进度条与清洗/训练页同一口径
            progress(row['commit_hash'], index + 1, total)
        try:
            commit_hash = row['commit_hash']
            if line == 'expert':
                if external and commit_hash in computed:
                    vector = feature_source.vector_from(computed[commit_hash])
                else:
                    vector = [float(row[field]) for field in config.FEATURE_COLUMNS]
            else:
                from app import semantic_source
                embedding = semantic_source.embedding_for(commit_hash)
                if embedding is None:
                    raise ValueError(f'{line} 语义向量不可用（缺预计算且无法在线编码）')
                vector = embedding.tolist()
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

        out, failed, _ = _predict_rows(request['rows'], cfg, progress, job_id, attempt, len(request['rows']))
        # 收尾一步与清洗/收集页一致：进度条走到 100% 再发布产物
        progress('publish', job['total'], job['total'] - 1)
        summary = {'input_rows': len(request['rows']), 'success_count': len(out), 'failed_count': len(failed),
                   'model_name': cfg['model_name'], 'model_version': cfg['model_version'],
                   'feature_version': cfg['feature_version'], 'decision_threshold': cfg['decision_threshold'],
                   'testset_ref': cfg.get('testset_ref'), 'failed_samples': failed[:100]}
        base = _output_base(cfg.get('output_name'), job_id)
        # 预测结果只交付一张结果表，不再生成额外的说明文件。
        artifacts = {f'{base}.csv': fc.encode_table(fc.PREDICTIONS_COLUMNS, out, 'csv')}
        saved_rows = 0
        with db.SessionLocal() as session:
            job_store.assert_running(session, job_id, attempt=attempt)
            reference = output_store.publish_output('predict', artifacts, inputs=request['inputs'],
                config=job_store.sanitize(cfg), job_id=job_id, code_version=output_store.backend_code_version())
            published = True
            if cfg.get('save_to_db', True):
                if session.get(Model, cfg['model_name']) is None:
                    raise AppError(40001, '模型未登记，无法保存预测结果')
                hashes = {row['commit_hash'] for row in out}
                known = set()
                for start in range(0, len(hashes), 1000):
                    chunk = list(hashes)[start:start + 1000]
                    known.update(session.scalars(
                        select(Commit.commit_hash).where(Commit.commit_hash.in_(chunk))
                    ).all())
                records = [{
                    'job_id': job_id,
                    'commit_hash': row['commit_hash'],
                    'model_name': row['model_name'],
                    'risk_score': row['risk_score'],
                    'predicted_label': row['predicted_label'],
                    'decision_threshold': row['decision_threshold'],
                    'model_version': row['model_version'],
                    'feature_version': row['feature_version'],
                    'output_name': cfg.get('output_name'),
                    'predicted_at': datetime.fromisoformat(row['predicted_at'].replace('Z', '+00:00')).astimezone(UTC).replace(tzinfo=None),
                    'is_bug_inducing': None if row['is_bug_inducing'] in ('', None) else int(row['is_bug_inducing']),
                } for row in out if row['commit_hash'] in known]
                for start in range(0, len(records), 1000):
                    statement = mysql_insert(Prediction).values(records[start:start + 1000])
                    session.execute(statement.on_duplicate_key_update(
                        job_id=statement.inserted.job_id,
                        risk_score=statement.inserted.risk_score,
                        predicted_label=statement.inserted.predicted_label,
                        decision_threshold=statement.inserted.decision_threshold,
                        model_version=statement.inserted.model_version,
                        feature_version=statement.inserted.feature_version,
                        output_name=statement.inserted.output_name,
                        predicted_at=statement.inserted.predicted_at,
                        is_bug_inducing=statement.inserted.is_bug_inducing,
                    ))
                saved_rows = len(records)
            summary['saved_rows'] = saved_rows
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
