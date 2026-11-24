"""AI-generated W4 integration tests; not human-reviewed."""
import json

import pytest
from app import db
from app.models import Commit, Dataset
from app.services import file_contracts as fc
from app.services import output_store
from sqlalchemy import func, select

from tests.conftest import HEADERS
from tests.test_clean_api import post, settings, source_rows


@pytest.fixture
def real_clean(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from app.models import Base
    from app.services import clean_run
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    assert (clean_run.config.REPO_ROOT / 'data_model/preparation/clean.py').exists()
    clean_run._core.cache_clear()
    monkeypatch.setattr(clean_run, 'REQUEST_ROOT', tmp_path / 'inputs')
    monkeypatch.setattr(clean_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    with TestClient(create_app()) as client:
        yield client, clean_run, tmp_path


@pytest.mark.parametrize('mode', ['preview', 'apply'])
def test_real_clean_files_and_stats_equivalent_to_core(real_clean, mode):
    client, module, _ = real_clean
    response = post(client, mode)
    assert response.status_code == 200, response.text
    result = response.json()['data']
    assert result['status'] == 'success', result
    job_id = result['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    assert job['done'] == job['total'] == 3
    reference = job['output_ref_json']
    assert reference['mode'] == mode
    manifest = client.get(f'/api/clean/outputs/{job_id}/{reference["manifest_name"]}', headers=HEADERS).json()
    assert manifest['config']['mode'] == mode
    png_name = f'clean_column_distribution_final_is_bug_inducing_{job_id}.png'
    png = client.get(f'/api/clean/outputs/{job_id}/{png_name}', headers=HEADERS).content
    assert png.startswith(b'\x89PNG\r\n\x1a\n')
    for entry in reference['outputs']:
        data = client.get(f'/api/clean/outputs/{job_id}/{entry["name"]}', headers=HEADERS)
        assert data.status_code == 200 and fc.sha256(data.content) == entry['sha256']
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, source_rows(), 'csv')
    rows, metadata = module._core().parse_input('collected_commits.csv', content)
    direct = module._core().run(rows, settings(mode), metadata=metadata)
    assert reference['summary'] == direct['summary']
    if mode == 'apply':
        name = f'clean_dataset_{job_id}.csv'
        data = client.get(f'/api/clean/outputs/{job_id}/{name}', headers=HEADERS).content
        direct_bytes = module._core().artifacts(direct, job_id)[name]
        assert data == direct_bytes
        columns, parsed = fc.read_table(name, data)
        assert columns == list(fc.CLEAN_DATASET_COLUMNS)
        assert parsed[-1]['is_bug_inducing'] == ''
        assert 'is_test' not in columns


@pytest.mark.parametrize('config', [settings() | {'features': []}, settings() | {'steps': [{'op': 'unknown'}]},
    settings() | {'steps': [{'op': 'schema_validate'}, {'op': 'type_convert', 'params': {'columns': 'bad'}}]},
    settings() | {'steps': [{'op': 'derive_basic_fields'}, {'op': 'date_normalize'}]}, settings() | {'seed': True}])
def test_real_config_rejected_before_job(real_clean, config):
    client, _, path = real_clean
    response = post(client, config=config)
    assert response.status_code == 400, response.text
    assert client.get('/api/jobs?kind=clean', headers=HEADERS).json()['data']['total'] == 0
    assert not (path / 'outputs').exists()


def test_collect_file_handoff_apply_explicit_import_then_dataset_input(real_clean):
    client, module, _ = real_clean
    bytes_ = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, source_rows(), 'csv')
    batch = output_store.publish_output('collect', {'collect_commits_ai.csv': bytes_},
        inputs=[], config={'feature_version': 'v1'}, code_version='AI fixture')
    manifest_bytes = output_store.read_output('collect', batch['job_id'], batch['manifest_name']).read_bytes()
    response = post(client, 'apply', files=[('files[]', ('collect_commits_ai.csv', bytes_)),
        ('files[]', ('collect_commits_ai.manifest.json', manifest_bytes))])
    assert response.status_code == 200 and response.json()['data']['status'] == 'success', response.text
    job_id = response.json()['data']['job_id']
    with db.SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Commit)) == 0
        assert session.scalar(select(func.count()).select_from(Dataset)) == 0
    name = f'clean_dataset_{job_id}.csv'
    manifest = name.replace('.csv', '.manifest.json')
    uploaded = [('files[]', (file_name, output_store.read_output('clean', job_id, file_name).read_bytes())) for file_name in (name, manifest)]
    imported = client.post('/api/storage/import', files=uploaded, data={'config': json.dumps({'create_dataset': {'name': 'W4 AI fixture', 'source_type': 'git_repo', 'repo_name': 'fixture'}})}, headers=HEADERS)
    assert imported.status_code == 200 and imported.json()['data']['summary']['rejected'] == 0, imported.text
    dataset = client.get('/api/datasets', headers=HEADERS).json()['data']['items'][0]
    assert dataset['sample_count'] == 4 and dataset['pos_count'] == 1 and dataset['neg_count'] == 2
    again = post(client, files=[], config=settings() | {'dataset_id': dataset['dataset_id']})
    assert again.status_code == 200 and again.json()['data']['status'] == 'success', again.text
    with db.SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Dataset)) == 1
    job = client.get('/api/jobs/' + again.json()['data']['job_id'], headers=HEADERS).json()['data']
    snapshot = fc.read_json(module._request_path(job['params_json']['input_ref']).read_bytes())
    assert snapshot['metadata']['feature_version'] == 'v1'


def test_real_templates_validate_registry_and_reject_unknown_ops(real_clean):
    client, _, _ = real_clean
    for value, status in [({'good': settings()}, 200), ({'bad': settings() | {'steps': [{'op': 'wat'}]}}, 400)]:
        response = client.put('/api/config/clean.chain_templates', json={'value': value}, headers=HEADERS)
        assert response.status_code == status, response.text
