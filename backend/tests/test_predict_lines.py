"""AI-generated semantic/fused/e2e batch input tests; not human-reviewed."""
import json
from types import SimpleNamespace

import numpy as np
import pytest
from app import db, model_registry
from app.models import Base
from app.services import file_contracts as fc
from app.services import output_store, predict_run

from tests.conftest import HEADERS
from tests.test_train_real import train_rows


@pytest.fixture
def lineclient(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    monkeypatch.setattr(predict_run, 'REQUEST_ROOT', tmp_path / 'inputs')
    monkeypatch.setattr(predict_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    with TestClient(create_app()) as client:
        yield client, tmp_path, monkeypatch


def commits_file():
    return ('files[]', ('cleaned.csv', fc.encode_table(fc.COMMITS_COLUMNS, train_rows(), 'csv')))


def text_file():
    rows = [{'commit_hash': r['commit_hash'], 'text': 'diff --git a/x b/x\n+added line'} for r in train_rows()]
    return ('files[]', ('commit_text.csv', fc.encode_table(['commit_hash', 'text'], rows, 'csv')))


def run(client, line, files, monkeypatch, widths, proba=0.42):
    monkeypatch.setattr(predict_run, '_resolve_model', lambda *a: ('m_' + line, line, 'v1', 'v1'))
    monkeypatch.setattr(model_registry, 'get_model', lambda name: SimpleNamespace(name=name, model=object(), line=line))
    monkeypatch.setattr(model_registry, 'predict_proba', lambda model, vector: widths.append(len(vector)) or proba)
    return client.post('/api/predict/run', data={'config': json.dumps({'decision_threshold': 0.5})}, files=files, headers=HEADERS)


def test_semantic_batch_uses_768_embedding(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr('app.semantic_source.embedding_for', lambda h: np.full(768, 0.1, dtype=np.float32))
    widths = []
    response = run(client, 'semantic', [commits_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['status'] == 'success' and data['summary']['success_count'] == len(train_rows())
    assert widths and all(w == 768 for w in widths)
    job_id = data['job_id']
    _, rows = fc.read_table('p.csv', client.get(f'/api/predict/outputs/{job_id}/predict_predictions_{job_id}.csv', headers=HEADERS).content)
    assert all(r['risk_score'] == '0.42' for r in rows)


def test_fused_batch_uses_782_vector(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr('app.semantic_source.embedding_for', lambda h: np.full(768, 0.1, dtype=np.float32))
    widths = []
    response = run(client, 'fused', [commits_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    assert response.json()['data']['summary']['success_count'] == len(train_rows())
    assert widths and all(w == 782 for w in widths)


def test_e2e_batch_uses_text_model(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr('app.e2e_source.predict_proba', lambda h: 0.37)
    widths = []
    response = run(client, 'e2e', [commits_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['summary']['success_count'] == len(train_rows())
    job_id = data['job_id']
    _, rows = fc.read_table('p.csv', client.get(f'/api/predict/outputs/{job_id}/predict_predictions_{job_id}.csv', headers=HEADERS).content)
    assert all(r['risk_score'] == '0.37' for r in rows)


def test_e2e_batch_accepts_explicit_text_file(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr('app.e2e_source.predict_proba_text', lambda text: 0.55)
    widths = []
    response = run(client, 'e2e', [text_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['summary']['success_count'] == len(train_rows())
    job_id = data['job_id']
    _, rows = fc.read_table('p.csv', client.get(f'/api/predict/outputs/{job_id}/predict_predictions_{job_id}.csv', headers=HEADERS).content)
    assert all(r['risk_score'] == '0.55' for r in rows)


def test_semantic_missing_embedding_fails_rows_not_job(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr('app.semantic_source.embedding_for', lambda h: None)
    widths = []
    response = run(client, 'semantic', [commits_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['summary']['success_count'] == 0
    assert data['summary']['failed_count'] == len(train_rows())
    assert data['summary']['failed_samples']


def test_e2e_uploaded_package_rejected(lineclient):
    client, _, monkeypatch = lineclient
    monkeypatch.setattr(predict_run, '_resolve_model', lambda *a: ('codebert_e2e_v1', 'e2e', 'v1', 'v1'))
    response = client.post('/api/predict/run', data={'config': json.dumps({})},
                           files=[commits_file(), ('files[]', ('model_package.zip', b'PK\x03\x04fake'))], headers=HEADERS)
    assert response.status_code == 400
