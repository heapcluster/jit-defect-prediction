"""AI-generated W9 boundary tests; not human-reviewed."""
import importlib.util
import json
import os
import subprocess
import sys

import pytest
from app import db
from app.models import Base, Job, Prediction
from app.services import file_contracts as fc
from app.services import output_store
from sqlalchemy import func, select

from tests.conftest import HEADERS
from tests.test_localization_core import git
from tests.test_localization_core import repository as repository


def service():
    assert importlib.util.find_spec('app.services.localize_run'), 'W9 API boundary is missing'
    from app.services import localize_run
    return localize_run


def predictions(commit):
    return [{'commit_hash': commit, 'model_name': 'fixture', 'risk_score': .7, 'predicted_label': 1,
             'decision_threshold': .5, 'model_version': 'v1', 'feature_version': 'v1',
             'predicted_at': '2026-01-01T00:00:00Z', 'is_bug_inducing': None}]


def files(commit):
    cells = [{key: '' if value is None else value for key, value in row.items()} for row in predictions(commit)]
    return [('files[]', ('predictions.csv', fc.encode_table(fc.PREDICTIONS_COLUMNS, cells, 'csv')))]


@pytest.fixture
def source_client(engine, repository, tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    mod = service()
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    monkeypatch.setattr(mod, '_policy', lambda session: {'allow_roots': [str(repository[0].parent)], 'protocol_whitelist': []})
    with TestClient(create_app()) as client:
        yield client, mod, repository


def test_routes_are_real(client):
    assert {'/api/source/tree', '/api/source/file', '/api/localize/run', '/api/localize/outputs/{job_id}/{name}'} <= client.app.openapi()['paths'].keys()


def test_source_is_commit_version_with_explicit_statuses(source_client):
    client, _, repo = source_client
    params = {'repo_source': str(repo[0]), 'commit_hash': repo[1]}
    tree = client.get('/api/source/tree', params=params, headers=HEADERS)
    assert tree.status_code == 200, tree.text
    assert any(x['path'] == 'src' for x in tree.json()['data']['entries'])
    data = client.get('/api/source/file', params={**params, 'path': 'src/代码 space.java', 'end_line': 200}, headers=HEADERS).json()['data']
    assert data['status'] == 'ok' and 'int value = 1' in data['content'] and 'DIRTY' not in data['content']
    for path, expected in [('missing.java', 'not_found'), ('binary.bin', 'binary')]:
        response = client.get('/api/source/file', params={**params, 'path': path}, headers=HEADERS)
        assert response.status_code == 200 and response.json()['data']['status'] == expected
    assert client.get('/api/source/file', params={**params, 'path': '../escape'}, headers=HEADERS).status_code == 400
    assert client.get('/api/source/tree', params=params).status_code == 401


def test_localize_outputs_four_sections_and_no_job_mutation(source_client):
    client, mod, repo = source_client
    before = git(repo[0], 'status', '--porcelain'), git(repo[0], 'rev-parse', 'HEAD'), git(repo[0], 'rev-list', '--count', 'HEAD')
    response = client.post('/api/localize/run', data={'config': json.dumps({'repo_source': str(repo[0]), 'patch_preview': True})}, files=files(repo[2]), headers=HEADERS)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['status'] == 'success' and data['summary']['commits'] == 1
    assert data['summary']['patch_reason'] == 'no_reliable_patch'
    assert all(row['commit_hash'] == repo[2] for row in data['localization'])
    assert not any(entry['name'].endswith('.diff') for entry in data['outputs'])
    for entry in data['outputs']:
        url = f'/api/localize/outputs/{data["job_id"]}/{entry["name"]}'
        assert client.get(url).status_code == 401
        downloaded = client.get(url, headers=HEADERS)
        assert downloaded.status_code == 200 and fc.sha256(downloaded.content) == entry['sha256']
    assert all(heading in data['suggestions'] for heading in ('问题说明', '建议修改', '风险提示', '参考依据'))
    assert before == (git(repo[0], 'status', '--porcelain'), git(repo[0], 'rev-parse', 'HEAD'), git(repo[0], 'rev-list', '--count', 'HEAD'))
    with db.SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Job)) == 0
        assert session.scalar(select(func.count()).select_from(Prediction)) == 0


@pytest.mark.parametrize('extra', [{'top_n': {'files': True}}, {'weights': {'hunk': -1}}, {'unknown': 1}])
def test_invalid_configuration_prevents_publication(source_client, extra):
    client, _, repo = source_client
    response = client.post('/api/localize/run', data={'config': json.dumps({'repo_source': str(repo[0]), **extra})}, files=files(repo[2]), headers=HEADERS)
    assert response.status_code == 400


def test_partial_run_config_preserves_saved_nested_values(source_client):
    client, _, repo = source_client
    assert client.put('/api/config/localization.weights', json={'value': {'line_path': {'source': .2}, 'hunk': .9}}, headers=HEADERS).status_code == 200
    assert client.put('/api/config/localization.top_n', json={'value': {'files': 2, 'lines': 4}}, headers=HEADERS).status_code == 200
    response = client.post('/api/localize/run', data={'config': json.dumps({'repo_source': str(repo[0]), 'weights': {'hunk': .1}, 'top_n': {'lines': 1}})}, files=files(repo[2]), headers=HEADERS)
    assert response.status_code == 200, response.text
    evidence = json.loads(response.json()['data']['localization'][0]['evidence_json'])
    assert evidence['signal_weights']['line_path']['source'] == .2
    assert evidence['signal_weights']['hunk'] == .1
    manifest = next(item for item in response.json()['data']['outputs'] if item['name'].endswith('.manifest.json'))
    meta = client.get(f'/api/localize/outputs/{response.json()["data"]["job_id"]}/{manifest["name"]}', headers=HEADERS).json()
    assert meta['config']['top_n'] == {'files': 2, 'lines': 1}


def test_explanation_version_is_checked(source_client):
    client, _, repo = source_client
    columns = ['commit_hash', 'model_name', 'technique', 'feature', 'raw_value', 'contribution', 'direction', 'rank', 'label', 'model_version', 'feature_version', 'reason_code']
    row = {'commit_hash': repo[2], 'model_name': 'fixture', 'technique': 'shap', 'feature': 'la', 'raw_value': 1, 'contribution': .3,
           'direction': 'increase', 'rank': 1, 'label': '新增', 'model_version': 'wrong', 'feature_version': 'v1', 'reason_code': ''}
    response = client.post('/api/localize/run', data={'config': json.dumps({'repo_source': str(repo[0])})},
        files=[*files(repo[2]), ('files[]', ('explanations.csv', fc.encode_table(columns, [row], 'csv')))], headers=HEADERS)
    assert response.status_code == 400


def test_cli_config_is_not_overwritten_by_unsupplied_flags(repository, tmp_path):
    src = tmp_path / 'predictions.csv'
    records = predictions(repository[2]) + predictions(repository[3])
    src.write_bytes(fc.encode_table(fc.PREDICTIONS_COLUMNS, [{k: '' if v is None else v for k, v in row.items()} for row in records], 'csv'))
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'commit_hash': repository[3], 'top_n': {'files': 1, 'lines': 1}, 'patch_preview': False, 'format': 'xlsx'}))
    result = subprocess.run([sys.executable, '-m', 'app.cli', 'localize', 'run', '--repo', str(repository[0]), '--allow-root', str(repository[0].parent), '--predictions', str(src), '--config', str(cfg), '--out', str(tmp_path / 'out')], capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data['summary']['commits'] == 1 and data['summary']['patch_reason'] is None
    assert data['localization'][0]['commit_hash'] == repository[3]
    assert data['outputs'][0]['name'].endswith('.xlsx')


def test_cli_sources_and_localize_are_db_independent(repository, tmp_path):
    service()
    pred = tmp_path / 'predictions.csv'
    pred.write_bytes(files(repository[2])[0][1][1])
    output = tmp_path / 'cli'
    env = {**os.environ, 'DB_HOST': '', 'DATABASE_URL': ''}
    base = [sys.executable, '-m', 'app.cli']
    args = ['--repo', str(repository[0]), '--allow-root', str(repository[0].parent)]
    source = subprocess.run([*base, 'source', 'file', *args, '--commit', repository[1], '--path', 'src/代码 space.java'], env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert source.returncode == 0, source.stderr
    assert 'int value = 1' in json.loads(source.stdout)['content']
    localized = subprocess.run([*base, 'localize', 'run', *args, '--predictions', str(pred), '--out', str(output)], env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert localized.returncode == 0, localized.stderr
    data = json.loads(localized.stdout)
    assert data['summary']['commits'] == 1
