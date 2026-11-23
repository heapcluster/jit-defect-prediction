"""AI-generated, unreviewed W2 acceptance cases; only jit_test and tmp outputs."""
import csv
import importlib.util
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest
from app import config
from app.db import get_db
from app.errors import register_error_handlers
from app.models import (
    Base,
    Commit,
    CommitFeature,
    Dataset,
    Job,
    Model,
    ModelArtifact,
    Prediction,
    User,
    UserConfig,
)
from app.services import file_contracts as fc
from app.services import output_store
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT = Path(__file__).parent / "fixtures/files/storage"
HEADERS = {"X-API-Key": "test-token"}
A, B = "a" * 40, "b" * 40
CREATE = {"create_dataset": {"name": "AI fixture", "repo_source": "https://example.org/repo.git"}}


def test_required_storage_modules():
    for module in ("app.services.storage", "app.api.storage", "app.api.datasets"):
        assert importlib.util.find_spec(module) is not None, f"missing approved W2 module: {module}"


@pytest.fixture
def storage_client(engine, tmp_path, monkeypatch):
    assert engine.url.database in {"jit_test", "jit_test_w2_validation_447e6b8c"}, "storage tests require an explicitly designated test database"
    with Session(engine) as db:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.add(Model(model_name="fixture", line="expert", algo="rf", version_key="v2", feature_version="log-v2"))
        db.commit()
    monkeypatch.setattr(output_store, "OUTPUT_ROOT", tmp_path)
    from app.api import datasets, storage
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(storage.router)
    app.include_router(datasets.router)
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def manifest(name, raw, **settings):
    return json.dumps({"schema_version": "1.0", "module": "collect", "job_id": "fixture",
                       "inputs": [{"name": "source.json", "sha256": "1" * 64}], "config": settings,
                       "outputs": [{"name": name, "sha256": fc.sha256(raw)}],
                       "code_version": "fixture", "created_at": "2026-11-21T12:00:00Z"}).encode()


def upload(client, files, settings=None):
    return client.post("/api/storage/import", headers=HEADERS,
                       files=[("files[]", (name, raw)) for name, raw in files],
                       data={"config": json.dumps(settings or {})})


def commits(client, settings=CREATE, raw=None):
    raw = raw or (ROOT / "normal/commits.csv").read_bytes()
    return upload(client, [("arbitrary.csv", raw), ("arbitrary.manifest.json", manifest("arbitrary.csv", raw, feature_version="log-v2"))], settings)


def table_bytes(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def package(**changes):
    meta = json.loads((ROOT / "normal/model_meta.json").read_bytes())
    meta.update(changes)
    line = meta["line"]
    order = list(config.FEATURE_COLUMNS) if line == "expert" else ([f"semantic_{i}" for i in range(768)] if line == "semantic" else list(config.FEATURE_COLUMNS) + [f"semantic_{i}" for i in range(768)] if line == "fused" else ["commit_text"])
    members = {"model_meta.json": json.dumps(meta).encode(), "feature_order.txt": "\n".join(order).encode(),
               "weights/model.safetensors" if line == "e2e" else "weights.pkl": b"opaque weight bytes: MUST NOT deserialize"}
    members["checksum.sha256"] = "\n".join(f"{fc.sha256(raw)}  {name}" for name, raw in members.items()).encode()
    return zip_bytes(members)


def zip_bytes(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    return stream.getvalue()


def prediction_rows(**changes):
    row = dict(commit_hash=A, model_name="fixture", risk_score="0.75000", predicted_label="1",
               decision_threshold="0.5", model_version="v2", feature_version="log-v2", predicted_at="2026-11-21T12:00:00Z", is_bug_inducing="")
    row.update(changes)
    return table_bytes(fc.PREDICTIONS_COLUMNS, [row])


def test_commits_idempotent_counts_and_null_preservation(storage_client, engine):
    first = commits(storage_client).json()["data"]
    assert first["items"][0]["inserted"] == 2
    assert set(first["items"][0]["target_tables"]) == {"commit", "commit_feature", "dataset", "dataset_commit"}
    dataset = storage_client.get("/api/datasets", headers=HEADERS).json()["data"]["items"][0]
    assert (dataset["sample_count"], dataset["pos_count"], dataset["neg_count"]) == (2, 1, 0)
    assert commits(storage_client).json()["data"]["items"][0]["unchanged"] == 2
    assert storage_client.get("/api/datasets", headers=HEADERS).json()["data"]["items"] == [dataset]
    columns, rows = fc.read_table("commits.csv", (ROOT / "normal/commits.csv").read_bytes())
    rows[0]["is_bug_inducing"] = ""
    rows[0]["labeled_at"] = ""
    rows[0]["message"] = "updated"
    assert commits(storage_client, raw=table_bytes(columns, rows)).json()["data"]["items"][0]["updated"] == 1
    with Session(engine) as db:
        feature = db.get(CommitFeature, A)
        assert feature.is_bug_inducing == 1 and str(feature.la) == "-4.2720000000"
        assert db.get(CommitFeature, B).is_bug_inducing is None


@pytest.mark.parametrize("case", ["no_manifest", "no_version", "long_version", "bad_date", "bad_hash", "bad_fix", "infinite", "duplicate", "extra", "missing", "long_name", "formula"])
def test_invalid_commits_atomic(storage_client, engine, case):
    columns, rows = fc.read_table("commits.csv", (ROOT / "normal/commits.csv").read_bytes())
    version = "log-v2"
    changes = {"bad_date": ("committed_at", "2026-02-30T12:00:00Z"), "bad_hash": ("commit_hash", "xyz"),
               "bad_fix": ("fix", "2"), "infinite": ("la", "NaN"), "long_name": ("repo_name", "r" * 65),
               "formula": ("message", "=HYPERLINK(1)")}
    if case in changes:
        field, value = changes[case]
        rows[1][field] = value
    if case == "duplicate":
        rows.append(rows[0])
    if case == "extra":
        columns.append("feature_version")
        for row in rows:
            row["feature_version"] = "log-v2"
    if case == "missing":
        columns.remove("is_test")
        for row in rows:
            row.pop("is_test")
    if case == "no_version":
        version = ""
    if case == "long_version":
        version = "v" * 33
    raw = table_bytes(columns, rows)
    files = [("data.csv", raw)]
    if case != "no_manifest":
        files.append(("data.manifest.json", manifest("data.csv", raw, feature_version=version)))
    response = upload(storage_client, files, CREATE)
    assert response.status_code == 400 and response.json()["code"] == 40001
    if case in ("no_manifest", "no_version", "long_version"):
        assert "feature_version" in response.json()["message"]
    with Session(engine) as db:
        assert db.scalar(select(Commit)) is None and db.scalar(select(Dataset)) is None


def test_labels_atomic_rollback_and_empty_known_label(storage_client, engine):
    commits(storage_client)
    raw = table_bytes(fc.LABELS_COLUMNS, [dict(commit_hash=A, is_bug_inducing="0", labeled_at="2026-11-21T12:00:00Z"), dict(commit_hash="c" * 40, is_bug_inducing="1", labeled_at="")])
    assert upload(storage_client, [("labels.csv", raw)]).status_code == 400
    with Session(engine) as db:
        assert db.get(CommitFeature, A).is_bug_inducing == 1
    result = upload(storage_client, [("not_labels.csv", (ROOT / "boundary/labels.csv").read_bytes())]).json()["data"]
    assert result["items"][0]["updated"] == 1 and result["items"][0]["unchanged"] == 1
    details = storage_client.get("/api/datasets", headers=HEADERS).json()["data"]["items"][0]
    assert (details["pos_count"], details["neg_count"]) == (1, 1)


@pytest.mark.parametrize("changes", [{"model_name": "absent"}, {"commit_hash": "c" * 40}, {"model_version": "v3"}, {"feature_version": "log-v3"}, {"predicted_label": "0"}, {"risk_score": "1.1"}, {"predicted_at": "2026-11-21T12:00:00+00:00"}])
def test_prediction_constraints(storage_client, engine, changes):
    commits(storage_client)
    assert upload(storage_client, [("data.csv", prediction_rows(**changes))]).status_code == 400
    with Session(engine) as db:
        assert db.scalar(select(Prediction)) is None


def test_prediction_idempotent_and_feature_reversion_guard(storage_client):
    commits(storage_client)
    for count in ("inserted", "unchanged"):
        assert upload(storage_client, [("data.csv", prediction_rows())]).json()["data"]["items"][0][count] == 1
    raw = (ROOT / "normal/commits.csv").read_bytes()
    assert upload(storage_client, [("data.csv", raw), ("data.manifest.json", manifest("data.csv", raw, feature_version="v3"))]).status_code == 400


def test_mixed_batch_and_duplicate_upload_names(storage_client):
    raw = (ROOT / "boundary/labels.csv").read_bytes()
    commits(storage_client)
    result = upload(storage_client, [("legal.csv", raw), ("illegal.csv", (ROOT / "illegal/unknown.csv").read_bytes())])
    assert result.status_code == 200
    assert any(item["status"] == "rejected" for item in result.json()["data"]["items"])
    valid = prediction_rows()
    invalid = prediction_rows(model_name="missing")
    result = upload(storage_client, [("good.csv", valid), ("bad.csv", invalid)]).json()["data"]
    assert [item["status"] for item in result["items"]] == ["imported", "rejected"]
    assert result["summary"]["inserted"] == 1 and result["summary"]["rejected"] == 1
    assert upload(storage_client, [("same.csv", raw), ("same.csv", raw)]).status_code == 400


@pytest.mark.parametrize("settings", [{"feature_version": "v1"}, {"password": "secret"}, {"register_figures": 1}, {"model_artifact_status": "load_failed"}, {"create_dataset": {"name": "x"}}, {"dataset_id": "x", **CREATE}])
def test_bad_global_config(storage_client, settings):
    assert commits(storage_client, settings).status_code == 400


@pytest.mark.parametrize("line,algo", [("expert", "rf"), ("semantic", "rf"), ("fused", "rf"), ("e2e", "codebert_e2e")])
def test_opaque_model_registration_repeat(storage_client, engine, tmp_path, line, algo):
    raw = package(line=line, algo=algo)
    for count in ("inserted", "unchanged"):
        assert upload(storage_client, [("anything.zip", raw)]).json()["data"]["items"][0][count] == 1
    assert len(list(tmp_path.iterdir())) == 1
    with Session(engine) as db:
        artifact = db.scalar(select(ModelArtifact))
        assert artifact.size_bytes == len(raw) and artifact.checksum_sha256 == fc.sha256(raw)
        assert artifact.weight_path.startswith("backend/var/outputs/") and artifact.weight_path.endswith(".zip")
        assert artifact.train_job_id is None
        assert db.get(Model, "registered").feature_version == "log-v2"


@pytest.mark.parametrize("case", ["checksum", "traversal", "missing_weights", "order", "bad_line", "date"])
def test_bad_model_zip(storage_client, engine, tmp_path, case):
    members = fc.read_zip("m.zip", package())
    if case == "checksum":
        members["weights.pkl"] = b"tampered"
    if case == "traversal":
        members["../escape.pkl"] = b"bad"
    if case == "missing_weights":
        members.pop("weights.pkl")
    if case == "order":
        members["feature_order.txt"] = b"wrong"
    if case in ("bad_line", "date"):
        meta = fc.read_json(members["model_meta.json"])
        meta["line" if case == "bad_line" else "trained_at"] = "bad"
        members["model_meta.json"] = json.dumps(meta).encode()
    if case not in ("checksum", "traversal"):
        members["checksum.sha256"] = "\n".join(f"{fc.sha256(raw)}  {name}" for name, raw in members.items() if name != "checksum.sha256").encode()
    assert upload(storage_client, [("m.zip", zip_bytes(members))]).status_code == 400
    with Session(engine) as db:
        assert db.scalar(select(ModelArtifact)) is None
    assert not list(tmp_path.iterdir())


def test_existing_prediction_blocks_model_relabel(storage_client):
    commits(storage_client)
    upload(storage_client, [("p.csv", prediction_rows())])
    assert upload(storage_client, [("m.zip", package(model_name="fixture", version_key="v3"))]).status_code == 400


@pytest.mark.parametrize("case", ["valid", "false_header", "bad_sha", "unknown_model", "bad_type"])
def test_figure_verification(storage_client, engine, case):
    stream = io.BytesIO()
    Image.new("RGB", (2, 2)).save(stream, "PNG")
    raw = b"\x89PNG\r\n\x1a\nbad" if case == "false_header" else stream.getvalue()
    companion = manifest("figure.png", raw, model_name="absent" if case == "unknown_model" else "fixture", figure_type="evil" if case == "bad_type" else "roc")
    if case == "bad_sha":
        companion = companion.replace(fc.sha256(raw).encode(), b"0" * 64)
    response = upload(storage_client, [("figure.png", raw), ("figure.manifest.json", companion)])
    assert response.status_code == (200 if case == "valid" else 400)
    if case == "valid":
        assert response.json()["data"]["items"][0]["target_tables"] == ["model_figure"]


@pytest.mark.parametrize("table", list(Base.metadata.tables))
def test_all_twelve_raw_exports(storage_client, table):
    commits(storage_client)
    result = storage_client.get("/api/storage/export", headers=HEADERS, params={"table": table}).json()["data"]
    assert result["columns"] == list(Base.metadata.tables[table].columns.keys())
    assert len(result["preview"]) <= 20
    for output in result["outputs"]:
        url = f"/api/storage/outputs/{result['job_id']}/{output['name']}"
        response = storage_client.get(url, headers=HEADERS)
        assert response.status_code == 200 and fc.sha256(response.content) == output["sha256"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "attachment" in response.headers["content-disposition"]
        assert storage_client.get(url).status_code == 401
        if output["name"].endswith(".csv"):
            assert response.content.startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("params", [{"table": "unknown"}, {"table": "commit", "format": "json"}, {"table": "user", "dataset_id": "x"}, {"table": "dataset", "model_name": "x"}, {"table": "commit", "limit": 0}, {"table": "commit", "limit": 100001}, {"table": "commit", "arbitrary": "x"}, {"table": "commit", "start_time": "invalid"}])
def test_export_invalid_queries(storage_client, params):
    assert storage_client.get("/api/storage/export", headers=HEADERS, params=params).status_code == 400


def test_export_limit_snapshot_null_xlsx_and_secrets(storage_client, engine, monkeypatch):
    commits(storage_client)
    from app.services import storage
    monkeypatch.setattr(storage, "MAX_ROWS", 1)
    assert storage_client.get("/api/storage/export?table=commit", headers=HEADERS).status_code == 400
    first = storage_client.get("/api/storage/export?table=commit&limit=1", headers=HEADERS).json()["data"]
    assert first["row_count"] == 1 and first["total"] == 2
    again = storage_client.get("/api/storage/export?table=commit&limit=1", headers=HEADERS).json()["data"]
    assert first["preview"] == again["preview"] and first["outputs"][0]["sha256"] == again["outputs"][0]["sha256"]
    monkeypatch.setattr(storage, "MAX_ROWS", 100000)
    result = storage_client.get("/api/storage/export?table=commit_feature&format=xlsx", headers=HEADERS).json()["data"]
    output = result["outputs"][0]
    raw = storage_client.get(f"/api/storage/outputs/{result['job_id']}/{output['name']}", headers=HEADERS).content
    _, rows = fc.read_table("features.xlsx", raw)
    assert rows[1]["is_bug_inducing"] == "" and rows[0]["la"] == "-4.2720000000"
    with Session(engine) as db:
        db.add(User(user_id="global", display_name="Global", created_at=datetime(2026, 11, 21)))
        db.flush()
        db.add_all([UserConfig(user_id="global", config_key="password", value_json='"leak"', value_type="string", updated_at=datetime(2026, 11, 21)), UserConfig(user_id="global", config_key="page_prefs", value_json='{"password":"leak","url":"https://user:leak@example.org"}', value_type="object", updated_at=datetime(2026, 11, 21))])
        db.add(Job(job_id="secret-job", kind="collect", created_at=datetime(2026, 11, 21), params_json='{"token":"leak"}', error_log="password=leak /private/internal/file.sql"))
        db.commit()
    for table in ("user_config", "job"):
        data = storage_client.get(f"/api/storage/export?table={table}", headers=HEADERS).json()["data"]
        assert "leak" not in json.dumps(data) and "/private" not in json.dumps(data)


def test_datasets_empty_members_filters_and_canonical_exports(storage_client):
    assert storage_client.get("/api/datasets", headers=HEADERS).json()["data"] == {"total": 0, "page": 1, "size": 20, "items": []}
    assert storage_client.get("/api/datasets/missing", headers=HEADERS).status_code == 404
    commits(storage_client)
    dataset = storage_client.get("/api/datasets?status=ready&q=AI", headers=HEADERS).json()["data"]["items"][0]
    url = f"/api/datasets/{dataset['dataset_id']}"
    assert storage_client.get(url, headers=HEADERS).json()["data"]["pos_rate"] == 1
    members = storage_client.get(url + "/commits?is_test=1", headers=HEADERS).json()["data"]
    assert members["total"] == 1 and members["items"][0]["is_bug_inducing"] is None
    assert members["items"][0].get("label_method") is None
    for artifact, cols in (("commits", fc.COMMITS_COLUMNS), ("predictions", fc.PREDICTIONS_COLUMNS)):
        upload(storage_client, [("p.csv", prediction_rows())])
        params = {"artifact": artifact}
        if artifact == "predictions":
            params.update(model_name="fixture", decision_threshold=0.8)
        data = storage_client.get(url + "/export", params=params, headers=HEADERS).json()["data"]
        main = data["outputs"][0]
        raw = storage_client.get(f"/api/datasets/outputs/{data['job_id']}/{main['name']}", headers=HEADERS).content
        columns, rows = fc.read_table(main["name"], raw)
        assert columns == list(cols)
        if artifact == "predictions":
            assert rows[0]["predicted_label"] == "0"
        manifest_raw = storage_client.get(f"/api/datasets/outputs/{data['job_id']}/{data['manifest_name']}", headers=HEADERS).content
        assert fc.verify_manifest(main["name"], raw, manifest_raw)["config"]["feature_version"] == "log-v2"


@pytest.mark.parametrize("suffix", ["?size=0", "?status=evil", "/missing/commits?page=0", "/missing/commits?is_test=2"])
def test_invalid_dataset_parameters(storage_client, suffix):
    assert storage_client.get("/api/datasets" + suffix, headers=HEADERS).status_code == 400


@pytest.mark.parametrize("path", ["/api/datasets", "/api/datasets/missing", "/api/datasets/missing/commits", "/api/datasets/missing/export", "/api/storage/export?table=commit", "/api/storage/outputs/missing/x.csv", "/api/datasets/outputs/missing/x.csv"])
def test_all_read_routes_authenticated(storage_client, path):
    assert storage_client.get(path).status_code == 401


def test_download_paths_and_import_auth(storage_client):
    assert storage_client.post("/api/storage/import", files=[("files[]", ("x.csv", b"x"))]).status_code == 401
    assert storage_client.get("/api/storage/outputs/x/%2E%2E%2Fsecret", headers=HEADERS).status_code in (400, 404)
    assert storage_client.get("/api/storage/outputs/x/.index.json", headers=HEADERS).status_code == 404


@pytest.mark.parametrize("name", ["metrics.csv", "report.html", "explanations.csv", "localization.csv", "unsupported.json"])
def test_unsupported_result_schemas(storage_client, name):
    response = upload(storage_client, [(name, b"model_name,metric,value\nfixture,auc,0.9\n" if name.endswith("csv") else b"{}")])
    assert response.status_code == 400 and "unsupported_storage_schema" in response.json()["message"]


def test_repeated_figure_is_unchanged_without_new_batch(storage_client, tmp_path):
    stream = io.BytesIO()
    Image.new("RGB", (2, 2)).save(stream, "PNG")
    raw = stream.getvalue()
    files = [("f.png", raw), ("f.manifest.json", manifest("f.png", raw, model_name="fixture", figure_type="roc"))]
    for count in ("inserted", "unchanged"):
        response = upload(storage_client, files)
        assert response.json()["data"]["items"][0][count] == 1
    assert len(list(tmp_path.iterdir())) == 1


def test_invalid_figure_title_does_not_publish(storage_client, tmp_path):
    stream = io.BytesIO()
    Image.new("RGB", (2, 2)).save(stream, "PNG")
    raw = stream.getvalue()
    assert upload(storage_client, [("f.png", raw), ("f.manifest.json", manifest("f.png", raw, model_name="fixture", figure_type="roc", title="x" * 129))]).status_code == 400
    assert not list(tmp_path.iterdir())


def test_changed_features_cannot_relabel_old_probability(storage_client, engine):
    commits(storage_client)
    upload(storage_client, [("p.csv", prediction_rows())])
    columns, rows = fc.read_table("x.csv", (ROOT / "normal/commits.csv").read_bytes())
    rows[0]["la"] = "-5"
    assert commits(storage_client, raw=table_bytes(columns, rows)).status_code == 400
    with Session(engine) as db:
        assert str(db.get(CommitFeature, A).la) == "-4.2720000000"


def test_prediction_threshold_not_rounded_to_probability_precision(storage_client):
    commits(storage_client)
    response = upload(storage_client, [("p.csv", prediction_rows(decision_threshold="0.750000000001", predicted_label="0"))])
    assert response.status_code == 200


@pytest.mark.parametrize("params", [{"table": "user", "dataset_id": ""}, {"table": "commit", "start_time": ""}, {"table": "commit", "model_name": ""}])
def test_empty_filters_not_silently_ignored(storage_client, params):
    assert storage_client.get("/api/storage/export", headers=HEADERS, params=params).status_code == 400


def test_missing_predictions_nulls_and_nonapplicable_dataset_filters(storage_client):
    commits(storage_client)
    identifier = storage_client.get("/api/datasets", headers=HEADERS).json()["data"]["items"][0]["dataset_id"]
    assert storage_client.get(f"/api/datasets/{identifier}/export?model_name=fixture", headers=HEADERS).status_code == 400
    data = storage_client.get(f"/api/datasets/{identifier}/export?artifact=predictions&model_name=fixture", headers=HEADERS).json()["data"]
    assert data["row_count"] == 2
    assert all(row["risk_score"] is None and row["predicted_label"] is None for row in data["preview"])


def test_nested_colon_secret_and_absolute_path_scrub(storage_client, engine):
    with Session(engine) as db:
        db.add(Job(job_id="scrub", kind="collect", created_at=datetime(2026, 11, 21), params_json=json.dumps({"notes": "password: hidden_value", "nested": ["failed at /private/internal/location"]})))
        db.commit()
    data = storage_client.get("/api/storage/export?table=job", headers=HEADERS).json()["data"]
    assert "hidden_value" not in json.dumps(data) and "/private/internal" not in json.dumps(data)


@pytest.mark.parametrize("kind", ["labels", "predictions"])
def test_duplicate_keys_rejected_for_every_row_schema(storage_client, engine, kind):
    commits(storage_client)
    columns, rows = fc.read_table("x.csv", prediction_rows() if kind == "predictions" else (ROOT / "boundary/labels.csv").read_bytes())
    response = upload(storage_client, [("duplicate.csv", table_bytes(columns, [rows[0], rows[0]]))])
    assert response.status_code == 400 and "duplicate natural key" in response.json()["message"]
    with Session(engine) as db:
        assert db.scalar(select(Prediction)) is None


def test_unknown_file_does_not_abort_other_valid_files(storage_client):
    raw = (ROOT / "normal/commits.csv").read_bytes()
    response = upload(storage_client, [("commits.csv", raw), ("commits.manifest.json", manifest("commits.csv", raw, feature_version="log-v2")), ("unknown.csv", b"unknown\n1\n")])
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert items[0]["status"] == "imported"
    assert items[1]["status"] == "rejected"
    assert "unsupported_storage_schema" in items[1]["errors"][0]


def test_figure_import_is_readable_through_figures_api(storage_client, engine, monkeypatch):
    from app.api.figures import figures
    monkeypatch.setattr("app.api.figures._load_metrics", lambda: {"fixture": {"auc": 0.99}})
    output = io.BytesIO()
    Image.new("RGB", (2, 2)).save(output, format="PNG")
    raw = output.getvalue()
    response = upload(storage_client, [("roc.png", raw), ("roc.manifest.json", manifest("roc.png", raw, model_name="fixture", figure_type="roc"))])
    assert response.status_code == 200
    view = figures("fixture")["data"]
    assert len(view["figures"]) == 1
    assert view["metrics"] is None
    url = view["figures"][0]["file_path"]
    assert url.startswith("/api/storage/outputs/")
    assert storage_client.get(url, headers=HEADERS).content == raw


def test_failed_asset_commit_does_not_leave_published_files(storage_client, tmp_path, monkeypatch):
    from sqlalchemy.exc import IntegrityError
    def fail_commit(self):
        raise IntegrityError("injected", {}, Exception("test commit failure"))
    monkeypatch.setattr(Session, "commit", fail_commit)
    response = upload(storage_client, [("model_package.zip", package())])
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_asset_names_include_the_actual_output_batch_id(storage_client, engine):
    response = upload(storage_client, [("model_package.zip", package())])
    assert response.status_code == 200
    with Session(engine) as db:
        path = db.scalar(select(ModelArtifact.weight_path))
    parts = path.split("/")
    assert parts[3] in parts[4]


def test_packet_registration_cannot_relabel_an_active_model(storage_client, monkeypatch):
    from types import SimpleNamespace

    from app import model_registry
    monkeypatch.setattr(model_registry, "all_models", lambda: [SimpleNamespace(name="loaded-model")])
    response = upload(storage_client, [("model_package.zip", package(model_name="loaded-model"))])
    assert response.status_code == 400
    assert "loaded" in response.json()["message"]


def test_output_tampering_and_database_failure_not_empty_export(storage_client, engine, monkeypatch):
    data = storage_client.get("/api/storage/export?table=model", headers=HEADERS).json()["data"]
    output = data["outputs"][0]
    path = output_store.read_output("storage", data["job_id"], output["name"])
    path.write_bytes(b"tampered")
    assert storage_client.get(f"/api/storage/outputs/{data['job_id']}/{output['name']}", headers=HEADERS).status_code == 404
    from sqlalchemy.exc import OperationalError
    def failure(*args, **kwargs):
        raise OperationalError("SELECT private", {}, Exception("password=secret /private/sql"))
    monkeypatch.setattr(Session, "execute", failure)
    response = storage_client.get("/api/storage/export?table=model", headers=HEADERS)
    assert response.status_code == 500 and response.json()["data"] is None
    assert "private" not in response.text and "password" not in response.text


@pytest.mark.parametrize("case", ["bad_repo_url", "manifest_input_name", "unhashable_figure_type", "nonfinite_model_meta"])
def test_malformed_metadata_is_client_error(storage_client, tmp_path, case):
    if case == "bad_repo_url":
        response = commits(storage_client, {"create_dataset": {"name": "x", "repo_source": "https://[bad"}})
    elif case == "manifest_input_name":
        raw = (ROOT / "normal/commits.csv").read_bytes()
        companion = json.loads(manifest("x.csv", raw, feature_version="log-v2"))
        companion["inputs"][0]["name"] = 42
        response = upload(storage_client, [("x.csv", raw), ("x.manifest.json", json.dumps(companion).encode())])
    elif case == "unhashable_figure_type":
        stream = io.BytesIO()
        Image.new("RGB", (2, 2)).save(stream, "PNG")
        raw = stream.getvalue()
        response = upload(storage_client, [("f.png", raw), ("f.manifest.json", manifest("f.png", raw, model_name="fixture", figure_type=[], title="x"))])
    else:
        members = fc.read_zip("m.zip", package())
        members["model_meta.json"] = members["model_meta.json"].replace(b'"seed": 42', b'"seed": 42, "bad_numeric": 1e309')
        members["checksum.sha256"] = "\n".join(f"{fc.sha256(raw)}  {name}" for name, raw in members.items() if name != "checksum.sha256").encode()
        response = upload(storage_client, [("m.zip", zip_bytes(members))])
    assert response.status_code == 400 and response.json()["code"] == 40001
    assert not list(tmp_path.iterdir())


def test_manifest_failure_reports_all_rejected_rows_and_target_tables(storage_client):
    commits(storage_client)
    raw = (ROOT / "normal/commits.csv").read_bytes()
    companion = manifest("bad.csv", raw, feature_version="log-v2").replace(fc.sha256(raw).encode(), b"0" * 64)
    data = upload(storage_client, [("good.csv", prediction_rows()), ("bad.csv", raw), ("bad.manifest.json", companion)]).json()["data"]
    assert data["items"][1]["rejected"] == 2
    assert data["items"][1]["target_tables"] == ["commit", "commit_feature"]
