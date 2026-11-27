"""AI-generated W7 evaluate API tests; not human-reviewed."""
import json

import pytest
from app import db
from app.models import Base
from app.services import evaluate_run, output_store
from app.services import file_contracts as fc

from tests.conftest import HEADERS


def pred_rows():
    # 新契约：一次评估固定单一模型、单一测试集。
    rows = []
    for i in range(8):
        risk = round((i + 1) / 9, 5)
        rows.append({"commit_hash": f"{i + 1:040x}", "model_name": "m1",
                     "risk_score": risk, "predicted_label": int(risk >= 0.5),
                     "decision_threshold": 0.5, "model_version": "v1",
                     "feature_version": "v1", "predicted_at": "2026-01-01T00:00:00Z", "is_bug_inducing": i % 2})
    return rows


def pred_file():
    return ('files[]', ('predictions.csv', fc.encode_table(fc.PREDICTIONS_COLUMNS, pred_rows(), 'csv')))


@pytest.fixture
def evalclient(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    monkeypatch.setattr(evaluate_run, 'REQUEST_ROOT', tmp_path / 'inputs')
    monkeypatch.setattr(evaluate_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    with TestClient(create_app()) as client:
        yield client, tmp_path


def post(client, config=None, files=None):
    # 新契约：评估不再接收 threshold，判定阈值逐行取自 predictions.decision_threshold。
    return client.post('/api/evaluate/run', data={'config': json.dumps(config or {'metrics': ['auc', 'f1'], 'primary_metric': 'auc'})},
        files=files if files is not None else [pred_file()], headers=HEADERS)


def test_metrics_registry_and_defaults(evalclient):
    client, _ = evalclient
    data = client.get('/api/evaluate/metrics', headers=HEADERS).json()['data']
    assert len(data['metrics']) == 10
    assert {'metrics_selected', 'primary_metric', 'effort_enabled'} <= data['defaults'].keys()
    assert client.get('/api/evaluate/metrics').status_code == 401


def test_run_delivers_section36_outputs(evalclient):
    client, _ = evalclient
    response = post(client)
    assert response.status_code == 200, response.text
    result = response.json()['data']
    assert result['status'] == 'success' and result['summary']['rows'] == 8
    job_id = result['job_id']
    names = [o['name'] for o in result['outputs']]
    assert any(n.startswith('evaluate_figures_') and n.endswith('.zip') for n in names)
    assert any(n.startswith('metrics_evaluate_') and n.endswith('.csv') for n in names)
    assert any(n.endswith('_effort_aware.png') for n in names)
    assert not any('comparison' in n or n.startswith('evaluate_report_') for n in names)
    metrics_name = next(n for n in names if n.startswith('metrics_evaluate_') and n.endswith('.csv'))
    columns, rows = fc.read_table(metrics_name, client.get(f'/api/evaluate/outputs/{job_id}/{metrics_name}', headers=HEADERS).content)
    assert columns == ["model_name", "line", "metric", "value", "threshold", "n", "pos_rate", "dataset_version", "model_version", "computed_at"]
    assert {r['model_name'] for r in rows} == {'m1'}


def test_deprecated_labels_and_unknown_files_rejected(evalclient):
    """labels.csv 已废止；真标签必须由 predictions 透传。未知表格一律拒绝。"""
    client, _ = evalclient
    labels = fc.encode_table(['commit_hash', 'is_bug_inducing', 'labeled_at'],
        [{'commit_hash': f'{1:040x}', 'is_bug_inducing': 1, 'labeled_at': '2026-01-01T00:00:00Z'}], 'csv')
    deprecated = post(client, files=[pred_file(), ('files[]', ('labels.csv', labels))])
    assert deprecated.status_code == 400
    bad = post(client, files=[('files[]', ('wrong.csv', b'a,b\n1,2\n'))])
    assert bad.status_code == 400


def test_effort_source_accepted_but_missing_effort_disclosed(evalclient):
    """新契约不含 la/ld，effort 来源被接受但 LOC 不可还原，必须披露 missing_effort。"""
    client, _ = evalclient
    commits = []
    for i in range(8):
        commits.append({
            'commit_hash': f'{i + 1:040x}', 'repo_name': 'r', 'repo_url': '',
            'author_name': 'a', 'author_email': '', 'committed_at': '2026-01-01T00:00:00Z',
            'message': 'm', 'parent_hash': '', 'is_bug_inducing': i % 2,
            'label_method': 'szz_v1', 'label_source': 'git_szz', 'labeled_at': '',
            'fix_commit_hash': '', 'source_type': 'git_repo',
        })
    effort_file = ('files[]', ('train_testset.csv', fc.encode_table(fc.CLEAN_DATASET_COLUMNS, commits, 'csv')))
    config = {'metrics': ['auc', 'recall_at_20', 'p_norm'], 'primary_metric': 'auc', 'effort_enabled': True}
    response = post(client, config=config, files=[pred_file(), effort_file])
    assert response.status_code == 200, response.text
    data = response.json()['data']
    assert data['status'] == 'success'
    assert data['summary']['effort'] == {'provided': 0, 'matched': 0}
    assert any(item['reason_code'] == 'missing_effort' for item in data['summary']['unavailable'])
    job_id = data['job_id']
    metrics_name = next(o['name'] for o in data['outputs'] if o['name'].startswith('metrics_evaluate_') and o['name'].endswith('.csv'))
    _, rows = fc.read_table(metrics_name, client.get(f'/api/evaluate/outputs/{job_id}/{metrics_name}', headers=HEADERS).content)
    vals = {r['metric']: r['value'] for r in rows if r['model_name'] == 'm1'}
    # 新契约不含 LOC：effort-aware 指标应为不可用，而不是伪造数值。
    assert vals['recall_at_20'] in (None, '') and vals['p_norm'] in (None, '')
    dup = post(client, config=config, files=[pred_file(), effort_file, effort_file])
    assert dup.status_code == 400


def test_queued_retry_cancel(evalclient, monkeypatch):
    client, path = evalclient
    monkeypatch.setattr(evaluate_run, 'SYNC_MAX_ROWS', 1)
    response = post(client)
    assert response.status_code == 200 and response.json()['data']['status'] == 'queued'
    job_id = response.json()['data']['job_id']
    assert evaluate_run._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'
    second = post(client).json()['data']['job_id']
    client.post('/api/jobs/' + second + '/cancel', headers=HEADERS)
    evaluate_run._execute(second, 0)
    assert client.get('/api/jobs/' + second, headers=HEADERS).json()['data']['status'] == 'cancelled'
    assert not (path / 'outputs' / second).exists()
