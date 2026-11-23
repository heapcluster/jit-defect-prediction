"""AI-generated stale/version persistence tests; not human-reviewed."""
from datetime import datetime

from app import db
from app.models import CommitFeature, Model, Prediction
from app.services.predict import predict_single

from tests.conftest import C1


def _row():
    with db.SessionLocal() as session:
        return session.get(Prediction, (C1, "fixture_v2"))


def test_legacy_null_versions_are_stale_not_verified_fresh(client):
    data = predict_single(C1, "fixture_v2")
    assert data["result_source"] == "stored"
    assert data["stale"] is True


def test_computed_persists_versions_and_stored_same_version_is_fresh(client):
    computed = predict_single(C1, "fixture_v2", force_recompute=True)
    assert computed["result_source"] == "computed"
    row = _row()
    assert row.model_version == computed["model_version"]
    assert row.feature_version == computed["feature_version"] == "v1"
    again = predict_single(C1, "fixture_v2")
    assert again["result_source"] == "stored"
    assert again["stale"] is False
    assert again["predicted_at"] == computed["predicted_at"]


def test_model_version_change_marks_stored_result_stale(client):
    predict_single(C1, "fixture_v2", force_recompute=True)
    with db.SessionLocal() as session:
        session.get(Model, "fixture_v2").version_key = "new-model-version"
        session.commit()
    data = predict_single(C1, "fixture_v2")
    assert data["result_source"] == "stored"
    assert data["stale"] is True
    assert data["model_version"] == "new-model-version"
    refreshed = predict_single(C1, "fixture_v2", force_recompute=True)
    assert refreshed["stale"] is False
    assert _row().model_version == "new-model-version"
    assert predict_single(C1, "fixture_v2")["stale"] is False


def test_feature_version_change_marks_stored_result_stale(client):
    predict_single(C1, "fixture_v2", force_recompute=True)
    with db.SessionLocal() as session:
        session.get(CommitFeature, C1).feature_version = "v2"
        session.commit()
    data = predict_single(C1, "fixture_v2")
    assert data["result_source"] == "stored"
    assert data["stale"] is True
    assert data["feature_version"] == "v2"
    predict_single(C1, "fixture_v2", force_recompute=True)
    assert _row().feature_version == "v2"
    assert predict_single(C1, "fixture_v2")["stale"] is False


def test_sync_all_models_path_persists_versions(client):
    from app.services.predict import predict_commit_all_models

    predict_commit_all_models(C1, model_names=["fixture_v2"])
    row = _row()
    assert row.model_version and row.feature_version == "v1"
    assert row.predicted_at > datetime(2026, 9, 1, 8, 0, 0)
