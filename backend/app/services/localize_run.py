from __future__ import annotations

import json
import math
from uuid import uuid4

from app import localization_core
from app.errors import AppError
from app.models import Dataset
from app.services import config_store, job_store, output_store, storage
from app.services import file_contracts as fc

COLUMNS = ('commit_hash', 'file_path', 'line_number', 'suspicion', 'rank', 'evidence_json', 'level')
EXPLANATION_COLUMNS = ('commit_hash', 'model_name', 'technique', 'feature', 'raw_value', 'contribution',
                       'direction', 'rank', 'label', 'model_version', 'feature_version')
MAX_BATCH_ROWS = 20
MAX_RESULT_ROWS = 5000


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True).encode('utf-8')


def _policy(session):
    return {'allow_roots': config_store.get_value('collect.allow_roots', session),
            'protocol_whitelist': config_store.get_value('collect.protocol_whitelist', session)}


def _repo(session, repo_source=None, dataset_id=None):
    if repo_source:
        if not isinstance(repo_source, str):
            fc.invalid('repo_source 必须为字符串')
        return repo_source
    if not isinstance(dataset_id, str) or not dataset_id:
        fc.invalid('请指定 repo_source 或已登记 dataset_id')
    dataset = session.get(Dataset, dataset_id)
    if dataset is None:
        raise AppError(40400, '数据集不存在')
    return dataset.repo_source


def source(session, operation, *, repo_source=None, dataset_id=None, commit_hash, path='', search=None, start_line=1, end_line=None):
    repo = _repo(session, repo_source, dataset_id)
    with localization_core.SourceReader(repo, **_policy(session), file_size_max=config_store.get_value('localization.file_size_max', session)) as reader:
        if operation == 'tree':
            return reader.tree(commit_hash, path, search)
        return reader.file(commit_hash, path, start_line, end_line)


def _explanations(records):
    result, seen = [], set()
    for row in records:
        identity = (storage.hash40(row['commit_hash']), storage.text(row['model_name'], 'model_name', 64),
                    storage.text(row['model_version'], 'model_version', 64), storage.text(row['feature_version'], 'feature_version', 32))
        base = dict(zip(('commit_hash', 'model_name', 'model_version', 'feature_version'), identity, strict=True))
        reason = row.get('reason_code', '')
        if reason:
            if row.get('feature') or row.get('contribution'):
                fc.invalid('原因行的特征与贡献必须为空')
            result.append({**base, 'reason_code': storage.text(reason, 'reason_code', 128)})
            continue
        feature = storage.text(row['feature'], 'feature', 128)
        value = float(row['contribution'])
        raw_value = float(row['raw_value'])
        if not math.isfinite(value) or not math.isfinite(raw_value):
            fc.invalid('解释原值与贡献必须为有限数值')
        if row['direction'] != ('increase' if value > 0 else 'decrease' if value < 0 else 'neutral'):
            fc.invalid('解释方向与贡献符号不一致')
        try:
            rank = int(row['rank'])
            if rank < 1 or str(rank) != row['rank']:
                raise ValueError
        except (TypeError, ValueError):
            fc.invalid('解释 rank 必须为正整数')
        key = (*identity, row['technique'], feature)
        if key in seen:
            fc.invalid('解释存在重复提交/模型/技术/特征')
        seen.add(key)
        result.append({**base, 'feature': feature, 'raw_value': raw_value, 'contribution': value, 'technique': row['technique']})
    return result


def parse_files(files):
    if not files or len(files) > 4 or len({n for n, _ in files}) != len(files) or sum(len(b) for _, b in files) > fc.MAX_UPLOAD_BYTES:
        fc.invalid('请上传预测与可选解释；文件名不能重复，合计最多 64MiB/4文件')
    uploaded = dict(files)
    predictions, explanations, inputs = None, None, []
    for name, data in files:
        fc.validate_upload_name(name)
        inputs.append({'name': name, 'sha256': fc.sha256(data)})
        if name.endswith('.manifest.json'):
            bases = [n for n in uploaded if not n.endswith('.manifest.json') and n.rsplit('.', 1)[0] == name[:-len('.manifest.json')]]
            if len(bases) != 1:
                fc.invalid('manifest 必须对应一个同 stem 表格')
            fc.verify_manifest(bases[0], uploaded[bases[0]], data)
            continue
        columns, records = fc.read_table(name, data)
        if columns == list(fc.PREDICTIONS_COLUMNS):
            if predictions is not None:
                fc.invalid('只能上传一个预测主表')
            validated = storage.table_rows('predictions', records, None)
            predictions = [{**row, 'risk_score': float(row['risk_score'])} for row in validated]
        elif tuple(columns) in (EXPLANATION_COLUMNS, (*EXPLANATION_COLUMNS, 'reason_code')):
            if explanations is not None:
                fc.invalid('只能上传一个解释表')
            try:
                explanations = _explanations(records)
            except (ValueError, OverflowError, TypeError) as error:
                raise AppError(40001, '解释值类型非法') from error
        else:
            fc.invalid('定位只接受 §3.4 预测与 §3.7 解释表格')
    if not predictions:
        fc.invalid('定位必须提供非空预测文件')
    return predictions, explanations, inputs


def run_files(repo, files, raw_config, *, policy, llm=None):
    cfg = localization_core.validate_config(raw_config)
    predictions, explanations, inputs = parse_files(files)
    targets = [p for p in predictions if (not cfg['commit_hash'] or p['commit_hash'] == cfg['commit_hash'])
               and (not cfg['model_name'] or p['model_name'] == cfg['model_name'])]
    if not targets or len(targets) > MAX_BATCH_ROWS or len(targets) * cfg['top_n']['files'] * cfg['top_n']['lines'] > MAX_RESULT_ROWS:
        fc.invalid('定位单批最多 20 个预测目标/5000 个定位位置，请筛选、降低 Top-N 或分批')
    with localization_core.SourceReader(repo, **policy, file_size_max=cfg['file_size_max']) as reader:
        result = localization_core.localize(reader, predictions, cfg, explanations=explanations, llm=llm)
    result['summary']['line_rows'] = sum(row['level'] == 'line' for row in result['rows'])
    result['summary']['commit_rows'] = sum(row['level'] == 'commit' for row in result['rows'])
    return result, inputs


def publish(result, inputs, repo):
    job_id = str(uuid4())
    formats = [result['config']['format'], 'xlsx' if result['config']['format'] == 'csv' else 'csv']
    cells = [{k: '' if row[k] is None else row[k] for k in COLUMNS} for row in result['rows']]
    assets = {f'localization_localization_{job_id}.{fmt}': fc.encode_table(COLUMNS, cells, fmt) for fmt in formats}
    assets[f'localization_evidence_{job_id}.json'] = _json({'rows': result['rows'], 'evidence': result['evidence'], 'summary': result['summary']})
    assets[f'localization_suggestions_{job_id}.md'] = result['suggestions'].encode('utf-8')
    snapshot = {**result['config'], 'repo_source': repo, 'repo_fingerprint': fc.sha256(repo.encode()),
                'git_commits': list(result['evidence']), 'patch_reason': result['summary']['patch_reason']}
    reference = output_store.publish_output('localize', assets, inputs=inputs, config=job_store.sanitize(snapshot), job_id=job_id,
                                            code_version=output_store.backend_code_version())
    return {**reference, 'status': 'success', 'summary': result['summary'], 'localization': result['rows'][:20], 'suggestions': result['suggestions']}


def submit(session, raw_config, files):
    raw = fc.read_json(raw_config.encode())
    repo_source, dataset_id = raw.pop('repo_source', None), raw.pop('dataset_id', None)
    defaults = {'weights': config_store.get_value('localization.weights', session), 'top_n': config_store.get_value('localization.top_n', session),
                'file_size_max': config_store.get_value('localization.file_size_max', session),
                'suggestion_sources': config_store.get_value('localization.suggestion_sources', session)}
    defaults = localization_core.validate_config(defaults)
    localization_core.validate_config(raw)
    settings = {**defaults, **raw}
    settings['weights'] = localization_core._weights(raw.get('weights', {}), defaults['weights'])
    settings['top_n'] = {**defaults['top_n'], **raw.get('top_n', {})}
    repo = _repo(session, repo_source, dataset_id)
    from app.services.fix_suggestion import _llm_suggestions
    result, inputs = run_files(repo, files, settings, policy=_policy(session), llm=_llm_suggestions)
    return publish(result, inputs, repo)
