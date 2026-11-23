# 来源：[AI生成]；尚未人工审核，不作为课程审核完成证据。

from app.db import SessionLocal
from app.main import create_app
from app.models import Job, Model, ModelArtifact
from app.services import job_store
from fastapi.testclient import TestClient

from tests.conftest import HEADERS


def test_main_app_exposes_job_management(client):
    response = client.get("/api/jobs", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_registered_model_metadata_is_not_overwritten_by_startup(client):
    from datetime import datetime
    with SessionLocal() as session:
        model = session.get(Model, "fixture_v1")
        model.algo = "registered-algorithm"
        model.version_key = "registered-version"
        model.feature_version = "registered-features"
        session.add(ModelArtifact(artifact_id="w2-registry-test", model_name="fixture_v1", line="expert",
                                  algo="registered-algorithm", version_key="registered-version",
                                  feature_version="registered-features", weight_path="opaque-package.zip",
                                  checksum_sha256="a" * 64, size_bytes=10, status="available",
                                  created_at=datetime(2026, 11, 22)))
        session.commit()
    with TestClient(create_app()):
        pass
    with SessionLocal() as session:
        model = session.get(Model, "fixture_v1")
        assert model.version_key == "registered-version"
        assert model.feature_version == "registered-features"
        assert model.algo == "registered-algorithm"


def test_upload_auth_is_checked_before_parsing(client):
    response = client.post("/api/storage/import", content=b"malformed multipart", headers={"Content-Type": "multipart/form-data; boundary=missing"})
    assert response.status_code == 401
    assert response.json()["code"] == 40100


def test_upload_total_body_limit_is_checked_before_parsing(client, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "MAX_IMPORT_BODY_BYTES", 10, raising=False)
    response = client.post("/api/storage/import", content=b"x" * 11, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_chunked_upload_is_also_bounded(client, monkeypatch):
    from app import main
    monkeypatch.setattr(main, "MAX_IMPORT_BODY_BYTES", 10, raising=False)
    response = client.post("/api/storage/import", content=iter([b"x" * 6, b"x" * 6]), headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_valid_upload_body_replays_to_the_real_storage_route(client):
    from tests.test_storage_api import ROOT, manifest
    raw = (ROOT / "normal/commits.csv").read_bytes().replace(b"a" * 40, b"e" * 40).replace(b"b" * 40, b"f" * 40)
    response = client.post("/api/storage/import", headers=HEADERS, files=[
        ("files[]", ("commits.csv", raw)),
        ("files[]", ("commits.manifest.json", manifest("commits.csv", raw, feature_version="log-v2"))),
    ], data={"config": "{}"})
    assert response.status_code == 200
    assert response.json()["data"]["summary"]["inserted"] == 2


def test_real_lifespan_recovers_running_jobs(client):
    with SessionLocal() as session:
        job = job_store.create(session, "evaluate", total=4, start_immediately=True)
        job_store.update_progress(session, job["job_id"], attempt=0, done=2)
    with TestClient(create_app()) as restarted:
        response = restarted.get("/api/jobs/" + job["job_id"], headers=HEADERS)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "failed"
        assert data["done"] == 2
        assert data["error_log"] == "进程重启中断"
    with SessionLocal() as session:
        assert session.get(Job, job["job_id"]).status == "failed"
