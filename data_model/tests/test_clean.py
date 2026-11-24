"""W4 file-only cleaning 契约测试：collected_commits -> clean_dataset，无数据库、无模型特征。"""
from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
sys.path.insert(0, str(DATA_MODEL))
sys.path.insert(0, str(ROOT / "backend"))
from app.services import file_contracts as fc

OPS = ["schema_validate", "duplicate_drop", "merge_commit_filter", "missing_value_handle",
       "invalid_time_filter", "unlabeled_handle", "outlier_filter", "label_validate", "text_clean",
       "type_convert", "date_normalize", "text_normalize", "category_normalize", "derive_basic_fields"]
CLEAN_OPS, PREPROCESS_OPS = OPS[:9], OPS[9:]


def core():
    return importlib.import_module("preparation.clean")


def rows(count=4):
    result = []
    for index in range(count):
        committed = (datetime(2026, 1, 1, 12, tzinfo=UTC) + timedelta(days=index)).isoformat().replace("+00:00", "Z")
        row = dict.fromkeys(fc.CLEAN_DATASET_COLUMNS)
        row.update(commit_hash=f"{index + 1:040x}", repo_name="fixture",
                   repo_url="https://example.invalid/repo.git", author_name="测试",
                   author_email="dev@example.invalid", committed_at=committed,
                   message="Feature change", parent_hash=f"{index:040x}",
                   label_method="szz_v1", label_source="git_szz", source_type="git_repo",
                   is_bug_inducing=index % 2, labeled_at=committed)
        result.append(row)
    return result


def config(*enabled, mode="apply", fmt="csv", charts=(), params=None):
    chosen = set(enabled) if enabled else set(OPS) - {"outlier_filter", "derive_basic_fields"}
    steps = [{"op": op, "enabled": op in chosen, "params": (params or {}).get(op, {})} for op in OPS]
    return {"mode": mode, "steps": steps, "format": fmt, "chart_columns": list(charts)}


def apply(*enabled, records=None, params=None, charts=()):
    return core().run(records if records is not None else rows(), config(*enabled, params=params, charts=charts))


def stat(result, op):
    return next(item for item in result["steps_stats"] if item["step"] == op)


def manifest(name, content, **fields):
    return json.dumps({"schema_version": "1.0", "module": "collect", "job_id": "fixture",
                       "inputs": [], "config": {"feature_version": "v1", **fields},
                       "outputs": [{"name": name, "sha256": fc.sha256(content)}],
                       "code_version": "fixture-code", "created_at": "2026-02-01T00:00:00Z"}).encode()


def test_operations_catalog():
    catalog = core().operations()
    assert [item["op"] for item in catalog] == OPS
    for item in catalog:
        assert set(item) == {"op", "name", "description", "group", "input_schema", "output_schema",
                             "params_schema", "order_constraints", "supports_preview", "default_enabled"}
        assert item["group"] == ("clean" if item["op"] in CLEAN_OPS else "preprocess")
        assert item["supports_preview"] is True
        assert item["default_enabled"] is (item["op"] != "derive_basic_fields")
        assert item["input_schema"]["columns"] == list(fc.CLEAN_DATASET_COLUMNS)
        for param in item["params_schema"]:
            assert set(param) == {"name", "type", "default", "min", "max", "choices", "description"}
        assert all(rule["type"] in {"first", "after", "before_basic_derive", "clean_before_preprocess"}
                   for rule in item["order_constraints"])
    assert catalog[0]["order_constraints"] == [{"type": "first"}]


def test_config_normalizes_without_mutating_input():
    raw = config()
    saved = copy.deepcopy(raw)
    normalized = core().validate_config(raw)
    assert raw == saved
    assert normalized["mode"] == "apply" and normalized["format"] == "csv"
    assert normalized["chart_columns"] == []
    assert all(set(step["params"]) == {p["name"] for p in next(
        item for item in core().operations() if item["op"] == step["op"])["params_schema"]}
        for step in normalized["steps"])


@pytest.mark.parametrize("change", [
    {"dataset_id": 1}, {"template": "x"}, {"features": ["ns"]}, {"seed": 42}, {"split_ratio": 0.7},
    {"is_test": 1}, {"mode": "invalid"}, {"steps": {}}, {"format": "zip"},
    {"chart_columns": ["ns"]}, {"chart_columns": "message"},
    {"chart_columns": ["message", "message"]},
])
def test_config_rejects_unknown_or_train_only_keys(change):
    with pytest.raises(ValueError):
        core().validate_config({**config(), **change})


@pytest.mark.parametrize("steps", [
    [{"op": "unknown", "enabled": True, "params": {}}],
    [{"op": "time_split", "enabled": True, "params": {}}],
    [{"op": "duplicate_drop", "enabled": 1, "params": {}}],
    [{"op": "duplicate_drop", "enabled": True, "params": [], "extra": 1}],
    [{"op": "duplicate_drop", "enabled": None}],
    [{"op": "duplicate_drop", "params": None}],
    [{"op": "duplicate_drop", "enabled": True, "params": {"unknown": 1}}],
    [{"op": "duplicate_drop", "enabled": True, "params": {}}] * 2,
    [{"op": "missing_value_handle", "enabled": True, "params": {"strategy": "drop"}}],
    [{"op": "outlier_filter", "enabled": True, "params": {"method": "mad"}}],
    [{"op": "derive_basic_fields", "enabled": True, "params": {"columns": "message"}}],
])
def test_config_rejects_invalid_steps(steps):
    with pytest.raises(ValueError):
        core().validate_config({"mode": "apply", "steps": steps})


def test_config_requires_enabled_schema_validate_first():
    with pytest.raises(ValueError):
        core().validate_config({"mode": "apply", "steps": [
            {"op": "duplicate_drop", "enabled": True}, {"op": "schema_validate", "enabled": True}]})
    with pytest.raises(ValueError):
        core().validate_config({"mode": "apply", "steps": [
            {"op": "schema_validate", "enabled": False}]})


def test_config_requires_clean_ops_before_preprocess():
    steps = [{"op": "schema_validate", "enabled": True},
             {"op": "date_normalize", "enabled": True},
             {"op": "duplicate_drop", "enabled": True}]
    with pytest.raises(ValueError):
        core().validate_config({"mode": "apply", "steps": steps})


def test_config_requires_derive_after_date_normalize():
    steps = [{"op": "schema_validate", "enabled": True},
             {"op": "derive_basic_fields", "enabled": True},
             {"op": "date_normalize", "enabled": True}]
    with pytest.raises(ValueError):
        core().validate_config({"mode": "apply", "steps": steps})


def test_parse_input_accepts_new_schema_only():
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows(), "csv")
    parsed, metadata = core().parse_input("collected_commits.csv", content)
    assert len(parsed) == 4
    assert metadata["manifest_verified"] is False and metadata["external"] is True
    assert metadata["input"]["sha256"] == fc.sha256(content)
    old = {**rows()[0], "ns": 1, "is_test": 0}
    with pytest.raises(ValueError):
        core().parse_input("commits.csv", fc.encode_table(("commit_hash", "ns", "is_test"), [old], "csv"))


def test_parse_input_verifies_manifest():
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows(), "csv")
    _parsed, metadata = core().parse_input("collected_commits.csv", content, manifest("collected_commits.csv", content))
    assert metadata["manifest_verified"] is True
    assert metadata["evidence"]["module"] == "collect"


@pytest.mark.parametrize("field,value", [
    ("commit_hash", "ABC"), ("committed_at", "2026-01-01 12:00:00"),
    ("label_method", "szz"), ("label_source", "manual"), ("source_type", "camel"),
])
def test_parse_input_rejects_invalid_field_values(field, value):
    record = rows()[0]
    record[field] = value
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, [record], "csv")
    with pytest.raises(ValueError):
        core().parse_input("collected_commits.csv", content)


@pytest.mark.parametrize("field", ["message", "author_name"])
def test_rows_external_rejects_raw_formula(field):
    record = rows()[0]
    record[field] = "=SUM(1)"
    with pytest.raises(ValueError):
        core()._rows_external([record])


def test_parse_input_rejects_duplicate_hash_and_bad_name():
    duplicate = rows() + [rows()[0]]
    content = fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, duplicate, "csv")
    with pytest.raises(ValueError):
        core().parse_input("collected_commits.csv", content)
    with pytest.raises(Exception):
        core().parse_input("../collected_commits.csv", content)


def test_run_never_emits_model_features_or_is_test():
    result = apply()
    assert result["summary"]["input_rows"] == result["summary"]["output_rows"] == 4
    for row in result["rows"]:
        assert not set(row) & set(fc.FEATURE_COLUMNS)
        assert "is_test" not in row
        assert set(row) == set(fc.CLEAN_DATASET_COLUMNS)


def test_duplicate_drop_records_excluded_reason():
    result = apply("schema_validate", "duplicate_drop", records=rows() + [rows()[0]])
    assert len(result["rows"]) == 4
    assert stat(result, "duplicate_drop")["excluded_samples"][0]["reason"].startswith("Duplicate")
    assert result["summary"]["output_rows"] == 4


def test_merge_commit_filter_uses_parent_evidence():
    records = rows()
    records[1]["parent_hash"] = f"{records[1]['parent_hash']} {records[2]['parent_hash']}"
    result = apply("schema_validate", "merge_commit_filter", records=records)
    assert [r["commit_hash"] for r in result["rows"]] == [r["commit_hash"] for r in records if r is not records[1]]
    assert "Multiple valid parents" in stat(result, "merge_commit_filter")["excluded_samples"][0]["reason"]


@pytest.mark.parametrize("strategy,expected", [("keep", 4), ("fill", 4), ("exclude", 3)])
def test_missing_value_handle_strategies(strategy, expected):
    records = rows()
    records[0]["message"] = None
    result = apply("schema_validate", "missing_value_handle", records=records,
                   params={"missing_value_handle": {"strategy": strategy}})
    assert len(result["rows"]) == expected
    if strategy == "fill":
        assert result["rows"][0]["message"] == ""


def test_invalid_time_filter_excludes_bad_timestamp():
    records = rows()
    records[2]["committed_at"] = "not-a-time"
    result = apply("schema_validate", "invalid_time_filter", records=records)
    assert len(result["rows"]) == 3
    assert result["rows"][0]["commit_hash"] == records[0]["commit_hash"]


@pytest.mark.parametrize("strategy,expected", [("keep", 4), ("warn", 4), ("exclude", 3)])
def test_unlabeled_handle_keeps_null_semantics(strategy, expected):
    records = rows()
    records[0]["is_bug_inducing"] = None
    result = apply("schema_validate", "unlabeled_handle", records=records,
                   params={"unlabeled_handle": {"strategy": strategy}})
    assert len(result["rows"]) == expected
    assert all(r["is_bug_inducing"] is not None or r["is_bug_inducing"] is None for r in result["rows"])
    if strategy == "warn":
        assert any("NULL kept, not 0" in warning for warning in result["summary"]["warnings"])


@pytest.mark.parametrize("method", ["iqr", "zscore"])
def test_outlier_filter_only_touches_existing_columns(method):
    result = apply("schema_validate", "outlier_filter", params={"outlier_filter": {"method": method}})
    assert len(result["rows"]) == 4
    assert any("no model features generated" in warning for warning in result["summary"]["warnings"])


def test_text_clean_and_normalize_collapse_controls_and_whitespace():
    records = rows()
    records[0]["message"] = "  fix\x00the\nroute  "
    result = apply("schema_validate", "text_clean", "text_normalize", records=records)
    assert result["rows"][0]["message"] == "fix the route"
    assert stat(result, "text_clean")["modified_rows"] >= 1


@pytest.mark.parametrize("value,expected", [
    ("2026-01-01T12:00:00+08:00", "2026-01-01T04:00:00Z"),
    ("2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z"),
])
def test_date_normalize_produces_utc(value, expected):
    records = rows()
    records[0]["committed_at"] = value
    result = apply("schema_validate", "date_normalize", records=records)
    assert result["rows"][0]["committed_at"] == expected


def test_category_normalize_trims_without_encoding():
    records = rows()
    records[0]["label_method"] = " szz_v1 "
    result = apply("schema_validate", "category_normalize", records=records)
    assert result["rows"][0]["label_method"] == "szz_v1"
    assert not set(result["rows"][0]) & set(fc.FEATURE_COLUMNS)


def test_derive_basic_fields_are_display_only():
    result = apply("schema_validate", "date_normalize", "derive_basic_fields")
    assert result["rows"][0]["message_length"] == len("Feature change")
    assert result["rows"][0]["parent_count"] == 1
    assert result["rows"][0]["commit_hour"] == 12
    assert not set(result["rows"][0]) & set(fc.FEATURE_COLUMNS)


def test_column_stats_before_and_after_are_reported():
    result = apply("schema_validate", "text_clean", charts=["message"])
    stats = result["feature_stats"]["message"]
    assert stats["before"]["kind"] == stats["after"]["kind"] == "categorical"
    assert set(stats["before"]["frequency"]) == {"Feature change"}


def test_stats_record_every_excluded_and_modified_hash():
    records = rows()
    records[1]["parent_hash"] = "a" * 40 + " " + "b" * 40
    records[2]["message"] = "  changed  "
    result = apply("schema_validate", "merge_commit_filter", "text_clean", records=records)
    excluded = {item["commit_hash"] for step in result["steps_stats"] for item in step["excluded_samples"]}
    modified = {item["commit_hash"] for step in result["steps_stats"] for item in step["modified_samples"]}
    assert records[1]["commit_hash"] in excluded
    assert records[2]["commit_hash"] in modified


def test_preview_mode_has_no_dataset_artifact():
    records = rows()
    result = core().run(records, config("schema_validate", mode="preview"))
    artifacts = core().artifacts(result, "preview-job")
    assert not any(name.startswith("clean_dataset_") for name in artifacts)
    assert "clean_steps_stats_preview-job.json" in artifacts


@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_artifacts_primary_and_parity_tables(fmt):
    result = apply("schema_validate", charts=["message"])
    artifacts = core().artifacts(result, "fixture-job")
    assert f"clean_dataset_fixture-job.{fmt}" in artifacts
    parity = "xlsx" if fmt == "csv" else "csv"
    assert f"clean_dataset_fixture-job.{parity}" in artifacts
    columns, decoded = fc.read_table(f"data.{fmt}", artifacts[f"clean_dataset_fixture-job.{fmt}"])
    assert columns == list(fc.CLEAN_DATASET_COLUMNS) and len(decoded) == 4
    assert json.loads(artifacts["clean_steps_stats_fixture-job.json"])[0]["step"] == "schema_validate"
    assert any(name.endswith("_message_fixture-job.png") for name in artifacts)


def test_artifacts_reject_invalid_job_id():
    with pytest.raises(ValueError):
        core().artifacts(apply(), "../bad")


def test_code_version_is_stable():
    assert core().code_version() == core().code_version()


def test_cli_operations_and_isolated_run(tmp_path):
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(DATA_MODEL) + ";" + str(ROOT / "backend"),
           "DATABASE_URL": "", "DB_HOST": "", "MPLCONFIGDIR": str(tmp_path / "mpl")}
    operations = subprocess.run([sys.executable, "-m", "preparation.clean", "operations"],
                                cwd=DATA_MODEL, env=env, capture_output=True, text=True, encoding="utf-8")
    assert operations.returncode == 0, operations.stderr
    assert [item["op"] for item in json.loads(operations.stdout)] == OPS

    source = tmp_path / "collected_commits.csv"
    source.write_bytes(fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows(), "csv"))
    chain = tmp_path / "chain.json"
    chain.write_text(json.dumps([{"op": "schema_validate", "enabled": True}]), encoding="utf-8")
    out = tmp_path / "out"
    process = subprocess.run([sys.executable, "-m", "preparation.clean", "run", "--input", str(source),
                              "--chain", str(chain), "--mode", "apply", "--out", str(out)],
                             cwd=DATA_MODEL, env=env, capture_output=True, text=True, encoding="utf-8")
    assert process.returncode == 0, process.stderr
    payload = json.loads(process.stdout)
    assert payload["summary"]["output_rows"] == 4
    assert any(item["name"].startswith("clean_dataset_") for item in payload["outputs"])


def test_core_imports_no_database_or_online_modules():
    source = (DATA_MODEL / "preparation/clean.py").read_text(encoding="utf-8")
    assert "SessionLocal" not in source
    assert "requests" not in source
