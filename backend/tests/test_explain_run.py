"""AI-generated W8 tests; not human-reviewed."""

import importlib.util
import io
import json
import os
import sys
from pathlib import Path

import joblib
import pytest
from app import db, model_registry
from app.models import Base, Prediction
from app.services import file_contracts as fc
from app.services import output_store

from tests.conftest import C1, FAKE_EXTRACTOR, HEADERS
from tests.test_clean_api import source_rows
from tests.test_models_manage import lr_package


def service():
    assert importlib.util.find_spec("app.services.explain_run") is not None, (
        "independent explain service is missing"
    )
    from app.services import explain_run

    return explain_run


def test_required_service_exists():
    assert callable(service().run_files)


def test_file_explain_without_predictions_safe_and_cache(tmp_path):
    mod = service()
    name, version, raw = lr_package()
    rows = source_rows()
    table = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows, "csv")
    prepared = mod.prepare_files(
        {"techniques": ["shap", "lime"], "top_n": 3}, [("model.zip", raw), ("commits.csv", table)]
    )
    registry_before = dict(model_registry._REGISTRY)
    first = mod.run_files(prepared)
    second = mod.run_files(prepared)
    assert first["summary"]["input_rows"] == len(rows)
    assert first["summary"]["success_count"] == len(rows) * 2
    assert second["summary"]["cache_hits"] == len(rows) * 2
    assert model_registry._REGISTRY == registry_before
    assert {r["technique"] for r in first["rows"]} == {"shap", "lime"}
    assert all(r["rank"] in (1, 2, 3) and r["model_version"] for r in first["rows"])
    assert all(
        r["direction"]
        == (
            "increase"
            if r["contribution"] > 0
            else "decrease"
            if r["contribution"] < 0
            else "neutral"
        )
        for r in first["rows"]
    )
    assets = mod.artifacts(first, "test-batch")
    columns, exported = fc.read_table(
        "explain_explanations_test-batch.xlsx", assets["explain_explanations_test-batch.xlsx"]
    )
    assert columns == list(mod.COLUMNS) and len(exported) == len(first["rows"])
    assert assets["explain_explanations_test-batch.csv"].startswith(b"\xef\xbb\xbf")
    assert assets["explain_contributions_test-batch.png"].startswith(b"\x89PNG")
    invalid = dict(prepared)
    invalid["config"] = dict(
        prepared["config"],
        params={"shap": {"background_size": 2}, "lime": prepared["config"]["params"]["lime"]},
    )
    changed = mod.run_files(invalid)
    assert changed["summary"]["cache_hits"] == len(rows)


def test_sandbox_does_not_read_other_user_files(tmp_path):
    mod = service()
    secret = tmp_path / "protected.txt"
    secret.write_text("private content")

    class ReadFile:
        def __reduce__(self):
            return (Path.read_text, (secret,))

    buf = io.BytesIO()
    joblib.dump(ReadFile(), buf)
    result = mod.isolated_results(
        buf.getvalue(),
        [{"commit_hash": "a" * 40, "features": [0] * 14}],
        ["shap"],
        {"shap": {"background_size": 1}},
        8,
    )
    assert all(item["reason_code"] == "explainer_failed" for item in result)
    assert "private content" not in json.dumps(result)


@pytest.mark.parametrize(
    "config",
    [
        {"techniques": []},
        {"techniques": ["unknown"]},
        {"techniques": ["shap", "shap"]},
        {"techniques": ["lime"], "params": {"lime": {"num_samples": True}}},
        {"techniques": ["shap"], "top_n": 0},
        {"techniques": ["shap"], "cache_ttl": -1},
        {"techniques": ["shap"], "unknown": 1},
    ],
)
def test_invalid_config(config):
    with pytest.raises((ValueError, fc.AppError)):
        service().validate_config(config)


def test_sandbox_blocks_external_shared_tmp_contents(tmp_path):
    """跨平台：任务目录之外的临时文件内容不得被上传权重读取。"""
    mod = service()
    shared = tmp_path / "shared.dat"
    shared.write_bytes(b"protected shared data")

    class ReadShared:
        def __reduce__(self):
            return (Path.read_bytes, (shared,))

    buffer = io.BytesIO()
    joblib.dump(ReadShared(), buffer)
    result = mod.isolated_results(
        buffer.getvalue(),
        [{"commit_hash": "a" * 40, "features": [0] * 14}],
        ["shap"],
        {"shap": {"background_size": 1}},
        8,
    )
    assert result[0]["reason_code"] == "explainer_failed"
    assert "protected shared data" not in json.dumps(result)


def test_worker_timeout_kills_group_and_returns_reason(monkeypatch):
    mod = service()
    calls = []

    class Worker:
        pid = 998811
        returncode = None

        def poll(self):
            return None

        def wait(self, timeout=None):
            self.returncode = -9
            return -9

    monkeypatch.setattr(mod.subprocess, "Popen", lambda *a, **kw: Worker())
    clock = iter([0, 121])
    monkeypatch.setattr(mod.time, "monotonic", lambda: next(clock))
    if os.name == "nt":
        monkeypatch.setattr(mod, "_kill_process_group", lambda pid: calls.append(pid))
    else:
        monkeypatch.setattr(mod.os, "killpg", lambda pid, signal: calls.append(pid))
    result = mod.isolated_results(
        b"bad",
        [{"commit_hash": "a" * 40, "features": [0] * 14}],
        ["shap"],
        {"shap": {"background_size": 1}},
        8,
    )
    assert calls == [998811]
    assert result[0]["reason_code"] == "execution_limit_exceeded"


@pytest.mark.parametrize("oversized", [False, True])
def test_invalid_worker_output_and_fast_exit_limit(monkeypatch, oversized):
    mod = service()

    class Worker:
        returncode = 0

        def poll(self):
            return 0

    def launch(*args, **kwargs):
        kwargs["stdout"].write(
            json.dumps([{"commit_hash": "a" * 40, "technique": "shap", "items": []}]).encode()
        )
        kwargs["stdout"].flush()
        return Worker()

    monkeypatch.setattr(mod.subprocess, "Popen", launch)
    if oversized:
        monkeypatch.setattr(mod, "MAX_WORKER_BYTES", 8, raising=False)
    result = mod.isolated_results(
        b"bad",
        [{"commit_hash": "a" * 40, "features": [0] * 14}],
        ["shap"],
        {"shap": {"background_size": 1}},
        8,
    )
    assert result[0]["reason_code"] == (
        "execution_limit_exceeded" if oversized else "invalid_worker_output"
    )


def test_manifest_optional_predictions_checksums_and_ranges(tmp_path):
    mod = service()
    name, version, raw = lr_package()
    table = fc.encode_table(fc.COMMITS_COLUMNS, source_rows(), "csv")
    bad_manifest = b'{"not":"manifest"}'
    with pytest.raises((ValueError, fc.AppError)):
        mod.prepare_files(
            {"techniques": ["shap"]},
            [("model.zip", raw), ("commits.csv", table), ("commits.manifest.json", bad_manifest)],
        )
    predictions = [
        {
            "commit_hash": "a" * 40,
            "model_name": name,
            "risk_score": 0.7,
            "predicted_label": 1,
            "decision_threshold": 0.5,
            "model_version": "mismatch",
            "feature_version": "v1",
            "predicted_at": "2026-01-01T00:00:00Z",
            "is_bug_inducing": "",
        }
    ]
    with pytest.raises((ValueError, fc.AppError)):
        mod.prepare_files(
            {"techniques": ["shap"]},
            [
                ("model.zip", raw),
                ("commits.csv", table),
                ("predictions.csv", fc.encode_table(fc.PREDICTIONS_COLUMNS, predictions, "csv")),
            ],
        )


@pytest.fixture
def explain_client(engine, tmp_path, monkeypatch):
    from app.main import create_app
    from fastapi.testclient import TestClient

    mod = service()
    with db.SessionLocal() as session:
        assert session.bind.url.database in {"jit_test", "jit_test_w2_validation_447e6b8c"}
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    monkeypatch.setattr(mod, "REQUEST_ROOT", tmp_path / "requests")
    monkeypatch.setattr(mod, "dispatch", lambda: None)
    monkeypatch.setattr(output_store, "OUTPUT_ROOT", tmp_path / "outputs")
    with TestClient(create_app()) as client:
        yield client, mod, tmp_path


def submit(client):
    _, _, raw = lr_package()
    return client.post(
        "/api/explain/run",
        data={"config": json.dumps({"techniques": ["shap"], "top_n": 4})},
        files=[
            ("files[]", ("model.zip", raw)),
            ("files[]", ("collected_commits.csv", fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, source_rows(), "csv"))),
        ],
        headers=HEADERS,
    )


def test_explain_api_with_empty_business_tables(explain_client):
    client, mod, _ = explain_client
    listed = client.get("/api/explain/techniques", headers=HEADERS)
    assert listed.status_code == 200 and {
        t["key"] for t in listed.json()["data"]["techniques"]
    } == {"shap", "lime"}
    response = submit(client)
    assert response.status_code == 200 and response.json()["data"]["status"] == "success", (
        response.text
    )
    result = response.json()["data"]
    assert result["summary"]["success_count"] == 4
    for item in result["outputs"]:
        url = f"/api/explain/outputs/{result['job_id']}/{item['name']}"
        assert client.get(url).status_code == 401
        blob = client.get(url, headers=HEADERS)
        assert blob.status_code == 200 and fc.sha256(blob.content) == item["sha256"]
    with db.SessionLocal() as session:
        assert session.query(Prediction).count() == 0


def test_null_techniques_are_rejected_before_run(explain_client):
    client, _, _ = explain_client
    response = client.post(
        "/api/explain/run", data={"config": json.dumps({"techniques": None})}, headers=HEADERS
    )
    assert response.status_code == 400 and response.json()["code"] == 40001


def test_compare_disabled_and_lime_default_are_persisted(explain_client):
    client, _, _ = explain_client
    assert (
        client.put("/api/config/default_xai", json={"value": "lime"}, headers=HEADERS).status_code
        == 200
    )
    assert (
        client.get("/api/explain/techniques", headers=HEADERS).json()["data"]["default_technique"]
        == "lime"
    )
    assert (
        client.put(
            "/api/config/explain.compare_enabled", json={"value": False}, headers=HEADERS
        ).status_code
        == 200
    )
    response = client.post(
        "/api/explain/run",
        data={"config": json.dumps({"techniques": ["shap", "lime"]})},
        headers=HEADERS,
    )
    assert response.status_code == 400


def test_cancel_retries_snapshot_and_body_limits(explain_client, monkeypatch):
    client, mod, path = explain_client
    monkeypatch.setattr(mod, "SYNC_MAX_ROWS", 1)
    response = submit(client)
    assert response.status_code == 200 and response.json()["data"]["status"] == "queued"
    job_id = response.json()["data"]["job_id"]
    original = mod.run_files
    monkeypatch.setattr(
        mod, "run_files", lambda *a, **kw: (_ for _ in ()).throw(fc.AppError(40001, "test failure"))
    )
    mod._execute(job_id, 0)
    assert client.get("/api/jobs/" + job_id, headers=HEADERS).json()["data"]["status"] == "failed"
    called = []
    monkeypatch.setattr(mod, "dispatch", lambda: called.append(True))
    assert (
        client.post("/api/jobs/" + job_id + "/retry", headers=HEADERS).json()["data"]["retry_count"]
        == 1
    )
    assert called == [True]
    monkeypatch.setattr(mod, "run_files", original)
    client.post("/api/jobs/" + job_id + "/cancel", headers=HEADERS)
    mod._execute(job_id, 1)
    assert not (path / "outputs" / job_id).exists()


def test_cli_explain_is_database_independent(tmp_path):
    import os
    import subprocess

    name, _, raw = lr_package()
    package = tmp_path / "model.zip"
    package.write_bytes(raw)
    table = tmp_path / "collected_commits.csv"
    table.write_bytes(fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, source_rows(), "csv"))
    env = {
        **os.environ,
        "DB_HOST": "",
        "DATABASE_URL": "",
        "FEATURE_EXTRACTOR_SCRIPT": str(FAKE_EXTRACTOR),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "explain",
            "run",
            "--model-package",
            str(package),
            "--input",
            str(table),
            "--technique",
            "lime",
            "--top-n",
            "4",
            "--out",
            str(tmp_path / "out"),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["summary"]["success_count"] == 4
    files = tmp_path / "out" / data["job_id"]
    for entry in data["outputs"]:
        assert fc.sha256((files / entry["name"]).read_bytes()) == entry["sha256"]


def test_float_parameter_accepts_json_integer_number():
    assert (
        service().validate_config(
            {"techniques": ["lime"], "params": {"lime": {"kernel_width": 3}}}
        )["params"]["lime"]["kernel_width"]
        == 3.0
    )


def test_prediction_does_not_call_explain(client, monkeypatch):
    from app import explain_core

    monkeypatch.setattr(
        explain_core,
        "explain",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("predict must not explain")),
    )
    response = client.post(
        "/api/predict", json={"commit_hash": C1, "model_name": "fixture_v2"}, headers=HEADERS
    )
    assert response.status_code == 200
    assert "explanation" not in response.json()["data"]
