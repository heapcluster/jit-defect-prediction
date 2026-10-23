from __future__ import annotations

import csv
from datetime import datetime

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, db, model_registry
from app.ingest import ingest
from app.main import create_app
from app.models import Commit, CommitFeature, CommitLabel, Prediction
from tests.conftest import C1, C2, C3, FEATURE_VALUES, HEADERS

C4 = "e" * 40


@pytest.fixture()
def integration_db(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    previous_bind = db.SessionLocal.kw.get("bind")
    monkeypatch.setattr(db, "_engine", engine)
    monkeypatch.setattr(model_registry, "_REGISTRY", {})
    weights = tmp_path / "weights"
    weights.mkdir()
    monkeypatch.setattr(config, "MODEL_DIR", weights)
    rng = np.random.RandomState(7)
    x = rng.rand(60, 14)
    model = DecisionTreeClassifier(max_depth=3, random_state=7).fit(
        x, (x[:, 3] > 0.5).astype(int)
    )
    joblib.dump(model, weights / "integration_v1.pkl")
    joblib.dump(model, weights / "integration_v2.pkl")
    # 交付清单（#96）是在线模型的唯一来源：联调夹具也必须声明，否则注册表恒为空。
    (weights / "feature_order.txt").write_text(
        "[models]\nintegration_v1.pkl\nintegration_v2.pkl\n[feature_order]\n"
        + "\n".join(f"{i}. {name}" for i, name in enumerate(config.FEATURE_COLUMNS, 1))
        + "\n",
        encoding="utf-8",
    )
    db.SessionLocal.configure(bind=engine)
    try:
        db.init_db()
        yield engine, tmp_path
    finally:
        db.SessionLocal.configure(bind=previous_bind)
        engine.dispose()


@pytest.fixture()
def csv_paths(integration_db):
    _, folder = integration_db
    times = {C1: "2026-07-31T09:00:00Z", C2: "2026-08-02T09:00:00Z",
             C3: "2026-08-03T09:00:00Z", C4: "2026-08-04T09:00:00Z"}
    rows = {
        "commits": [
            {"repo_name": "camel", "commit_hash": h, "author_name": "fixture-author",
             "committed_at": t, "message": "fixture commit"}
            for h, t in times.items()
        ],
        "labels": [
            {"commit_hash": h, "is_bug_inducing": i % 2, "label_method": "szz",
             "labeled_at": "2026-09-01T00:00:00Z"}
            for i, h in enumerate(times)
        ],
        "features": [
            {"commit_hash": h, "committed_at": times[h], "feature_version": "v1",
             **FEATURE_VALUES}
            for h in (C1, C2, C4)
        ],
        "predictions": [
            {"commit_hash": h, "model_name": "integration_v2", "risk_score": score,
             "predicted_at": "2026-09-01T00:00:00Z", "feature_version": "v1"}
            for h, score in ((C1, 0.8), (C2, 0.2))
        ],
    }
    paths = {}
    for kind, records in rows.items():
        path = folder / f"{kind}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        paths[kind] = path
    return paths


@pytest.fixture()
def populated_api(integration_db, csv_paths):
    engine, _ = integration_db
    for kind, path in csv_paths.items():
        assert ingest(kind, str(path)) == 0
    with TestClient(create_app()) as client:
        yield client, engine


def test_four_csv_ingests_are_idempotent(integration_db, csv_paths):
    engine, _ = integration_db
    assert set(inspect(engine).get_table_names()) == {
        "commit", "commit_label", "commit_feature", "prediction"
    }
    for _ in range(2):
        db.init_db()
        for kind, path in csv_paths.items():
            assert ingest(kind, str(path)) == 0
        with sessionmaker(bind=engine)() as session:
            for model, count in ((Commit, 4), (CommitLabel, 4), (CommitFeature, 3), (Prediction, 2)):
                assert session.scalar(select(func.count()).select_from(model)) == count
            assert session.scalar(select(Commit.message).where(Commit.commit_hash == C1)) == "fixture commit"
            feature = session.get(CommitFeature, C1)
            assert feature.feature_version == "v1"
            assert float(feature.la) == pytest.approx(FEATURE_VALUES["la"])


def test_predict_then_query_and_repeat_keeps_one_row(populated_api):
    client, engine = populated_api
    first = client.post("/api/predict", headers=HEADERS, json={"commit_hash": C1})
    second = client.post("/api/predict", headers=HEADERS, json={"commit_hash": C1})
    assert first.status_code == second.status_code == 200
    predicted = second.json()["data"]
    assert second.json()["code"] == 0
    assert predicted["model_name"] == "integration_v2"
    assert predicted["explanation"]
    assert set(predicted["features"]) == set(FEATURE_VALUES)
    assert predicted["predicted_at"].endswith("Z")
    with sessionmaker(bind=engine)() as session:
        saved = session.scalars(select(Prediction).where(
            Prediction.commit_hash == C1, Prediction.model_name == "integration_v2"
        )).all()
        assert len(saved) == 1
        assert float(saved[0].risk_score) == predicted["risk_score"]
        assert saved[0].feature_version == "v1"
        assert saved[0].predicted_at == datetime.fromisoformat(predicted["predicted_at"].removesuffix("Z"))
    detail = client.get(f"/api/commits/{C1}", headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["data"]["risk_score"] == predicted["risk_score"]
    assert detail.json()["data"]["explanation"]
    listing = client.get("/api/commits", headers=HEADERS).json()["data"]
    assert listing["total"] == 2
    match = next(row for row in listing["items"] if row["commit_hash"] == C1)
    assert match["risk_score"] == predicted["risk_score"]


def test_week_month_and_closed_range_match_imported_data(populated_api):
    client, _ = populated_api
    weekly = client.get("/api/trends?granularity=week", headers=HEADERS)
    monthly = client.get("/api/trends?granularity=month", headers=HEADERS)
    assert weekly.status_code == monthly.status_code == 200
    assert weekly.json()["data"]["series"] == [
        {"period": "2026-W31", "commit_count": 2, "avg_risk": 0.5, "high_risk_count": 1}
    ]
    assert monthly.json()["data"]["series"] == [
        {"period": "2026-07", "commit_count": 1, "avg_risk": 0.8, "high_risk_count": 1},
        {"period": "2026-08", "commit_count": 1, "avg_risk": 0.2, "high_risk_count": 0},
    ]
    selected = client.get(
        "/api/commits?start_time=2026-07-27&end_time=2026-08-02", headers=HEADERS
    ).json()["data"]
    assert selected["total"] == 2
    assert [row["commit_hash"] for row in selected["items"]] == [C1, C2]


def test_missing_prediction_and_feature_keep_contract_shapes(populated_api):
    client, _ = populated_api
    unpredicted = client.get(f"/api/commits/{C4}", headers=HEADERS)
    assert unpredicted.status_code == 200
    body = unpredicted.json()["data"]
    assert body["risk_score"] is None
    assert body["model_name"] is None
    assert body["explanation"] == []
    assert set(body["features"]) == set(FEATURE_VALUES)
    missing = client.get(f"/api/commits/{C3}", headers=HEADERS)
    assert missing.status_code == 200
    assert missing.json()["data"]["features"] is None
    response = client.post("/api/predict", headers=HEADERS, json={"commit_hash": C3})
    assert response.status_code == 404
    assert response.json()["code"] == 40400
    assert response.json()["message"] == "features not found for this commit"


def test_empty_database_queries_are_not_errors(integration_db):
    with TestClient(create_app()) as client:
        listing = client.get("/api/commits", headers=HEADERS)
        trends = client.get("/api/trends", headers=HEADERS)
        assert listing.status_code == trends.status_code == 200
        assert listing.json()["data"]["items"] == []
        assert listing.json()["data"]["total"] == 0
        assert trends.json()["data"]["series"] == []


def test_auth_validation_and_failed_load_do_not_leak(populated_api, caplog):
    client, _ = populated_api
    for method, path, payload in (
        ("GET", "/api/commits", None), ("GET", f"/api/commits/{C1}", None),
        ("GET", "/api/trends", None), ("POST", "/api/predict", {"commit_hash": C1}),
    ):
        response = client.request(method, path, json=payload)
        assert response.status_code == 401
        assert response.json()["code"] == 40100
    for method, path, payload in (
        ("GET", "/api/commits?size=101", None),
        ("GET", f"/api/commits/{'z' * 40}", None),
        ("POST", "/api/predict", {"commit_hash": "z" * 40}),
    ):
        response = client.request(method, path, headers=HEADERS, json=payload)
        assert response.status_code == 400
        assert response.json()["code"] == 40001
    for model in config.MODEL_DIR.glob("*.pkl"):
        model.write_bytes(b"broken fixture")
    model_registry.load_models()
    response = client.post("/api/predict", headers=HEADERS, json={"commit_hash": C1})
    assert response.status_code == 500
    assert response.json() == {"code": 50000, "message": "internal error", "data": None}
    assert "failed models: ['integration_v1', 'integration_v2']" in caplog.text
    for forbidden in (str(config.MODEL_DIR), ".pkl", "Traceback", "SELECT", "failed models"):
        assert forbidden not in response.text
