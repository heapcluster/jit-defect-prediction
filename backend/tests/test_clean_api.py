"""AI-generated W4 tests; not human-reviewed."""
import importlib.util
import json
from types import SimpleNamespace

import pytest
from app import db
from app.errors import AppError
from app.models import Commit, Dataset
from app.services import file_contracts as fc
from app.services import output_store
from sqlalchemy import func, select

from tests.conftest import HEADERS


def source_rows():
    rows = []
    for index in range(4):
        row = dict.fromkeys(fc.COMMITS_COLUMNS, '')
        row.update({feature: 0 for feature in fc.FEATURE_COLUMNS})
        row.update(commit_hash=f'{index + 1:040x}', repo_name='AI unreviewed', author_name='测试',
                   message='fixture', committed_at=f'2026-01-0{index + 1}T00:00:00Z',
                   is_bug_inducing='' if index == 3 else index % 2, is_test=int(index > 1))
        rows.append(row)
    return rows


def settings(mode='preview'):
    return {'mode': mode, 'steps': [{'op': 'feature_align'}, {'op': 'time_split'}], 'features': ['ns']}


def post(client, mode='preview', config=None, files=None):
    return client.post('/api/clean/run', data={'config': json.dumps(config if config is not None else settings(mode))},
        files=files if files is not None else [('files[]', ('commits.csv', fc.encode_table(fc.COMMITS_COLUMNS, source_rows(), 'csv')))], headers=HEADERS)


@pytest.fixture
def clean_client(client, tmp_path, monkeypatch):
    module = None
    fake = SimpleNamespace()
    if importlib.util.find_spec('app.services.clean_run'):
        from app.services import clean_run as module
        monkeypatch.setattr(module, 'REQUEST_ROOT', tmp_path / 'inputs')
        monkeypatch.setattr(module, 'dispatch', lambda: None)
        monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
        def validate(raw):
            if set(raw) - {'mode', 'steps', 'features', 'seed', 'split_ratio', 'format'} or raw.get('mode') not in ('preview', 'apply'):
                raise AppError(40001, 'invalid config')
            return {'seed': 42, 'format': 'csv', **raw}
        def parse(name, content, manifest=None):
            columns, rows = fc.read_table(name, content)
            if columns != list(fc.COMMITS_COLUMNS):
                raise AppError(40001, 'schema invalid')
            if manifest:
                fc.verify_manifest(name, content, manifest)
            return rows, {'feature_version': 'v1', 'feature_state': 'log_v1'}
        def run(rows, config, **kwargs):
            kwargs['progress']('feature_align', 1, 2)
            return {'rows': rows, 'config': {**config, 'feature_version': 'v1'},
                    'summary': {'input_rows': len(rows), 'output_rows': len(rows)}, 'steps_stats': [], 'feature_stats': {}}
        def artifacts(result, job_id):
            output = {f'clean_steps_stats_{job_id}.json': b'[]', f'clean_feature_stats_{job_id}.json': b'{}',
                      f'clean_feature_distribution_ns_{job_id}.png': b'\x89PNG\r\n\x1a\nfixture'}
            if result['config']['mode'] == 'apply':
                output = {f'clean_cleaned_{job_id}.{fmt}': fc.encode_table(fc.COMMITS_COLUMNS, result['rows'], fmt) for fmt in ('csv', 'xlsx')} | output
            return output
        fake = SimpleNamespace(validate_config=validate, parse_input=parse, run=run, artifacts=artifacts,
                               operations=lambda: [{'op': 'feature_align'}], code_version=lambda: 'clean-test')
        monkeypatch.setattr(module, '_core', lambda: fake)
    return client, module, fake, tmp_path


def test_clean_routes_are_wired(client):
    paths = client.app.openapi()['paths']
    assert {'/api/clean/run', '/api/clean/operations', '/api/clean/preview/{job_id}', '/api/clean/outputs/{job_id}/{name}'} <= paths.keys()


@pytest.mark.parametrize('mode', ['preview', 'apply'])
def test_small_run_terminal_outputs_no_business_mutation(clean_client, mode):
    client, _, _, _ = clean_client
    with db.SessionLocal() as session:
        before = [session.scalar(select(func.count()).select_from(table)) for table in (Commit, Dataset)]
    response = post(client, mode)
    assert response.status_code == 200
    result = response.json()['data']
    assert result['status'] == 'success' and result['mode'] == mode
    job_id = result['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert job['kind'] == 'clean' and job['status'] == 'success'
    outputs = job['output_ref_json']['outputs']
    assert any(item['name'].endswith('.png') for item in outputs)
    assert any(item['name'].endswith('.csv') for item in outputs) == (mode == 'apply')
    for item in outputs:
        url = f'/api/clean/outputs/{job_id}/{item["name"]}'
        assert client.get(url).status_code == 401
        download = client.get(url, headers=HEADERS)
        assert download.status_code == 200 and fc.sha256(download.content) == item['sha256']
    preview = client.get('/api/clean/preview/' + job_id, headers=HEADERS)
    assert preview.status_code == (200 if mode == 'apply' else 400)
    if mode == 'apply':
        assert preview.json()['data']['preview'][-1]['is_bug_inducing'] is None
    with db.SessionLocal() as session:
        assert before == [session.scalar(select(func.count()).select_from(table)) for table in (Commit, Dataset)]


def test_large_run_queued_then_executes_original_snapshot(clean_client, monkeypatch):
    client, module, _, _ = clean_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client, 'apply')
    assert response.status_code == 200 and response.json()['data']['status'] == 'queued'
    job_id = response.json()['data']['job_id']
    assert module._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'


@pytest.mark.parametrize('extra', [{'unknown': True}, {'mode': 'random'}, {'dataset_id': 'missing'}])
def test_invalid_config_or_dataset_no_job(clean_client, extra):
    client, _, _, _ = clean_client
    config = settings() | extra
    files = [] if 'dataset_id' in extra else None
    response = post(client, config=config, files=files)
    assert response.status_code in (400, 404)
    assert client.get('/api/jobs?kind=clean', headers=HEADERS).json()['data']['total'] == 0


def test_uploaded_file_overrides_missing_dataset(clean_client):
    client, _, _, _ = clean_client
    response = post(client, config=settings() | {'dataset_id': 'missing'})
    assert response.status_code == 200


@pytest.mark.parametrize('files', [[('files[]', ('bad.csv', b'bad\nwrong\n'))],
    [('files[]', ('bad.xlsx', b'not xlsx'))], [('files[]', ('../bad.csv', b'bad'))]])
def test_bad_file_rejected_before_job(clean_client, files):
    client, _, _, _ = clean_client
    response = post(client, files=files)
    assert response.status_code == 400
    assert client.get('/api/jobs?kind=clean', headers=HEADERS).json()['data']['total'] == 0


def test_failed_retry_dispatch_and_cancel_are_attempt_safe(clean_client, monkeypatch):
    client, module, fake, path = clean_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.run
    fake.run = lambda *args, **kwargs: (_ for _ in ()).throw(AppError(40001, 'password:secret failed'))
    module._execute(job_id, 0)
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert job['status'] == 'failed' and 'secret' not in job['error_log']
    dispatched = []
    monkeypatch.setattr(module, 'dispatch', lambda: dispatched.append(True))
    assert client.post('/api/jobs/' + job_id + '/retry', headers=HEADERS).json()['data']['retry_count'] == 1
    assert dispatched == [True]
    fake.run = original
    assert module._execute(job_id, 1)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'
    second = post(client).json()['data']['job_id']
    original = fake.run
    def cancel(*args, **kwargs):
        client.post('/api/jobs/' + second + '/cancel', headers=HEADERS)
        return original(*args, **kwargs)
    fake.run = cancel
    module._execute(second, 0)
    assert client.get('/api/jobs/' + second, headers=HEADERS).json()['data']['status'] == 'cancelled'
    assert not (path / 'outputs' / second).exists()


def test_dispatch_coalesces_worker_threads(clean_client, monkeypatch):
    _, module, _, _ = clean_client
    assert module is not None
    monkeypatch.undo()
    created = []
    class Worker:
        def __init__(self, **kwargs):
            created.append(kwargs)
        def is_alive(self):
            return True
        def start(self):
            pass
    monkeypatch.setattr(module, '_worker', None, raising=False)
    monkeypatch.setattr(module, '_wakeup', module.threading.Event(), raising=False)
    monkeypatch.setattr(module.threading, 'Thread', Worker)
    for _ in range(10):
        module.dispatch()
    assert len(created) == 1


def test_synchronous_completion_restarts_queued_execution(clean_client, monkeypatch):
    client, module, _, _ = clean_client
    dispatches = []
    if module:
        monkeypatch.setattr(module, 'dispatch', lambda: dispatches.append(True))
    response = post(client)
    assert response.status_code == 200 and response.json()['data']['status'] == 'success'
    assert dispatches == [True]


def test_cancel_during_artifact_build_never_publishes(clean_client, monkeypatch):
    client, module, fake, _ = clean_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.artifacts
    published = []
    publisher = output_store.publish_output
    def build(result, identifier):
        client.post('/api/jobs/' + identifier + '/cancel', headers=HEADERS)
        return original(result, identifier)
    def publish(*args, **kwargs):
        published.append(True)
        return publisher(*args, **kwargs)
    fake.artifacts = build
    monkeypatch.setattr(output_store, 'publish_output', publish)
    module._execute(job_id, 0)
    assert not published
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'cancelled'


def test_clean_templates_persist_and_run_without_overwriting_snapshot(clean_client):
    client, _, _, _ = clean_client
    template = {'steps': [{'op': 'feature_align'}], 'features': ['ns'], 'seed': 7}
    saved = client.put('/api/config/clean.chain_templates', json={'value': {'AI template': template}}, headers=HEADERS)
    assert saved.status_code == 200
    response = post(client, config={'mode': 'preview', 'template': 'AI template'})
    assert response.status_code == 200 and response.json()['data']['status'] == 'success'
    job = client.get('/api/jobs/' + response.json()['data']['job_id'], headers=HEADERS).json()['data']
    assert job['params_json']['config']['seed'] == 7
    assert client.put('/api/config/clean.chain_templates', json={'value': {'AI template': template | {'seed': 8}}}, headers=HEADERS).status_code == 200
    assert client.get('/api/jobs/' + job['job_id'], headers=HEADERS).json()['data']['params_json']['config']['seed'] == 7


def test_clean_upload_body_guard_precedes_parser(clean_client, monkeypatch):
    client, _, _, _ = clean_client
    from app import main
    monkeypatch.setattr(main, 'MAX_IMPORT_BODY_BYTES', 16)
    response = post(client)
    assert response.status_code == 400 and '总大小' in response.json()['message']


def test_replay_tampering_fails_without_output(clean_client, monkeypatch):
    client, module, _, path = clean_client
    if module:
        monkeypatch.setattr(module, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    module._request_path(job['params_json']['input_ref']).write_bytes(b'{}')
    module._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'failed'
    assert not (path / 'outputs' / job_id).exists()
