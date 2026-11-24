"""AI-generated W6 model management tests; not human-reviewed."""
import pytest
from app import db, model_registry
from app.models import Base, ModelArtifact
from app.services import output_store, storage, train_run
from sqlalchemy import select

from tests.conftest import HEADERS, TEST_REPO
from tests.test_train_real import train_rows


def lr_package(seed=42):
    core = train_run._core()
    cfg = core.validate_config({'line': 'expert', 'algos': ['lr'], 'split': {'ratio': 0.7}, 'seed': seed, 'decision_threshold': 0.5})
    result = core.run(train_rows(), cfg, metadata={'repo': str(TEST_REPO)})
    name = result['models'][0]['model_name']
    return name, result['models'][0]['feature_version'], core.artifacts(result, 'pkg')['train_lr_model_package_pkg.zip']


@pytest.fixture
def manage(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from app.services import predict_run
    from fastapi.testclient import TestClient
    assert engine.url.database in {'jit_test', 'jit_test_w2_validation_447e6b8c'}
    with db.SessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    train_run._core.cache_clear()
    monkeypatch.setattr(output_store, 'OUTPUT_ROOT', tmp_path / 'outputs')
    monkeypatch.setattr(predict_run, 'dispatch', lambda: None)
    name, feature_version, raw = lr_package()
    model_registry.unload(name)
    with db.SessionLocal() as session:
        storage.import_files(session, [('model_package.zip', raw)])
    with TestClient(create_app()) as client:
        yield client, name, feature_version, tmp_path


def test_status_load_unload_reload_default(manage):
    client, name, _, _ = manage
    status = client.get('/api/models/status', headers=HEADERS).json()['data']
    item = next(i for i in status['items'] if i['model_name'] == name)
    assert item['artifact_status'] == 'available' and item['checksum_sha256']
    loaded = client.post(f'/api/models/{name}/load', headers=HEADERS).json()['data']
    assert loaded['runtime_state'] == 'loaded' and loaded['load_error'] is None
    assert model_registry.has(name)
    reloaded = client.post(f'/api/models/{name}/reload', headers=HEADERS).json()['data']
    assert reloaded['runtime_state'] == 'loaded'
    assert client.put('/api/models/selection', json={'model_name': name}, headers=HEADERS).json()['data']['selected_model'] == name
    assert client.get('/api/models/status', headers=HEADERS).json()['data']['selected_model'] == name


def test_unload_non_selected(manage):
    client, name, _, _ = manage
    other, _, raw2 = lr_package(seed=7)
    model_registry.unload(other)
    with db.SessionLocal() as session:
        storage.import_files(session, [('model_package2.zip', raw2)])
    client.put('/api/models/selection', json={'model_name': name}, headers=HEADERS)
    unloaded = client.post(f'/api/models/{other}/unload', headers=HEADERS).json()['data']
    assert unloaded['runtime_state'] == 'unloaded'


def test_unload_selected_model_allowed(manage):
    client, name, _, _ = manage
    client.put('/api/models/selection', json={'model_name': name}, headers=HEADERS)
    unloaded = client.post(f'/api/models/{name}/unload', headers=HEADERS).json()['data']
    assert unloaded['runtime_state'] == 'unloaded'


def test_checksum_mismatch_load_failed_preserves(manage):
    client, name, _, _ = manage
    client.post(f'/api/models/{name}/load', headers=HEADERS)
    with db.SessionLocal() as session:
        artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == name))
        artifact.checksum_sha256 = '0' * 64
        session.commit()
    result = client.post(f'/api/models/{name}/reload', headers=HEADERS).json()['data']
    assert result['load_error'] and result['runtime_state'] in ('loaded', 'load_failed')
    assert model_registry.has(name)


def test_unknown_model_404_and_get_no_load(manage):
    client, name, _, _ = manage
    assert client.post('/api/models/nope_v1/load', headers=HEADERS).status_code == 404
    assert client.get('/api/models/status?line=bogus', headers=HEADERS).status_code == 400
    model_registry.unload(name)
    client.get('/api/models/status', headers=HEADERS)
    assert not model_registry.has(name)


def test_load_body_rejected(manage):
    client, name, _, _ = manage
    assert client.post(f'/api/models/{name}/load', json={'x': 1}, headers=HEADERS).status_code == 400
