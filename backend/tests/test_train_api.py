"""AI-generated W5 orchestration tests; not human-reviewed."""
import importlib.util
import json
from types import SimpleNamespace

import pytest
from app import db
from app.errors import AppError
from app.models import Commit, Dataset, Model, ModelArtifact
from app.services import file_contracts as fc
from app.services import output_store
from sqlalchemy import func, select

from tests.conftest import HEADERS
from tests.test_clean_api import source_rows


def settings(**extra):
    return {'line': 'expert', 'feature_set': 'kamei14', 'algos': ['lr'], 'split': {'ratio': 0.7}, **extra}


def post(client, config=None, files=None):
    return client.post('/api/train/run', data={'config': json.dumps(config if config is not None else settings())},
        files=files if files is not None else [('files[]', ('collected_commits.csv', fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, source_rows(), 'csv')))], headers=HEADERS)


@pytest.fixture
def train_client(client, tmp_path, monkeypatch):
    module = None
    fake = SimpleNamespace()
    reg = SimpleNamespace()
    if importlib.util.find_spec('app.services.train_run'):
        from app.services import train_run as module
        monkeypatch.setattr(module, 'REQUEST_ROOT', tmp_path / 'inputs')
        monkeypatch.setattr(module, 'dispatch', lambda: None)
        monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')

        def validate(raw):
            allowed = {'line', 'feature_set', 'algos', 'hyperparams', 'split', 'seed',
                       'decision_threshold', 'register', 'auto_load'}
            if set(raw) - allowed or raw.get('line') != 'expert' or raw.get('feature_set') not in (None, 'kamei14') or not raw.get('algos'):
                raise AppError(40001, 'invalid train config')
            return {'seed': 42, 'decision_threshold': 0.5, 'register': False, 'auto_load': False, 'split': {'ratio': 0.7}, **raw}

        def run(rows, config, **kwargs):
            kwargs['progress']('lr', 1, 1)
            sub = {'algo': 'lr', 'model_name': 'lr_deadbeef_v1', 'version_key': 'deadbeefdeadbeef', 'feature_version': 'v1',
                   'status': 'success', 'metrics': {'auc': 0.9, 'f1': 0.8, 'precision': 0.8, 'recall': 0.8, 'accuracy': 0.8},
                   'warnings': [], 'error': None, 'elapsed_ms': 1.0, 'hyperparams': {}}
            return {'config': {**config, 'feature_version': 'v1', 'input_sha': 'a' * 64},
                    'summary': {'input_rows': len(rows), 'labeled_rows': 3, 'unlabeled_rows': 1, 'train_rows': 2, 'test_rows': 1,
                                'success_count': 1, 'failed_count': 0, 'warnings': []},
                    'models': [sub], 'metrics_rows': [],
                    'testset_rows': [{key: ('1' if key == 'is_bug_inducing' else '') for key in fc.CLEAN_DATASET_COLUMNS}],
                    'comparison': {'line': 'expert', 'models': [sub]}}

        def artifacts(result, job_id):
            return {f'train_lr_model_package_{job_id}.zip': b'PK\x03\x04mock', f'train_metrics_{job_id}.csv': b'metric\n',
                    f'train_comparison_{job_id}.json': json.dumps(result['comparison']).encode(),
                    f'train_roc_{job_id}.png': b'\x89PNG\r\n\x1a\n', f'train_log_{job_id}.md': b'# log\n'}

        fake = SimpleNamespace(TrainError=type('TrainError', (ValueError,), {'code': 40001}), validate_config=validate,
                               run=run, artifacts=artifacts, code_version=lambda: 'train-test')
        reg = SimpleNamespace(algorithms=lambda line=None, enabled_only=False: [
            {'line': 'expert', 'algo': 'lr', 'family': '经典机器学习', 'enabled': True, 'description': 'lr',
             'hyperparams_schema': [], 'input_requirements': 'Kamei14'}],
            validate_selection=lambda line, algos, hp: {'line': line, 'algos': algos, 'hyperparams': hp or {}})
        monkeypatch.setattr(module, '_core', lambda: fake)
        monkeypatch.setattr(module, '_registry', lambda: reg)
    return client, module, fake, reg, tmp_path


def test_train_routes_wired(client):
    paths = client.app.openapi()['paths']
    assert {'/api/algorithms', '/api/train/run', '/api/train/compare', '/api/train/outputs/{job_id}/{name}'} <= paths.keys()


def test_algorithms_endpoint_and_param_validation(train_client):
    client, _, _, _, _ = train_client
    data = client.get('/api/algorithms', headers=HEADERS).json()['data']
    assert any(a['algo'] == 'lr' for a in data['algorithms'])
    assert client.get('/api/algorithms?line=bogus', headers=HEADERS).status_code == 400
    assert client.get('/api/algorithms?enabled_only=2', headers=HEADERS).status_code == 400
    assert client.get('/api/algorithms').status_code == 401


def test_small_sync_run_delivers_package_without_business_mutation(train_client):
    client, _, _, _, _ = train_client
    with db.SessionLocal() as session:
        before = [session.scalar(select(func.count()).select_from(t)) for t in (Commit, Dataset, Model, ModelArtifact)]
    response = post(client)
    assert response.status_code == 200, response.text
    result = response.json()['data']
    assert result['status'] == 'success' and result['models'][0]['status'] == 'success'
    job_id = result['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert job['kind'] == 'train' and job['status'] == 'success'
    names = [e['name'] for e in job['output_ref_json']['outputs']]
    assert any(n.endswith('.zip') for n in names) and any(n.endswith('.png') for n in names)
    for entry in job['output_ref_json']['outputs']:
        url = f'/api/train/outputs/{job_id}/{entry["name"]}'
        assert client.get(url).status_code == 401
        download = client.get(url, headers=HEADERS)
        assert download.status_code == 200 and fc.sha256(download.content) == entry['sha256']
    with db.SessionLocal() as session:
        assert before == [session.scalar(select(func.count()).select_from(t)) for t in (Commit, Dataset, Model, ModelArtifact)]


def test_compare_sorts_by_primary_metric(train_client):
    client, _, _, _, _ = train_client
    response = post(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    compare = client.get('/api/train/compare', params={'job_id': job_id}, headers=HEADERS).json()['data']
    assert compare['models'][0]['algo'] == 'lr' and 'primary_metric' in compare
    assert client.get('/api/train/compare', params={'job_id': 'missing'}, headers=HEADERS).status_code == 404


def test_large_queued_then_executes(train_client, monkeypatch):
    client, module, _, _, _ = train_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200 and response.json()['data']['status'] == 'queued'
    job_id = response.json()['data']['job_id']
    assert module._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'


@pytest.mark.parametrize('config', [settings(line='semantic'), settings(algos=[]), settings() | {'unknown': 1}, settings() | {'dataset_id': 'missing'}])
def test_invalid_config_or_dataset_no_job(train_client, config):
    client, _, _, _, _ = train_client
    files = [] if 'dataset_id' in config else None
    response = post(client, config=config, files=files)
    assert response.status_code in (400, 404)
    assert client.get('/api/jobs?kind=train', headers=HEADERS).json()['data']['total'] == 0


def test_bad_file_rejected_before_job(train_client):
    client, _, _, _, _ = train_client
    response = post(client, files=[('files[]', ('bad.csv', b'wrong\nx\n'))])
    assert response.status_code == 400
    assert client.get('/api/jobs?kind=train', headers=HEADERS).json()['data']['total'] == 0


def test_retry_and_cancel_attempt_safe(train_client, monkeypatch):
    client, module, fake, _, path = train_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.run
    fake.run = lambda *a, **k: (_ for _ in ()).throw(AppError(40001, 'password:secret boom'))
    module._execute(job_id, 0)
    failed = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert failed['status'] == 'failed' and 'secret' not in failed['error_log']
    dispatched = []
    monkeypatch.setattr(module, 'dispatch', lambda: dispatched.append(True))
    assert client.post('/api/jobs/' + job_id + '/retry', headers=HEADERS).json()['data']['retry_count'] == 1
    assert dispatched == [True]
    fake.run = original
    assert module._execute(job_id, 1)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'
    second = post(client).json()['data']['job_id']
    def cancel(*a, **k):
        client.post('/api/jobs/' + second + '/cancel', headers=HEADERS)
        return original(*a, **k)
    fake.run = cancel
    module._execute(second, 0)
    assert client.get('/api/jobs/' + second, headers=HEADERS).json()['data']['status'] == 'cancelled'
    assert not (path / 'outputs' / second).exists()


def test_train_templates_persist_and_snapshot_frozen(train_client):
    client, _, _, _, _ = train_client
    template = {'line': 'expert', 'algos': ['lr'], 'split': {'ratio': 0.8}, 'seed': 7}
    assert client.put('/api/config/train.templates', json={'value': {'AI tpl': template}}, headers=HEADERS).status_code == 200
    response = post(client, config={'template_name': 'AI tpl'})
    assert response.status_code == 200 and response.json()['data']['status'] == 'success'
    job = client.get('/api/jobs/' + response.json()['data']['job_id'], headers=HEADERS).json()['data']
    assert job['params_json']['config']['seed'] == 7
    assert client.put('/api/config/train.templates', json={'value': {'AI tpl': {**template, 'seed': 9}}}, headers=HEADERS).status_code == 200
    assert client.get('/api/jobs/' + job['job_id'], headers=HEADERS).json()['data']['params_json']['config']['seed'] == 7
    assert client.put('/api/config/train.templates', json={'value': {'bad': {'line': 'expert', 'algos': []}}}, headers=HEADERS).status_code == 400


def test_compare_handles_failed_submodel(train_client, monkeypatch):
    client, module, fake, _, _ = train_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    original = fake.run
    def mixed(rows, config, **kwargs):
        result = original(rows, config, **kwargs)
        result['models'].append({'algo': 'rf', 'model_name': 'rf_x_v1', 'version_key': 'x', 'feature_version': 'v1',
                                 'status': 'failed', 'metrics': None, 'error': 'boom', 'hyperparams': {}})
        result['comparison']['models'] = result['models']
        result['summary']['failed_count'] = 1
        return result
    fake.run = mixed
    response = post(client, settings(algos=['lr', 'rf']))
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    assert module._execute(job_id, 0)
    compare = client.get('/api/train/compare', params={'job_id': job_id}, headers=HEADERS)
    assert compare.status_code == 200, compare.text
    models = compare.json()['data']['models']
    assert models[0]['algo'] == 'lr' and models[-1]['status'] == 'failed'


def test_template_rejects_unknown_key(train_client):
    client, _, _, _, _ = train_client
    unknown = {'line': 'expert', 'algos': ['lr'], 'wat': 1}
    assert client.put('/api/config/train.templates', json={'value': {'bad': unknown}}, headers=HEADERS).status_code == 400


def test_train_body_guard(train_client, monkeypatch):
    client, _, _, _, _ = train_client
    from app import main
    monkeypatch.setattr(main, 'MAX_IMPORT_BODY_BYTES', 16)
    response = post(client)
    assert response.status_code == 400 and '总大小' in response.json()['message']
