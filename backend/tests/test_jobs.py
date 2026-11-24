"""W2 persistence contracts, using only the standard jit_test engine/client."""
from __future__ import annotations

import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest
from app.db import SessionLocal
from app.errors import AppError
from app.models import Job
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.conftest import HEADERS

KINDS = ("collect", "clean", "train", "predict_batch", "evaluate", "explain")
STATES = ("queued", "running", "success", "failed", "cancelled")


@pytest.fixture(autouse=True)
def job_client(engine, request, monkeypatch, tmp_path):
    assert engine.url.database in {"jit_test", "jit_test_w2_validation_447e6b8c"}, "Job tests require an explicitly designated test database"
    from app import config
    from app.services import figure_store

    monkeypatch.setattr(config, "FIGURES_DIR", tmp_path / "figures")
    monkeypatch.setattr(figure_store, "sync_figures", lambda: None)
    monkeypatch.setattr(config, "SYNC_ON_STARTUP", False)
    with Session(engine) as session:
        original_ids = set(session.scalars(select(Job.job_id)))
    client = request.getfixturevalue("client")
    # Coordinator wires main.py; until then register only on this fixture's app.
    if importlib.util.find_spec("app.api.jobs") and "/api/jobs" not in client.app.openapi()["paths"]:
        from app.api.jobs import router
        client.app.include_router(router)
    yield client
    with Session(engine) as session:
        ids = set(session.scalars(select(Job.job_id))) - original_ids
        if ids:
            session.query(Job).filter(Job.job_id.in_(ids)).delete(synchronize_session=False)
            session.commit()


def store():
    from app.services import job_store
    return job_store


def queued(kind="collect", params=None, total=3):
    with SessionLocal() as session:
        return store().create(session, kind, params=params, total=total)


def running(kind="collect", params=None):
    job = queued(kind, params)
    with SessionLocal() as session:
        return store().start(session, job["job_id"], attempt=0)


def failed(kind="collect", params=None):
    job = running(kind, params)
    with SessionLocal() as session:
        return store().fail(session, job["job_id"], attempt=0, error=AppError(40001, "invalid input"))


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("status", STATES)
def test_six_kinds_five_states_detail(job_client, kind, status):
    job = queued(kind, {"model_names": ["fixture_v1"]})
    with SessionLocal() as session:
        if status != "queued":
            store().start(session, job["job_id"], attempt=0)
        if status == "success":
            store().finish(session, job["job_id"], attempt=0, output_ref={"module": kind, "files": ["result.csv"]})
        elif status == "failed":
            store().fail(session, job["job_id"], attempt=0, error=AppError(40001, "invalid input"))
        elif status == "cancelled":
            store().cancel(session, job["job_id"])
    response = job_client.get(f"/api/jobs/{job['job_id']}", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["kind"], data["status"]) == (kind, status)
    assert data["params_json"] == {"model_names": ["fixture_v1"]}
    assert data["created_at"].endswith("Z")
    if status != "queued":
        assert data["started_at"].endswith("Z")
    if status in ("success", "failed", "cancelled"):
        assert data["finished_at"].endswith("Z")
    if status == "success":
        assert data["output_ref_json"]["files"] == ["result.csv"]


def test_list_filters_pagination_and_stable_order(job_client):
    jobs = [queued("collect"), queued("train"), queued("collect")]
    with SessionLocal() as session:
        session.query(Job).update({Job.created_at: datetime(2026, 1, 1)}, synchronize_session=False)
        session.commit()
    data = job_client.get("/api/jobs", params={"size": 2}, headers=HEADERS).json()["data"]
    assert (data["total"], data["page"], data["size"]) == (3, 1, 2)
    assert [j["job_id"] for j in data["items"]] == sorted(j["job_id"] for j in jobs)[:2]
    filtered = job_client.get("/api/jobs?kind=collect&status=queued", headers=HEADERS).json()["data"]
    assert filtered["total"] == 2
    assert len(job_client.get("/api/jobs?page=2&size=2", headers=HEADERS).json()["data"]["items"]) == 1
    with SessionLocal() as session:
        session.query(Job).filter(Job.job_id == jobs[1]["job_id"]).update({Job.created_at: datetime(2026, 2, 1)})
        session.commit()
    assert job_client.get("/api/jobs", headers=HEADERS).json()["data"]["items"][0]["job_id"] == jobs[1]["job_id"]


@pytest.mark.parametrize("query", ["kind=storage", "kind=localize", "kind=TRAIN", "status=unknown", "status=RUNNING", "page=0", "page=x", "size=0", "size=101"])
def test_invalid_list_filters(job_client, query):
    response = job_client.get("/api/jobs?" + query, headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == 40001


@pytest.mark.parametrize("method,path", [("get", "/api/jobs"), ("get", "/api/jobs/missing"), ("post", "/api/jobs/missing/retry"), ("post", "/api/jobs/missing/cancel")])
def test_auth(job_client, method, path):
    assert getattr(job_client, method)(path).json()["code"] == 40100
    assert getattr(job_client, method)(path, headers={"X-API-Key": "wrong"}).status_code == 401


@pytest.mark.parametrize("suffix", ["", "/retry", "/cancel"])
def test_missing_and_output_ids_are_not_jobs(job_client, suffix):
    response = (job_client.post if suffix else job_client.get)("/api/jobs/storage-batch-id" + suffix, headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["code"] == 40400


def test_retry_preserves_snapshot_and_does_not_execute(job_client):
    job = running(params={"predict": {"retry_max": 2}, "line": "expert"})
    with SessionLocal() as session:
        store().update_progress(session, job["job_id"], attempt=0, done=2, current_item="abc")
        store().fail(session, job["job_id"], attempt=0, error=AppError(40001, "bad input"), output_ref={"files": ["old.csv"]})
    response = job_client.post(f"/api/jobs/{job['job_id']}/retry", headers=HEADERS)
    assert response.json()["data"] == {"job_id": job["job_id"], "status": "queued", "retry_count": 1}
    data = job_client.get(f"/api/jobs/{job['job_id']}", headers=HEADERS).json()["data"]
    assert data["params_json"] == job["params_json"]
    assert data["done"] == 2 and data["output_ref_json"] == {"files": ["old.csv"]}
    assert data["started_at"] is None and data["finished_at"] is None
    with SessionLocal() as session:
        store().start(session, job["job_id"], attempt=1)
        store().fail(session, job["job_id"], attempt=1, error=RuntimeError("secret exception"))
        store().retry(session, job["job_id"])
    assert job_client.get(f"/api/jobs/{job['job_id']}", headers=HEADERS).json()["data"]["retry_count"] == 2


@pytest.mark.parametrize("operation", ["retry", "cancel"])
def test_mutation_rejects_override_body_and_query(job_client, operation):
    job = failed() if operation == "retry" else queued()
    for options in ({"json": {"params_json": {"line": "fused"}}}, {"params": {"line": "fused"}}):
        response = job_client.post(f"/api/jobs/{job['job_id']}/{operation}", headers=HEADERS, **options)
        assert response.json()["code"] == 40001


@pytest.mark.parametrize("status", ["queued", "running", "success", "cancelled"])
def test_retry_rejects_every_nonfailed_state(job_client, status):
    job = queued()
    with SessionLocal() as session:
        if status != "queued":
            store().start(session, job["job_id"], attempt=0)
        if status == "success":
            store().finish(session, job["job_id"], attempt=0)
        elif status == "cancelled":
            store().cancel(session, job["job_id"])
    assert job_client.post(f"/api/jobs/{job['job_id']}/retry", headers=HEADERS).json()["code"] == 40001


@pytest.mark.parametrize("initial", ["queued", "running"])
def test_cancel_atomic_and_late_worker_blocked(job_client, initial):
    job = queued() if initial == "queued" else running()
    response = job_client.post(f"/api/jobs/{job['job_id']}/cancel", headers=HEADERS)
    assert response.json()["data"]["status"] == "cancelled"
    with SessionLocal() as session:
        for fn, kwargs in [(store().finish, {}), (store().update_progress, {"done": 3}), (store().fail, {"error": RuntimeError("late")})]:
            with pytest.raises(AppError) as exc:
                fn(session, job["job_id"], attempt=0, **kwargs)
            assert exc.value.code == 40001
    assert job_client.post(f"/api/jobs/{job['job_id']}/cancel", headers=HEADERS).json()["code"] == 40001
    data = job_client.get(f"/api/jobs/{job['job_id']}", headers=HEADERS).json()["data"]
    assert data["status"] == "cancelled" and data["done"] == 0


@pytest.mark.parametrize("terminal", ["success", "failed"])
def test_cancel_rejects_terminal(job_client, terminal):
    job = running()
    with SessionLocal() as session:
        if terminal == "success":
            store().finish(session, job["job_id"], attempt=0)
        else:
            store().fail(session, job["job_id"], attempt=0, error=RuntimeError())
    assert job_client.post(f"/api/jobs/{job['job_id']}/cancel", headers=HEADERS).json()["code"] == 40001


def test_attempt_token_blocks_old_worker_after_retry(job_client):
    job = failed()
    with SessionLocal() as session:
        store().retry(session, job["job_id"])
        store().start(session, job["job_id"], attempt=1)
        for fn, kwargs in [(store().finish, {}), (store().update_progress, {"done": 3}), (store().fail, {"error": RuntimeError()})]:
            with pytest.raises(AppError) as exc:
                fn(session, job["job_id"], attempt=0, **kwargs)
            assert exc.value.code == 40001
        assert store().get(session, job["job_id"])["status"] == "running"


def test_same_kind_simultaneous_starts_independent_sessions(job_client, engine):
    jobs = [queued("train"), queued("train")]
    gate = Barrier(2)
    def start(job):
        with Session(engine) as session:
            assert session.scalar(text("SELECT @@transaction_isolation")) == "REPEATABLE-READ"
            gate.wait(timeout=10)
            try:
                return store().start(session, job["job_id"], attempt=0)["status"]
            except AppError as exc:
                return exc.code
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(start, jobs))
    assert sorted(map(str, results)) == ["40001", "running"]
    with Session(engine) as session:
        assert len(session.scalars(select(Job).where(Job.status == "running")).all()) == 1


def test_current_reads_ignore_stale_rr_identity_map(job_client, engine):
    first, second = queued("train"), queued("train")
    with Session(engine) as stale, Session(engine) as fresh:
        cached = stale.get(Job, first["job_id"])
        assert cached.status == "queued"
        store().start(fresh, first["job_id"], attempt=0)
        with pytest.raises(AppError) as exc:
            store().start(stale, second["job_id"], attempt=0)
        assert exc.value.code == 40001
    job = running("clean")
    with Session(engine) as stale, Session(engine) as fresh:
        stale.get(Job, job["job_id"])
        store().cancel(fresh, job["job_id"])
        with pytest.raises(AppError):
            store().update_progress(stale, job["job_id"], attempt=0, done=1)


def test_retry_kind_conflict(job_client):
    job = failed("train")
    running("train")
    response = job_client.post(f"/api/jobs/{job['job_id']}/retry", headers=HEADERS)
    assert response.status_code == 400 and response.json()["code"] == 40001


@pytest.mark.parametrize("number", [1213, 1205])
def test_mysql_lock_errors_are_conflicts_and_rollback(job_client, engine, monkeypatch, number):
    job = queued()
    with Session(engine) as session:
        scalars = session.scalars
        def fail_lock(statement, *args, **kwargs):
            if getattr(statement, "_for_update_arg", None) is not None:
                raise OperationalError("lock", {}, Exception(number, "sensitive database details"))
            return scalars(statement, *args, **kwargs)
        monkeypatch.setattr(session, "scalars", fail_lock)
        with pytest.raises(AppError) as exc:
            store().start(session, job["job_id"], attempt=0)
        assert exc.value.code == 40001 and not session.in_transaction()


def test_real_engine_recreation_preserves_jobs(job_client, engine):
    job = running("evaluate", {"dataset_id": "registered-id"})
    with SessionLocal() as session:
        store().update_progress(session, job["job_id"], attempt=0, total=7, done=2, current_item="metric")
    recreated = create_engine(engine.url, pool_pre_ping=True)
    try:
        with Session(recreated) as session:
            data = store().get(session, job["job_id"])
            assert data["done"] == 2 and data["total"] == 7 and data["status"] == "running"
    finally:
        recreated.dispose()


def test_startup_recovery_preserves_progress_retry_and_success(job_client):
    interrupted = failed("train")
    with SessionLocal() as session:
        store().retry(session, interrupted["job_id"])
        store().start(session, interrupted["job_id"], attempt=1)
        store().update_progress(session, interrupted["job_id"], attempt=1, done=2)
    completed = running("collect")
    with SessionLocal() as session:
        store().finish(session, completed["job_id"], attempt=0)
        assert store().recover_running(session) == 1
        data = store().get(session, interrupted["job_id"])
        assert (data["status"], data["done"], data["retry_count"]) == ("failed", 2, 1)
        assert data["error_log"] == "进程重启中断"
        assert store().get(session, completed["job_id"])["status"] == "success"
        assert store().recover_running(session) == 0


def test_oversized_unicode_snapshot_is_rejected_atomically(job_client):
    with SessionLocal() as session:
        with pytest.raises(AppError) as rejected:
            store().create(session, "train", params={"note": "中" * 22000})
        assert rejected.value.code == 40001
        assert session.scalars(select(Job)).all() == []


def test_secret_assignments_in_snapshot_values_are_redacted(job_client):
    job = queued(params={"note": "password:super-secret-value", "authorization_note": "drop this field"})
    encoded = json.dumps(job["params_json"])
    assert "super-secret-value" not in encoded
    assert "drop this field" not in encoded


@pytest.mark.parametrize("name", ["credential", "private_key"])
def test_all_secret_key_assignments_are_redacted(job_client, name):
    job = queued(params={"note": name + "=opaque-sensitive-value"})
    assert "opaque-sensitive-value" not in json.dumps(job["params_json"])
    job = running("train")
    with SessionLocal() as session:
        result = store().fail(session, job["job_id"], attempt=0, error=AppError(40001, name + ":opaque-sensitive-value"))
    assert "opaque-sensitive-value" not in result["error_log"]


def test_params_outputs_and_errors_sanitized_before_storage(job_client):
    params = {"api_key": "top-secret", "nested": {"LLM_KEY": "llm-secret", "password": "pw-secret"}, "repo_url": "https://user:url-secret@example.com/repo?token=query-secret&branch=main", "path": "/Users/private/data.csv", "windows": "C:\\private\\data.csv", "relative": "../../private", "line": "expert"}
    job = running(params=params)
    with SessionLocal() as session:
        store().fail(session, job["job_id"], attempt=0, error=RuntimeError("unexpected-secret /Users/private/file mysql://user:pw@host"), output_ref={"module": "collect", "files": ["result.csv", "/etc/passwd", "../escape.csv"], "password": "output-secret"})
        persisted = session.get(Job, job["job_id"])
        raw = str((persisted.params_json, persisted.output_ref_json, persisted.error_log))
        for secret in ("top-secret", "llm-secret", "pw-secret", "url-secret", "query-secret", "unexpected-secret", "output-secret", "/Users/private", "/etc/passwd", "../escape", "C:\\private"):
            assert secret not in raw
        assert persisted.error_log == "internal error"
        assert json.loads(persisted.params_json)["repo_url"] == "https://example.com/repo?branch=main"
        assert json.loads(persisted.output_ref_json)["files"][0] == "result.csv"


def test_expected_error_is_sanitized_and_bounded(job_client):
    job = running()
    with SessionLocal() as session:
        data = store().fail(session, job["job_id"], attempt=0, error=AppError(40001, "api_key=credential /Users/private/file https://user:password@example.com/repo " + "x" * 5000))
        assert "credential" not in data["error_log"] and "password" not in data["error_log"]
        assert "/Users/private" not in data["error_log"] and len(data["error_log"]) <= 2000


def test_sync_snapshot_is_latest_origin_job_and_persisted(job_client, engine):
    from app.services import sync_state
    token = sync_state.set_state(running=True, mode="manual", scope="latest", phase="plan", line="expert", model_name="fixture_v1", start_time="2026-01-01", end_time="2026-02-01")
    sync_state.set_state(total=4, done=1, current_hash="a" * 40, phase="predict")
    with Session(engine) as session:
        rows = session.scalars(select(Job)).all()
        assert len(rows) == 1
        params = json.loads(rows[0].params_json)
        assert params["origin"] == "sync" and params["line"] == "expert" and params["start_time"] == "2026-01-01"
        assert rows[0].kind == "predict_batch" and rows[0].done == 1
    sync_state.set_state(running=False, phase=None)
    queued("predict_batch", {"origin": "other"})
    assert sync_state.get_sync_state()["done"] == 1
    assert sync_state.get_sync_state()["running"] is False
    assert token[1] == 0


def test_sync_premark_worker_reuses_job_and_loser_cannot_finish_winner(job_client, monkeypatch):
    from app.api import sync
    from app.services import sync_state
    captured = []
    spawn_worker = sync._spawn_sync_worker
    monkeypatch.setattr(sync, "_spawn_sync_worker", lambda fn, **kwargs: captured.append((fn, kwargs)))
    response = job_client.post("/api/sync?line=expert&start_time=2026-01-01", headers=HEADERS)
    assert response.json()["data"] == {"accepted": True}
    fn, kwargs = captured[0]
    assert kwargs["job_id"]
    with pytest.raises(AppError):
        sync_state.begin_sync({"mode": "manual", "scope": "latest"})
    assert sync_state.get_sync_state()["running"] is True
    monkeypatch.setattr(sync.config, "SOURCE_REPO", None)
    from types import SimpleNamespace

    class ImmediateThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(sync, "threading", SimpleNamespace(Thread=ImmediateThread))
    spawn_worker(fn, **kwargs)
    with SessionLocal() as session:
        rows = session.scalars(select(Job)).all()
        assert len(rows) == 1 and rows[0].status == "failed"
        assert json.loads(rows[0].params_json)["start_time"].startswith("2026-01-01")


def test_sync_cancel_checked_before_more_predictions(job_client, monkeypatch, tmp_path):
    from app.api import sync
    from app.services import sync_state
    repo = tmp_path / "source"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync.config, "SOURCE_REPO", repo)
    monkeypatch.setattr(sync.config, "SYNC_FETCH", False)
    monkeypatch.setattr(sync, "run_git", lambda *args: "a" * 40)
    monkeypatch.setattr(sync, "ensure_extractable", lambda *args: (repo, lambda: None))
    monkeypatch.setattr(sync, "_prefetch_features", lambda *args: 0)
    writes = []
    def predict(commit_hash, *args):
        writes.append(commit_hash)
        job_id, attempt = sync_state.current_attempt()
        with SessionLocal() as session:
            store().cancel(session, job_id)
    monkeypatch.setattr(sync, "_predict_commit_models", predict)
    with pytest.raises(AppError):
        sync._run_batch(mode="manual", scope="latest", models=set(), plan=lambda *args: (2, ["a" * 40, "b" * 40], None))
    assert writes == ["a" * 40]
    with SessionLocal() as session:
        assert session.scalar(select(Job.status)) == "cancelled"


def test_health_db_down_safe_persisted_last_sync(job_client, monkeypatch):
    from app.services import health, sync_state
    sync_state.set_state(running=True, mode="manual")
    sync_state.set_state(running=False)
    assert job_client.get("/api/health", headers=HEADERS).json()["data"]["last_sync_at"].endswith("Z")
    def broken():
        raise RuntimeError("mysql://user:password@host /Users/private")
    monkeypatch.setattr(health, "SessionLocal", broken)
    monkeypatch.setattr(sync_state, "SessionLocal", broken)
    response = job_client.get("/api/health", headers=HEADERS)
    assert response.json()["data"]["db"] == "down"
    assert response.json()["data"]["last_sync_at"] is None
    assert "password" not in response.text and "/Users/private" not in response.text
