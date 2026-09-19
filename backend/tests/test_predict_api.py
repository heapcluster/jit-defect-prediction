from app import model_registry
from app.db import SessionLocal
from app.models import Prediction
from tests.conftest import C1, C3, FEATURE_VALUES, HEADERS, UNKNOWN


def _rows_for(hash_, model):
    with SessionLocal() as session:
        return (
            session.query(Prediction)
            .filter_by(commit_hash=hash_, model_name=model)
            .count()
        )


def test_predict_success(client):
    body = client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS).json()
    data = body["data"]
    assert body["code"] == 0
    assert 0.0 <= data["risk_score"] <= 1.0
    assert data["model_name"] == "fixture_v2"  # mtime 最新者
    assert set(data["features"]) == set(FEATURE_VALUES)
    assert isinstance(data["explanation"], list)
    assert data["predicted_at"].endswith("Z")


def test_predict_missing_hash(client):
    resp = client.post("/api/predict", json={}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_predict_bad_hash_format(client):
    resp = client.post("/api/predict", json={"commit_hash": "z" * 40}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_predict_unknown_commit(client):
    resp = client.post("/api/predict", json={"commit_hash": UNKNOWN}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["message"] == "commit not found"


def test_predict_missing_features(client):
    resp = client.post("/api/predict", json={"commit_hash": C3}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["message"] == "features not found for this commit"


def test_predict_idempotent_single_row(client):
    client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS)
    client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS)
    assert _rows_for(C1, "fixture_v2") == 1


def test_predict_second_model_new_row(client):
    client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS)
    client.post("/api/predict", json={"commit_hash": C1, "model_name": "fixture_v1"}, headers=HEADERS)
    assert _rows_for(C1, "fixture_v1") == 1
    assert _rows_for(C1, "fixture_v2") == 1


def test_predict_unknown_model_name_is_40001(client):
    resp = client.post("/api/predict", json={"commit_hash": C1, "model_name": "nope"}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_predict_without_models_is_50000_without_path(client, monkeypatch):
    monkeypatch.setattr(model_registry, "_REGISTRY", {})
    resp = client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS)
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == 50000
    assert body["message"] == "internal error"
    assert ".pkl" not in body["message"]
