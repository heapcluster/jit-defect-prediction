"""AI-generated W5 real integration tests; not human-reviewed."""
import json
import os
import subprocess
import sys

import pytest
from app import db
from app.models import Base, Model, ModelArtifact
from app.services import file_contracts as fc
from app.services import output_store
from sqlalchemy import select

from tests.conftest import FAKE_EXTRACTOR, HEADERS

ROOT = db.config.REPO_ROOT
PYTHON = sys.executable


def train_rows(n=12):
    """新契约：训练输入为 collected_commits 二维表（不含 Kamei14/is_test）。"""
    rows = []
    for i in range(n):
        rows.append({
            'commit_hash': f'{i + 1:040x}', 'repo_name': 'AI fixture',
            'repo_url': 'https://example.org/repo.git', 'author_name': '测试', 'author_email': '',
            'committed_at': f'2026-01-{i + 1:02d}T00:00:00Z', 'message': f'fixture {i}',
            'parent_hash': '', 'is_bug_inducing': i % 2, 'label_method': 'szz_v1',
            'label_source': 'git_szz', 'labeled_at': f'2026-01-{i + 1:02d}T01:00:00Z',
            'fix_commit_hash': '', 'source_type': 'git_repo',
        })
    return rows


def settings(**extra):
    return {'line': 'expert', 'feature_set': 'kamei14', 'algos': ['lr', 'rf'],
            'split': {'ratio': 0.7}, 'seed': 42, 'decision_threshold': 0.5, **extra}


def assert_train_testset(client, job_id, result):
    """新契约：train_testset_<job_id>.csv 为 §3.3 测试集，schema 同 clean_dataset。"""
    testset = result['testset']
    assert testset == f'train_testset_{job_id}.csv'
    assert testset in {item['name'] for item in result['outputs']}
    response = client.get(f'/api/train/outputs/{job_id}/{testset}', headers=HEADERS)
    assert response.status_code == 200, response.text
    columns, rows = fc.read_table(testset, response.content)
    assert tuple(columns) == tuple(fc.CLEAN_DATASET_COLUMNS)
    assert rows and all(row['is_bug_inducing'] not in ('', None) for row in rows)
    assert 'is_test' not in columns
    assert not any(column.startswith('semantic_') for column in columns)


def post(client, config=None, rows=None):
    return client.post('/api/train/run', data={'config': json.dumps(config if config is not None else settings())},
        files=[('files[]', ('cleaned.csv', fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows if rows is not None else train_rows(), 'csv')))], headers=HEADERS)


@pytest.fixture
def real_train(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from app.services import train_run
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    train_run._core.cache_clear()
    train_run._registry.cache_clear()
    monkeypatch.setattr(train_run, 'REQUEST_ROOT', tmp_path / 'inputs')
    monkeypatch.setattr(train_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    with TestClient(create_app()) as client:
        yield client, train_run, tmp_path


def test_algorithms_seeded_16_enabled(real_train):
    client, _, _ = real_train
    data = client.get('/api/algorithms?enabled_only=1', headers=HEADERS).json()['data']['algorithms']
    assert len(data) == 16
    assert {a['line'] for a in data} == {'expert', 'semantic'}
    assert len({a['family'] for a in data}) >= 2
    expert = client.get('/api/algorithms?line=expert', headers=HEADERS).json()['data']['algorithms']
    assert len(expert) == 12 and sum(a['enabled'] for a in expert) == 8


def test_real_train_packages_register_and_autoload(real_train):
    client, module, _ = real_train
    response = post(client, settings(register=True, auto_load=True))
    assert response.status_code == 200, response.text
    result = response.json()['data']
    assert result['status'] == 'success', result
    assert result['summary']['success_count'] == 2 and result['summary']['failed_count'] == 0
    job_id = result['job_id']
    job = client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']
    for sub in job['output_ref_json']['models']:
        assert sub['status'] == 'success' and sub['register_status'] == 'registered' and sub['load_status'] == 'loaded'
        zip_name = f'train_{sub["algo"]}_model_package_{job_id}.zip'
        blob = client.get(f'/api/train/outputs/{job_id}/{zip_name}', headers=HEADERS).content
        members = fc.read_zip(zip_name, blob)
        assert {'model_meta.json', 'feature_order.txt', 'feature_schema.json', 'checksum.sha256'} <= members.keys()
        assert members['feature_order.txt'].decode().splitlines() == list(fc.FEATURE_COLUMNS)
        meta = json.loads(members['model_meta.json'])
        assert meta['line'] == 'expert' and meta['algo'] == sub['algo'] and meta['seed'] == 42
        assert meta['feature_set'] == 'kamei14'
        with db.SessionLocal() as session:
            artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == sub['model_name']))
            assert artifact is not None and artifact.checksum_sha256 == fc.sha256(blob)
            assert session.get(Model, sub['model_name']) is not None
        from app import model_registry
        assert model_registry.get_model(sub['model_name']).model is not None
    assert_train_testset(client, job_id, result)
    compare = client.get('/api/train/compare', params={'job_id': job_id}, headers=HEADERS).json()['data']
    assert compare['primary_metric'] == 'auc' and len(compare['models']) == 2


def test_real_cli_api_parity(real_train, tmp_path):
    client, _, _ = real_train
    response = post(client, settings(algos=['lr']))
    assert response.status_code == 200 and response.json()['data']['status'] == 'success', response.text
    api_result = response.json()['data']
    api_sub = api_result['models'][0]
    source = tmp_path / 'cleaned.csv'
    source.write_bytes(fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, train_rows(), 'csv'))
    out = tmp_path / 'cli'
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'data_model'), 'DATABASE_URL': '', 'DB_HOST': '', 'MPLCONFIGDIR': str(tmp_path / 'mpl'), 'FEATURE_EXTRACTOR_SCRIPT': str(FAKE_EXTRACTOR)}
    proc = subprocess.run([PYTHON, '-B', '-m', 'pipelines.train', 'run', '--input', str(source), '--line', 'expert',
        '--feature-set', 'kamei14', '--algos', 'lr', '--split-ratio', '0.7', '--seed', '42',
        '--threshold', '0.5', '--out', str(out)],
        env=env, capture_output=True, text=True, cwd=str(ROOT / 'data_model'))
    assert proc.returncode == 0, proc.stderr
    registered = json.loads(proc.stdout)
    cli_comparison = json.loads((out / registered['job_id'] / f'train_comparison_{registered["job_id"]}.json').read_bytes())
    cli_sub = cli_comparison['models'][0]
    assert cli_sub['model_name'] == api_sub['model_name'] and cli_sub['version_key'] == api_sub['version_key']
    for metric in ('auc', 'f1', 'precision', 'recall', 'accuracy'):
        assert cli_sub['metrics'][metric] == pytest.approx(api_sub['metrics'][metric], abs=1e-9)
    # CLI 与 API 用同 inputs + 同 split/seed，测试集产物须逐字节一致。
    cli_testset = out / registered['job_id'] / f'train_testset_{registered["job_id"]}.csv'
    assert cli_testset.is_file()
    api_testset = client.get(
        f'/api/train/outputs/{api_result["job_id"]}/{api_result["testset"]}', headers=HEADERS).content
    assert cli_testset.read_bytes() == api_testset


def test_semantic_without_embedding_job_fails_without_outputs(real_train, monkeypatch):
    """semantic 线缺语义向量时任务失败且不落产物。"""
    client, _, path = real_train
    monkeypatch.setattr('app.semantic_source.embedding_for', lambda h: None)
    response = post(client, settings(line='semantic', feature_set='codebert768', algos=['lr']))
    assert response.status_code == 200, response.text
    assert response.json()['data']['status'] == 'failed'
    assert not (path / 'outputs').exists()


def test_real_template_run(real_train):
    client, _, _ = real_train
    template = {'line': 'expert', 'feature_set': 'kamei14', 'algos': ['lr'],
                'split': {'ratio': 0.7}, 'seed': 42, 'decision_threshold': 0.5}
    assert client.put('/api/config/train.templates', json={'value': {'AI tpl': template}}, headers=HEADERS).status_code == 200
    response = post(client, {'template_name': 'AI tpl'})
    assert response.status_code == 200 and response.json()['data']['status'] == 'success', response.text
    result = response.json()['data']
    assert_train_testset(client, result['job_id'], result)


def test_real_train_rejects_incompatible_feature_set(real_train):
    """新契约：feature_set 必须与 line 兼容（expert=kamei14 / semantic=codebert768）。"""
    client, _, _ = real_train
    response = post(client, settings(feature_set='codebert768'))
    assert response.status_code == 400
    assert response.json()['code'] == 40001


def test_real_template_rejects_bad_register_type(real_train):
    client, _, _ = real_train
    bad = {'line': 'expert', 'algos': ['lr'], 'register': 'yes'}
    assert client.put('/api/config/train.templates', json={'value': {'bad': bad}}, headers=HEADERS).status_code == 400
