"""AI-generated W3 orchestration tests, not yet human-reviewed."""
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


@pytest.fixture
def collect_client(client, tmp_path, monkeypatch):
    with db.SessionLocal() as session:
        assert session.bind.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    module = None
    fake = SimpleNamespace()
    if importlib.util.find_spec('app.services.collect_run'):
        from app.services import collect_run as module
        monkeypatch.setattr(module, 'REQUEST_ROOT', tmp_path / 'inputs')
        monkeypatch.setattr(module, 'CACHE_ROOT', tmp_path / 'cache')
        monkeypatch.setattr(module, 'dispatch', lambda: None)
        monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')

        class CollectError(ValueError):
            def __init__(self, code, message):
                self.code, self.message = code, message

        def validate(settings, **policy):
            if set(settings) - {'repo_source', 'dataset_name', 'fetch_remote', 'format', 'branch'}:
                raise CollectError(40001, 'unknown configuration')
            return {'format': 'csv', 'fetch_remote': False, **settings}

        def run(settings, **kwargs):
            kwargs['progress']('features', 3, 5)
            row = {name: 0.0 for name in fc.FEATURE_COLUMNS}
            row.update(commit_hash='e' * 40, repo_name='AI fixture', author_name='测试作者',
                       author_email=None, committed_at='2026-01-01T00:00:00Z',
                       message='AI unreviewed', parent_hash=None, is_bug_inducing=None,
                       labeled_at=None, is_test=0, label_method='szz')
            return {'rows': [row], 'summary': {'rows': 1, 'head_hash': 'e' * 40,
                'labeled_rows': 0, 'positive_rows': 0, 'negative_rows': 0, 'unlabeled_rows': 1},
                'audit': {'deduplicated': 0}, 'config': {**settings, 'feature_version': 'v1'},
                'inputs': [{'name': 'repository_snapshot.json', 'sha256': 'a' * 64, 'rows': 1}]}
        fake = SimpleNamespace(CollectError=CollectError, validate_config=validate, run=run,
                               encode_rows=module._core().encode_rows)
        monkeypatch.setattr(module, '_core', lambda: fake)
    return client, module, fake, tmp_path


def submit(client, settings=None, files=None):
    return client.post('/api/collect/run', data={'config': json.dumps(settings or {
        'repo_source': '/allowed/fixture', 'dataset_name': 'AI unreviewed fixture',
        'fetch_remote': False})}, files=files, headers=HEADERS)


def test_collect_run_is_wired_on_real_app(client):
    assert '/api/collect/run' in client.app.openapi()['paths']
    assert '/api/collect/outputs/{job_id}/{name}' in client.app.openapi()['paths']


def test_accepts_queued_job_and_keeps_private_replay_input(collect_client):
    client, module, _, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    data = response.json()['data']
    assert data['status'] == 'queued'
    job = client.get('/api/jobs/' + data['job_id'], headers=HEADERS).json()['data']
    assert job['kind'] == 'collect' and job['total'] == 5
    assert job['params_json']['config']['repo_source'] == '[redacted]'
    path = module._request_path(job['params_json']['input_ref'])
    assert json.loads(path.read_bytes())['config']['repo_source'] == '/allowed/fixture'
    assert fc.sha256(path.read_bytes()) == job['params_json']['input_sha256']


def test_worker_publishes_checked_outputs_without_business_import(collect_client):
    client, module, _, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    with db.SessionLocal() as session:
        before = [session.scalar(select(func.count()).select_from(table)) for table in (Commit, Dataset)]
    assert module._execute(job_id, 0)
    data = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert data['status'] == 'success' and data['done'] == 5
    result = data['output_ref_json']
    preview = client.get('/api/collect/preview/' + job_id, headers=HEADERS).json()['data']
    assert preview['preview'][0]['is_bug_inducing'] is None
    assert result['columns'] == list(fc.COMMITS_COLUMNS)
    manifest = client.get(f'/api/collect/outputs/{job_id}/' + result['manifest_name'], headers=HEADERS).json()
    assert manifest['config']['feature_version'] == 'v1'
    assert '+collect.' in manifest['code_version']
    for entry in result['outputs']:
        download = client.get(f'/api/collect/outputs/{job_id}/' + entry['name'], headers=HEADERS)
        assert download.status_code == 200
        assert fc.sha256(download.content) == entry['sha256']
        assert download.headers['x-content-type-options'] == 'nosniff'
    csv_name = next(row['name'] for row in result['outputs'] if row['name'].endswith('.csv'))
    content = client.get(f'/api/collect/outputs/{job_id}/{csv_name}', headers=HEADERS).content
    assert content.startswith(b'\xef\xbb\xbf')
    assert fc.read_table(csv_name, content)[1][0]['is_bug_inducing'] == ''
    with db.SessionLocal() as session:
        assert before == [session.scalar(select(func.count()).select_from(table)) for table in (Commit, Dataset)]


@pytest.mark.parametrize('name,content', [('hashes.csv', b'commit_hash\nnope\n'),
    ('hashes.csv', b'wrong\na\n'), ('hashes.csv', b'commit_hash\n=SUM(1)\n'),
    ('hashes.xlsx', b'not an xlsx')])
def test_invalid_auxiliary_files_do_not_create_jobs(collect_client, name, content):
    client, _, _, _ = collect_client
    response = submit(client, files=[('files[]', (name, content))])
    assert response.status_code == 400 and response.json()['code'] == 40001
    assert client.get('/api/jobs?kind=collect', headers=HEADERS).json()['data']['total'] == 0


def test_csv_and_xlsx_commit_lists_share_normalization(collect_client):
    client, module, _, _ = collect_client
    for format in ('csv', 'xlsx'):
        content = fc.encode_table(['commit_hash'], [{'commit_hash': 'e' * 40}], format)
        response = submit(client, files=[('files[]', ('hashes.' + format, content))])
        assert response.status_code == 200
        job = client.get('/api/jobs/' + response.json()['data']['job_id'], headers=HEADERS).json()['data']
        request = json.loads(module._request_path(job['params_json']['input_ref']).read_bytes())
        assert request['commit_hashes'] == ['e' * 40]
        assert request['inputs'][0]['sha256'] == fc.sha256(content)


def test_cancel_stops_worker_and_does_not_publish(collect_client):
    client, module, fake, path = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.run

    def cancel(settings, **kwargs):
        client.post('/api/jobs/' + job_id + '/cancel', headers=HEADERS)
        return original(settings, **kwargs)
    fake.run = cancel
    module._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'cancelled'
    assert not (path / 'outputs' / job_id).exists()


def test_failure_retry_uses_original_input_and_new_attempt(collect_client, monkeypatch):
    client, module, fake, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.run
    fake.run = lambda *args, **kwargs: (_ for _ in ()).throw(fake.CollectError(40001, 'password:secret git failed'))
    module._execute(job_id, 0)
    failed = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert failed['status'] == 'failed' and 'secret' not in failed['error_log']
    dispatches = []
    monkeypatch.setattr(module, 'dispatch', lambda: dispatches.append(True))
    retried = client.post('/api/jobs/' + job_id + '/retry', headers=HEADERS)
    assert retried.json()['data']['retry_count'] == 1 and dispatches == [True]
    fake.run = original
    module._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'queued'
    module._execute(job_id, 1)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'


def test_tampered_replay_input_fails_without_outputs(collect_client):
    client, module, _, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    module._request_path(job['params_json']['input_ref']).write_bytes(b'{}')
    module._execute(job_id, 0)
    failed = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert failed['status'] == 'failed' and 'checksum' in failed['error_log']


def test_database_finish_failure_removes_only_new_output(collect_client, monkeypatch):
    client, module, _, path = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    monkeypatch.setattr(module.job_store, 'finish', lambda *args, **kwargs: (_ for _ in ()).throw(AppError(50000, 'database failed')))
    module._execute(job_id, 0)
    assert not (path / 'outputs' / job_id).exists()
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'failed'


@pytest.mark.parametrize('path', ['/api/collect/run', '/api/collect/outputs/missing/collect.csv'])
def test_collect_auth_before_parsing(client, path):
    response = client.post(path, content=b'bad multipart') if path.endswith('/run') else client.get(path)
    assert response.status_code == 401


def test_unknown_and_duplicate_form_parts_rejected(collect_client):
    client, _, _, _ = collect_client
    for data in ({'config': '{}', 'unknown': 'x'}, {'config': ['{}', '{}']}):
        response = client.post('/api/collect/run', data=data, headers=HEADERS)
        assert response.status_code == 400


def test_unknown_config_is_not_queued(collect_client):
    client, _, _, _ = collect_client
    response = submit(client, {'repo_source': '/allowed', 'dataset_name': 'fixture', 'random_split': True})
    assert response.status_code == 400


def test_request_and_output_references_cannot_escape(collect_client):
    client, module, _, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    for reference in ('../request.json', '/tmp/request.json', 'a' * 32 + '/other.json'):
        with pytest.raises(AppError):
            module._request_path(reference)
    assert client.get('/api/collect/outputs/missing/.index.json', headers=HEADERS).status_code == 404


def test_collect_upload_body_is_bounded_before_parser(collect_client, monkeypatch):
    client = collect_client[0]
    from app import main
    monkeypatch.setattr(main, 'MAX_IMPORT_BODY_BYTES', 10)
    response = client.post('/api/collect/run', content=iter([b'x' * 6, b'x' * 6]), headers=HEADERS)
    assert response.status_code == 400
    assert '总大小' in response.json()['message']


def test_lifespan_resumes_collect_queue_after_recovering_running(client, monkeypatch):
    from app.main import create_app
    from app.services import collect_run
    from fastapi.testclient import TestClient
    calls = []
    monkeypatch.setattr(collect_run, 'dispatch', lambda: calls.append(True))
    with TestClient(create_app()):
        pass
    assert calls == [True]


def test_preview_is_not_stored_in_text_sized_job_snapshot(collect_client):
    client, module, fake, _ = collect_client
    response = submit(client)
    assert response.status_code == 200
    job_id = response.json()['data']['job_id']
    original = fake.run

    def long_message(settings, **kwargs):
        result = original(settings, **kwargs)
        result['rows'][0]['message'] = '长' * 30000
        return result
    fake.run = long_message
    module._execute(job_id, 0)
    result = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert result['status'] == 'success'
    assert 'preview' not in result['output_ref_json']
    preview = client.get('/api/collect/preview/' + job_id, headers=HEADERS).json()['data']
    assert preview['preview'][0]['message'] == '长' * 30000
    assert preview['columns'] == list(fc.COMMITS_COLUMNS)
