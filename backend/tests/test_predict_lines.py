"""两线批量预测输入测试：expert 14 维现算 / semantic 768 维向量。"""
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
    return ('files[]', ('cleaned.csv', fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, train_rows(), 'csv')))


def run(client, line, files, monkeypatch, widths, proba=0.42):
    monkeypatch.setattr(predict_run, '_resolve_model', lambda *a: ('m_' + line, line, 'v1', 'v1'))
    monkeypatch.setattr(model_registry, 'get_model', lambda name: SimpleNamespace(name=name, model=object(), line=line))
    monkeypatch.setattr(model_registry, 'predict_proba', lambda model, vector: widths.append(len(vector)) or proba)
    # 本测试只验证特征向量宽度；模型解析被 mock，未登记到 Model 表，故关闭落库。
    return client.post('/api/predict/run', data={'config': json.dumps({'decision_threshold': 0.5, 'save_to_db': False})}, files=files, headers=HEADERS)


def test_expert_batch_uses_14_feature_vector(lineclient):
    client, _, monkeypatch = lineclient
    widths = []
    response = run(client, 'expert', [commits_file()], monkeypatch, widths)
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['status'] == 'success' and data['summary']['success_count'] == len(train_rows())
    assert widths and all(w == 14 for w in widths)


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
