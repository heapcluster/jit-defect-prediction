"""AI-generated W6 batch predict tests; not human-reviewed."""
import json
import os
import subprocess

import pytest
from app import db, model_registry
from app.models import Base
from app.services import file_contracts as fc
from app.services import output_store, predict_run, storage, train_run

from tests.conftest import HEADERS
from tests.test_models_manage import lr_package
from tests.test_train_real import PYTHON, ROOT, train_rows


@pytest.fixture
def batch(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    train_run._core.cache_clear()
    monkeypatch.setattr(predict_run, 'REQUEST_ROOT', tmp_path / 'inputs')
    monkeypatch.setattr(predict_run, 'dispatch', lambda: None)
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    name, feature_version, raw = lr_package()
    model_registry.unload(name)
    with TestClient(create_app()) as client:
        yield client, name, raw, tmp_path


def table_file():
    return ('files[]', ('cleaned.csv', fc.encode_table(fc.COMMITS_COLUMNS, train_rows(), 'csv')))


def post(client, raw, config=None, with_zip=True):
    files = [('files[]', ('model_package.zip', raw)), table_file()] if with_zip else [table_file()]
    return client.post('/api/predict/run', data={'config': json.dumps(config or {'decision_threshold': 0.5, 'force_recompute': True})}, files=files, headers=HEADERS)


def test_batch_uploaded_zip_delivers_predictions(batch):
    client, name, raw, _ = batch
    response = post(client, raw)
    assert response.status_code == 200, response.text
    result = response.json()['data']
    assert result['status'] == 'success' and result['summary']['success_count'] == len(train_rows())
    job_id = result['job_id']
    csv_name = f'predict_predictions_{job_id}.csv'
    content = client.get(f'/api/predict/outputs/{job_id}/{csv_name}', headers=HEADERS).content
    columns, rows = fc.read_table(csv_name, content)
    assert columns == list(fc.PREDICTIONS_COLUMNS)
    assert content.startswith(b'\xef\xbb\xbf')
    for row in rows:
        assert len(row['risk_score'].split('.')[-1]) <= 5
        assert row['predicted_label'] == str(int(float(row['risk_score']) >= 0.5))
    assert any(row['is_bug_inducing'] == '' for row in rows) or all(row['is_bug_inducing'] != '' for row in rows)
    summary = json.loads(client.get(f'/api/predict/outputs/{job_id}/predict_summary_{job_id}.json', headers=HEADERS).content)
    assert summary['model_name'] == name and summary['failed_count'] == 0


def test_batch_registered_model_without_zip(batch):
    client, name, raw, _ = batch
    with db.SessionLocal() as session:
        storage.import_files(session, [('model_package.zip', raw)])
    response = post(client, raw, config={'model_name': name, 'decision_threshold': 0.5}, with_zip=False)
    assert response.status_code == 200 and response.json()['data']['status'] == 'success', response.text


def test_batch_semantic_without_input_rejected_pre_job(batch, monkeypatch):
    client, name, raw, path = batch
    monkeypatch.setattr(predict_run, '_resolve_model', lambda *a: (name, 'semantic', None, None))
    empty = ('files[]', ('cleaned.csv', fc.encode_table(fc.COMMITS_COLUMNS, [], 'csv')))
    response = client.post('/api/predict/run', data={'config': json.dumps({'decision_threshold': 0.5})},
                           files=[('files[]', ('model_package.zip', raw)), empty], headers=HEADERS)
    assert response.status_code == 400
    assert client.get('/api/jobs?kind=predict_batch', headers=HEADERS).json()['data']['total'] == 0


def test_batch_queued_retry_cancel(batch, monkeypatch):
    client, name, raw, path = batch
    monkeypatch.setattr(predict_run, 'SYNC_MAX_ROWS', 1)
    response = post(client, raw)
    assert response.status_code == 200 and response.json()['data']['status'] == 'queued'
    job_id = response.json()['data']['job_id']
    assert predict_run._execute(job_id, 0)
    assert client.get('/api/jobs/' + job_id, headers=HEADERS).json()['data']['status'] == 'success'
    second = post(client, raw).json()['data']['job_id']
    original = predict_run._predict_rows
    def cancel(*a, **k):
        client.post('/api/jobs/' + second + '/cancel', headers=HEADERS)
        return original(*a, **k)
    monkeypatch.setattr(predict_run, '_predict_rows', cancel)
    predict_run._execute(second, 0)
    assert client.get('/api/jobs/' + second, headers=HEADERS).json()['data']['status'] == 'cancelled'
    assert not (path / 'outputs' / second).exists()


def test_batch_cli_api_parity(batch, tmp_path):
    client, name, raw, _ = batch
    response = post(client, raw)
    assert response.status_code == 200 and response.json()['data']['status'] == 'success', response.text
    job_id = response.json()['data']['job_id']
    api_csv = client.get(f'/api/predict/outputs/{job_id}/predict_predictions_{job_id}.csv', headers=HEADERS).content
    _, api_rows = fc.read_table('p.csv', api_csv)
    pkg = tmp_path / 'model_package.zip'
    pkg.write_bytes(raw)
    src = tmp_path / 'cleaned.csv'
    src.write_bytes(fc.encode_table(fc.COMMITS_COLUMNS, train_rows(), 'csv'))
    out = tmp_path / 'cli'
    env = {**os.environ, 'PYTHONPATH': str(ROOT / 'backend'), 'DATABASE_URL': '', 'DB_HOST': '', 'MPLCONFIGDIR': str(tmp_path / 'mpl')}
    proc = subprocess.run([PYTHON, '-B', '-m', 'app.cli', 'predict', 'run', '--model-package', str(pkg),
        '--input', str(src), '--threshold', '0.5', '--out', str(out)], env=env, capture_output=True, text=True, cwd=str(ROOT / 'backend'))
    assert proc.returncode == 0, proc.stderr
    registered = json.loads(proc.stdout)
    cli_csv = (out / registered['job_id'] / f'predict_predictions_{registered["job_id"]}.csv').read_bytes()
    _, cli_rows = fc.read_table('p.csv', cli_csv)
    assert [r['risk_score'] for r in cli_rows] == [r['risk_score'] for r in api_rows]
    assert [r['predicted_label'] for r in cli_rows] == [r['predicted_label'] for r in api_rows]
