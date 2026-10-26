import os
import subprocess

from sqlalchemy import func, select

from app import config, model_registry
from app.db import SessionLocal
from app.models import Commit, CommitFeature, Prediction
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


def test_predict_new_git_commit_extracts_and_persists_features(client, tmp_path, monkeypatch):
    repo = tmp_path / "camel"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    source = repo / "src" / "A.java"
    source.parent.mkdir()
    source.write_text("class A {}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    env = os.environ.copy()
    env.update(GIT_AUTHOR_DATE="2026-01-01T12:00:00+0000", GIT_COMMITTER_DATE="2026-01-01T12:00:00+0000")
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Example", "-c", "user.email=test@example.org",
         "commit", "-m", "CAMEL-123 fix test"],
        check=True, capture_output=True, env=env,
    )
    commit_hash = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    monkeypatch.setattr(config, "SOURCE_REPO", repo)

    first = client.post("/api/predict", json={"commit_hash": commit_hash}, headers=HEADERS)
    assert first.status_code == 200
    assert first.json()["data"]["features"]["fix"] == 1
    assert set(first.json()["data"]["features"]) == set(FEATURE_VALUES)
    second = client.post("/api/predict", json={"commit_hash": commit_hash}, headers=HEADERS)
    assert second.status_code == 200
    assert _rows_for(commit_hash, "fixture_v2") == 1
    with SessionLocal() as session:
        assert session.query(Commit).filter_by(commit_hash=commit_hash).count() == 1
        assert session.query(CommitFeature).filter_by(commit_hash=commit_hash).count() == 1
    detail = client.get(f"/api/commits/{commit_hash}", headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["data"]["risk_score"] is not None
    listed = client.get("/api/commits", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    assert commit_hash in {item["commit_hash"] for item in listed["data"]["items"]}


def test_predict_source_unavailable_is_sanitized_50000(client, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOURCE_REPO", tmp_path / "missing")
    resp = client.post("/api/predict", json={"commit_hash": C3}, headers=HEADERS)
    assert resp.status_code == 500
    assert resp.json()["code"] == 50000
    assert str(tmp_path) not in resp.json()["message"]


def test_predict_uppercase_hash_uses_normalized_key(client):
    resp = client.post("/api/predict", json={"commit_hash": C1.upper()}, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["data"]["commit_hash"] == C1
    # 大写与小写必须落在同一个 (commit_hash, model_name) 键上：库里只留一行、且是小写哈希。
    # 注意：MySQL 默认 utf8mb4_0900_ai_ci 排序规则下 `=` 比较大小写不敏感，
    # 「按大写查得 0 行」这种大小写敏感断言在 MySQL 上永远不成立（SQLite 上才成立），
    # 故用 BINARY 比较单独验大写不落行、再验落库值全为小写。
    client.post("/api/predict", json={"commit_hash": C1}, headers=HEADERS)
    assert _rows_for(C1, "fixture_v2") == 1
    with SessionLocal() as session:
        upper_rows = session.execute(
            select(func.count()).select_from(Prediction).where(
                func.binary(Prediction.commit_hash) == C1.upper(),
                Prediction.model_name == "fixture_v2",
            )
        ).scalar_one()
        stored = session.execute(
            select(Prediction.commit_hash).where(
                Prediction.commit_hash == C1, Prediction.model_name == "fixture_v2"
            )
        ).scalars().all()
    assert upper_rows == 0, "大写哈希不得单独落一行"
    assert stored and all(h == h.lower() for h in stored), "落库哈希必须归一化为小写"
