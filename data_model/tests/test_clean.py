"""AI-generated/unreviewed W4 core tests and in-memory fixtures; no database."""
from __future__ import annotations

import copy
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
PYTHON = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
sys.path.insert(0, str(DATA_MODEL))
sys.path.insert(0, str(ROOT / "backend"))
from app.services import file_contracts as fc

FEATURES = list(fc.FEATURE_COLUMNS)
OPS = ["merge_filter", "szz_label", "d5_exclude", "anomaly_exclude", "label_validate",
       "feature_align", "log_transform", "standardize", "time_split"]


def core():
    assert (DATA_MODEL / "preparation/clean.py").is_file(), "W4 clean core missing"
    return importlib.import_module("preparation.clean")


def rows(count=4):
    result = []
    for i in range(count):
        row = dict.fromkeys(fc.COMMITS_COLUMNS, None)
        row.update(commit_hash=f"{i + 1:040x}", repo_name="fixture", author_name="测试",
                   author_email="test@example.invalid",
                   committed_at=(datetime(2026, 1, 1, 12, tzinfo=UTC) + timedelta(days=i)).isoformat().replace("+00:00", "Z"),
                   message="Feature change", parent_hash=f"{i:040x}" if i else None,
                   is_bug_inducing=i % 2, labeled_at="2026-02-01T00:00:00Z", is_test=0,
                   label_method="szz")
        row.update({feature: float(i + 1) for feature in FEATURES})
        row["fix"] = i % 2
        result.append(row)
    return result


def config(*enabled, mode="apply", params=None, **extra):
    chosen = set(enabled or [op for op in OPS if op not in ("anomaly_exclude", "standardize")])
    return {"mode": mode, "steps": [{"op": op, "enabled": op in chosen,
            "params": (params or {}).get(op, {})} for op in OPS], **extra}


def manifest(name, content, **config_fields):
    return json.dumps({"schema_version": "1.0", "module": "collect", "job_id": "fixture",
                       "inputs": [], "config": {"feature_version": "v1", **config_fields},
                       "outputs": [{"name": name, "sha256": fc.sha256(content)}],
                       "code_version": "fixture-code", "created_at": "2026-02-01T00:00:00Z"}).encode()


def stat(result, op):
    return next(item for item in result["steps_stats"] if item["op"] == op)


@pytest.mark.parametrize('version', ['a' * 20, 'b' * 32])
def test_standardized_version_is_bounded_and_preserves_source(version):
    result = core().run(rows(), config('feature_align', 'standardize', 'time_split'), metadata={'feature_version': version})
    assert len(result['config']['feature_version']) <= 32
    assert result['config']['feature_version'].endswith('-standardized')
    assert result['config']['source_feature_version'] == version


def test_registry_declares_every_removing_step_before_standardize():
    catalog = {item['op']: item for item in core().operations()}
    for op in ('merge_filter', 'd5_exclude', 'anomaly_exclude'):
        assert {'type': 'before', 'op': 'standardize'} in catalog[op]['order_constraints']


def test_operations_catalog():
    catalog = core().operations()
    assert [item["op"] for item in catalog] == OPS
    for item in catalog:
        assert set(item) == {"op", "name", "description", "input_schema", "output_schema",
                             "params_schema", "order_constraints", "supports_preview", "default_enabled"}
        assert item["supports_preview"] is True
        assert item["default_enabled"] is (item["op"] not in ("standardize", "anomaly_exclude"))
        for param in item["params_schema"]:
            assert set(param) == {"name", "type", "default", "min", "max", "choices", "description"}
        assert all(rule["type"] in {"first", "last", "before", "after", "requires"}
                   for rule in item["order_constraints"])
    assert {"type": "requires", "op": "time_split"} in catalog[7]["order_constraints"]


def test_normalization_and_copy_isolation():
    raw = config(features=["age", "fix", "ns"])
    saved = copy.deepcopy(raw)
    normalized = core().validate_config(raw)
    assert normalized["features"] == ["ns", "fix", "age"]
    assert normalized["seed"] == 42 and normalized["split_ratio"] == 0.7
    assert normalized["format"] == "csv"
    assert raw == saved


@pytest.mark.parametrize("change", [
    {"dataset_id": 1}, {"template": "x"}, {"random": True}, {"seed": True}, {"seed": 1.0},
    {"split_ratio": True}, {"split_ratio": float("nan")}, {"split_ratio": 0}, {"split_ratio": 1},
    {"split_ratio": "0.7"}, {"format": "zip"}, {"features": []}, {"features": ["ns", "ns"]},
    {"features": ["unknown"]}, {"features": "ns"}, {"mode": "invalid"}, {"steps": {}},
])
def test_reject_unknown_and_native_wrong_types(change):
    with pytest.raises((ValueError, fc.AppError)):
        core().validate_config({**config(), **change})


@pytest.mark.parametrize("steps", [
    [{"op": "unknown", "enabled": True, "params": {}}],
    [{"op": "time_split", "enabled": 1, "params": {}}],
    [{"op": "time_split", "enabled": True, "params": {"random": False}}],
    [{"op": "time_split", "enabled": True, "params": [], "extra": 1}],
    [{"op": "time_split", "extra": 1}],
    [{"enabled": True, "params": {}}],
    [{"op": "time_split", "enabled": None}],
    [{"op": "time_split", "params": None}],
    [{"op": "time_split", "params": []}],
    [{"op": "log_transform", "enabled": True, "params": {}}] * 2,
    [{"op": "standardize", "enabled": False, "params": {"with_mean": 1}}],
    [{"op": "anomaly_exclude", "enabled": True, "params": {"max_abs": float("inf")}}],
    [{"op": "szz_label", "enabled": True, "params": {"method": "both"}}],
])
def test_reject_invalid_steps(steps):
    with pytest.raises((ValueError, fc.AppError)):
        core().validate_config({"mode": "preview", "steps": steps})


@pytest.mark.parametrize("order", [
    ["szz_label", "merge_filter"], ["time_split", "feature_align"],
    ["d5_exclude", "szz_label"], ["log_transform", "feature_align"],
    ["standardize", "log_transform", "time_split"],
    ["feature_align", "standardize", "anomaly_exclude", "time_split"], ["standardize"],
])
def test_order_and_standardize_requires_final_split(order):
    with pytest.raises((ValueError, fc.AppError)):
        core().validate_config({"mode": "apply", "steps": [
            {"op": op, "enabled": True, "params": {}} for op in order]})


def test_mode_and_steps_required():
    for raw in ({}, {"steps": []}, {"mode": "apply"}):
        with pytest.raises((ValueError, fc.AppError)):
            core().validate_config(raw)


def test_merge_uses_parent_evidence_not_message():
    source = rows()
    source[0]["message"] = "Merge another feature"
    source[1]["parent_hash"] = "a" * 40 + " " + "b" * 40
    data = fc.encode_table(fc.COMMITS_COLUMNS, source, "csv")
    parsed, metadata = core().parse_input("input.csv", data)
    result = core().run(parsed, config(), metadata=metadata)
    assert [r["commit_hash"] for r in result["rows"]] == [source[i]["commit_hash"] for i in (0, 2, 3)]
    assert stat(result, "merge_filter")["excluded_samples"][0]["commit_hash"] == source[1]["commit_hash"]
    with pytest.raises((ValueError, fc.AppError)):
        core().run(parsed, config("label_validate"), metadata=metadata)


def test_d5_keeps_known_positive_and_unknown_without_method():
    source = rows()
    for row in source:
        row["message"] = "CAMEL-123 fix defect"
    source[0]["is_bug_inducing"] = 1
    source[1].update(is_bug_inducing=None, labeled_at=None)
    source[2].update(is_bug_inducing=None, label_method=None, labeled_at=None)
    source[3]["is_bug_inducing"] = 0
    result = core().run(source, config())
    assert [r["commit_hash"] for r in result["rows"]] == [source[i]["commit_hash"] for i in (0, 2, 3)]
    assert result["rows"][1]["is_bug_inducing"] is None
    reason = stat(result, "d5_exclude")["excluded_samples"][0]["reason"].lower()
    assert "file" in reason and "unresolved" in reason
    assert any("method" in warning.lower() for warning in result["summary"]["warnings"])
    assert stat(result, "szz_label")["modified"] == 0


def test_label_method_mismatch_rejected_without_changing_input():
    source = rows()
    saved = copy.deepcopy(source)
    with pytest.raises((ValueError, fc.AppError)):
        core().run(source, config(params={"szz_label": {"method": "szz_lite"}}))
    assert source == saved


def test_nullable_labels_log_identity_and_disabled_operations():
    source = rows()
    source[0].update(is_bug_inducing=None, labeled_at=None, label_method=None)
    source[0]["la"] = -2.345
    saved = copy.deepcopy(source)
    events = []
    result = core().run(source, config(), progress=lambda *args: events.append(args))
    assert source == saved
    assert result["rows"][0]["is_bug_inducing"] is None
    assert [[r[f] for f in FEATURES] for r in result["rows"]] == [[r[f] for f in FEATURES] for r in source]
    assert stat(result, "log_transform")["modified"] == 0
    assert any("skip" in warning.lower() for warning in stat(result, "log_transform")["warnings"])
    assert result["config"]["feature_version"] == "v1"
    assert result["config"]["feature_state"] == "log_v1"
    for op in ("standardize", "anomaly_exclude"):
        assert stat(result, op)["enabled"] is False
        assert stat(result, op)["removed"] == stat(result, op)["modified"] == 0
    assert events and all(total == len(OPS) for _, _, total in events)
    assert [done for _, done, _ in events] == sorted(done for _, done, _ in events)
    assert all(s["elapsed_ms"] >= 0 for s in result["steps_stats"])
    assert any(s["elapsed_ms"] > 0 for s in result["steps_stats"])


def test_anomaly_real_outlier_not_class_ratio_rebalancing():
    source = rows(5)
    for row in source:
        row["is_bug_inducing"] = 1
    source[4].update(ns=2e6, is_bug_inducing=None, labeled_at=None)
    result = core().run(source, config("anomaly_exclude", "label_validate"))
    assert len(result["rows"]) == 4
    assert result["summary"]["label_dist"] == {"positive": 4, "negative": 0, "null": 0}
    assert stat(result, "anomaly_exclude")["removed"] == 1
    assert not any("ratio" in w.lower() for w in result["summary"]["warnings"])


@pytest.mark.parametrize("with_mean,with_std", [(True, True), (False, True), (True, False), (False, False)])
def test_scaler_fits_only_final_training_rows_and_preserves_fix(with_mean, with_std):
    source = rows(5)
    source[0]["ns"] = 2e6
    source[1]["ns"], source[2]["ns"], source[3]["ns"], source[4]["ns"] = 1, 5, 10000, 90000
    cfg = config("anomaly_exclude", "feature_align", "log_transform", "standardize", "time_split",
                 split_ratio=0.5, params={"standardize": {"with_mean": with_mean, "with_std": with_std}})
    result = core().run(list(reversed(source)), cfg)
    output = result["rows"]
    assert [r["is_test"] for r in output] == [0, 0, 1, 1]
    assert [r["fix"] for r in output] == [r["fix"] for r in source[1:]]
    expected = [(value - (3 if with_mean else 0)) / (2 if with_std else 1) for value in (1, 5, 10000, 90000)]
    assert [r["ns"] for r in output] == pytest.approx(expected)
    scaler = result["config"]["scaler"]
    assert scaler["train_hashes"] == [r["commit_hash"] for r in source[1:3]]
    assert scaler["n_samples_seen_"] == 2
    assert "fix" not in scaler["features"]
    assert scaler["boundary"]["train_max"] == source[2]["committed_at"]
    assert result["config"]["feature_version"] == "v1-standardized"
    assert result["config"]["feature_state"] == "standardized_v1"
    with pytest.raises((ValueError, fc.AppError)):
        core().run(output, cfg, metadata={"feature_version": "v1-standardized", "feature_state": "standardized_v1"})


@pytest.mark.parametrize("ratio,same_second", [(0.7, True), (0.1, False)])
def test_invalid_temporal_boundaries_rejected(ratio, same_second):
    source = rows(2)
    if same_second:
        source[1]["committed_at"] = source[0]["committed_at"].replace("00Z", "00.5Z")
    with pytest.raises((ValueError, fc.AppError)):
        core().run(source, config(split_ratio=ratio))


@pytest.mark.parametrize("count", [0, 1])
def test_empty_and_single_row_stats_and_split(count):
    source = rows(count)
    data = fc.encode_table(fc.COMMITS_COLUMNS, source, "csv")
    parsed, metadata = core().parse_input("input.csv", data)
    result = core().run(parsed, config("feature_align", "standardize", "time_split"), metadata=metadata)
    assert result["summary"]["output_rows"] == count
    assert result["summary"]["warnings"]
    assert all(r["is_test"] == 0 for r in result["rows"])
    assert result["feature_stats"]["ns"]["before"]["missing_count"] == 0
    if not count:
        assert result["feature_stats"]["ns"]["after"]["mean"] is None
    assets = core().artifacts(result, "empty-test")
    assert assets["clean_feature_distribution_ns_empty-test.png"].startswith(b"\x89PNG")


def test_csv_xlsx_parity_metadata_and_verified_manifest():
    source = rows()
    source[0].update(is_bug_inducing=None, labeled_at=None, label_method=None)
    source[0]["committed_at"] = "2026-01-01T14:00:00+02:00"
    parsed = []
    for fmt in ("csv", "xlsx"):
        canonical = [{key: "" if value is None else value for key, value in row.items()} for row in source]
        data = fc.encode_table(fc.COMMITS_COLUMNS, canonical, fmt)
        table, meta = core().parse_input(f"input.{fmt}", data)
        assert meta["feature_version"] == "v1" and meta["feature_state"] == "log_v1"
        assert meta["warnings"]
        verified, vm = core().parse_input(f"input.{fmt}", data, manifest(f"input.{fmt}", data))
        assert verified == table and vm["manifest_verified"] is True
        parsed.append(table)
        with pytest.raises((ValueError, fc.AppError)):
            core().parse_input(f"input.{fmt}", data, manifest(f"input.{fmt}", b"wrong"))
    assert parsed[0] == parsed[1]


@pytest.mark.parametrize("field,value", [
    ("committed_at", "not-time"), ("committed_at", "2026-02-30T00:00:00Z"),
    ("committed_at", "2026-01-01"), ("ns", "nan"), ("age", "inf"), ("ns", "1e100"),
    ("fix", "2"), ("is_bug_inducing", "2"), ("is_test", "yes"),
    ("message", "=HYPERLINK(\"x\")"), ("parent_hash", "a" * 40 + " invalid"),
])
@pytest.mark.parametrize("fmt", ["csv", "xlsx"])
def test_input_rejects_invalid_types_time_finite_formula(field, value, fmt):
    source = rows()
    source[0][field] = value
    if field == "message":
        book = Workbook()
        sheet = book.active
        sheet.append(list(fc.COMMITS_COLUMNS))
        for row in source:
            sheet.append([row[col] for col in fc.COMMITS_COLUMNS])
        buffer = io.BytesIO()
        book.save(buffer)
        data = buffer.getvalue() if fmt == "xlsx" else fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv").replace(b"Feature change", value.encode(), 1)
    else:
        data = fc.encode_table(fc.COMMITS_COLUMNS, source, fmt)
    with pytest.raises((ValueError, fc.AppError)):
        core().parse_input(f"input.{fmt}", data)


def test_duplicate_hash_schema_and_manifest_version_rejected():
    source = rows()
    source[1]["commit_hash"] = source[0]["commit_hash"].upper()
    for fmt in ("csv", "xlsx"):
        with pytest.raises((ValueError, fc.AppError)):
            core().parse_input(f"input.{fmt}", fc.encode_table(fc.COMMITS_COLUMNS, source, fmt))
        with pytest.raises((ValueError, fc.AppError)):
            core().parse_input(f"input.{fmt}", fc.encode_table(tuple(reversed(fc.COMMITS_COLUMNS)), rows(), fmt))
    content = fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv")
    bad = json.loads(manifest("input.csv", content))
    bad["config"].pop("feature_version")
    with pytest.raises((ValueError, fc.AppError)):
        core().parse_input("input.csv", content, json.dumps(bad).encode())
    with pytest.raises((ValueError, fc.AppError)):
        core().parse_input("input.csv", content, manifest("input.csv", content, feature_state="raw"))


@pytest.mark.parametrize("mode,fmt", [("preview", "csv"), ("apply", "csv"), ("apply", "xlsx")])
def test_artifacts_primary_parity_deterministic_png_and_stats(mode, fmt):
    cfg = config(mode=mode, format=fmt, features=["ns", "fix"])
    first = core().run(rows(), cfg)
    second = core().run(rows(), cfg)
    assets = core().artifacts(first, "same-run")
    repeat = core().artifacts(second, "same-run")
    assert not any("manifest" in name for name in assets)
    assert "clean_steps_stats_same-run.json" in assets and "clean_feature_stats_same-run.json" in assets
    assert "clean_stats_same-run.json" not in assets
    assert json.loads(assets["clean_steps_stats_same-run.json"]) == first["steps_stats"]
    for name, content in assets.items():
        if "stats" not in name:
            assert content == repeat[name]
            assert hashlib.sha256(content).digest() == hashlib.sha256(repeat[name]).digest()
    if mode == "preview":
        assert not any("cleaned" in name for name in assets)
    else:
        assert next(iter(assets)) == f"clean_cleaned_same-run.{fmt}"
        csv_rows, _ = core().parse_input("clean_cleaned_same-run.csv", assets["clean_cleaned_same-run.csv"])
        xlsx_rows, _ = core().parse_input("clean_cleaned_same-run.xlsx", assets["clean_cleaned_same-run.xlsx"])
        assert csv_rows == xlsx_rows
    assert first["feature_stats"]["ns"]["before"]["mean"] == 2.5
    assert first["feature_stats"]["ns"]["before"]["median"] == 2.5
    assert "histogram" in first["feature_stats"]["ns"]["after"]
    assert core().code_version() == core().code_version()


def cli_prefix(module):
    prefix = [str(PYTHON), "-I", "-B"]
    if module:
        # -I intentionally ignores PYTHONPATH; bootstrap only the local module root.
        prefix += ["-c", f"import runpy,sys; sys.path.insert(0, {str(DATA_MODEL)!r}); "
                   "runpy.run_module('preparation.clean', run_name='__main__')"]
    else:
        prefix += [str(DATA_MODEL / "preparation/clean.py")]
    return prefix


@pytest.mark.parametrize("module", [False, True])
@pytest.mark.parametrize("chain_kind", ["literal-list", "literal-object", "file-list", "file-object"])
def test_cli_isolated_no_database_and_atomic_publisher(tmp_path, module, chain_kind):
    source = tmp_path / "input.csv"
    content = fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv")
    source.write_bytes(content)
    companion = source.with_suffix(".manifest.json")
    companion_content = manifest(source.name, content)
    companion.write_bytes(companion_content)
    out = tmp_path / "outputs"
    prefix = cli_prefix(module)
    chain_data = config()["steps"]
    if chain_kind.endswith("object"):
        chain_data = {"steps": chain_data}
    chain_arg = json.dumps(chain_data)
    if chain_kind.startswith("file"):
        chain_file = tmp_path / "chain.json"
        chain_file.write_text(chain_arg)
        chain_arg = str(chain_file)
    env = {**os.environ, "PYTHONPATH": str(DATA_MODEL), "DATABASE_URL": "", "DB_HOST": "",
           "MPLCONFIGDIR": str(tmp_path / "mpl")}
    listed = subprocess.run(prefix + ["operations"], env=env, capture_output=True, text=True)
    assert listed.returncode == 0, listed.stderr
    assert [item["op"] for item in json.loads(listed.stdout)] == OPS
    args = ["run", "--input", str(source), "--chain", chain_arg,
            "--mode", "apply", "--features", "ns,fix", "--seed", "42", "--split-ratio", "0.7",
            "--format", "xlsx", "--out", str(out)]
    if module:
        args += ["--manifest", str(companion)]
    batches = []
    for _ in range(2):
        proc = subprocess.run(prefix + args, env=env, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        registered = json.loads(proc.stdout)
        assert registered["summary"]["output_rows"] == 4
        batch = out / registered["job_id"]
        batches.append(batch)
        for item in registered["outputs"]:
            assert fc.sha256((batch / item["name"]).read_bytes()) == item["sha256"]
        cleaned = next(item["name"] for item in registered["outputs"] if item["name"].endswith(".xlsx"))
        table = (batch / cleaned).read_bytes()
        verified = fc.verify_manifest(cleaned, table, (batch / Path(cleaned).with_suffix(".manifest.json")).read_bytes())
        assert verified["module"] == "clean"
        assert verified["inputs"] == [
            {"name": source.name, "sha256": fc.sha256(content), "rows": 4},
            {"name": companion.name, "sha256": fc.sha256(companion_content)},
        ]
        assert verified["config"]["feature_order"] == FEATURES
    assert batches[0] != batches[1] and all(batch.is_dir() for batch in batches)
    assert source.read_bytes() == content
    source.write_bytes(content.replace(b"Feature change", b"=BAD()", 1))
    failed = subprocess.run(prefix + args, env=env, capture_output=True, text=True)
    assert failed.returncode != 0 and json.loads(failed.stderr)["message"]
    assert set(out.iterdir()) == set(batches)


def test_fractional_timestamps_sort_chronologically_inside_training_side():
    source = rows()
    source[1]["committed_at"] = "2026-01-01T12:00:00.5Z"
    result = core().run(list(reversed(source)), config(split_ratio=0.5))
    assert [r["commit_hash"] for r in result["rows"]] == [r["commit_hash"] for r in source]


def test_missing_label_method_warns_even_without_szz_step():
    source = rows()
    source[0]["label_method"] = None
    result = core().run(source, config("label_validate"))
    assert result["rows"][0]["is_bug_inducing"] == source[0]["is_bug_inducing"]
    assert any("method" in warning.lower() for warning in result["summary"]["warnings"])


@pytest.mark.parametrize("optional", [{}, {"enabled": True}, {"params": {}}, {"enabled": False}])
def test_step_optional_fields_normalize_defaults(optional):
    raw = {"mode": "preview", "steps": [{"op": "time_split", **optional}], "split_ratio": 0.6}
    saved = copy.deepcopy(raw)
    normalized = core().validate_config(raw)
    assert normalized["steps"] == [{"op": "time_split", "enabled": optional.get("enabled", True),
                                    "params": {"ratio": 0.6}}]
    assert raw == saved
    assert core().run(rows(), raw)["summary"]["output_rows"] == 4


@pytest.mark.parametrize("op", ["log_transform", "standardize"])
def test_transforms_require_enabled_feature_align_in_registry_and_validation(op):
    catalog = {item["op"]: item for item in core().operations()}
    assert {"type": "requires", "op": "feature_align"} in catalog[op]["order_constraints"]
    assert {"type": "before", "op": op} in catalog["feature_align"]["order_constraints"]
    enabled = [op] + (["time_split"] if op == "standardize" else [])
    with pytest.raises(core().CleanError, match="requires enabled feature_align"):
        core().validate_config(config(*enabled))


@pytest.mark.parametrize("labels,window_warning,specific", [
    ([0, 1] * 5, True, None),
    ([1] + [0] * 9, False, None),
    ([1] * 10, False, None),
    ([0] * 10, False, "zero positive"),
    ([None] * 10, False, "no labeled"),
])
def test_anomaly_window_and_truthful_zero_null_warnings(labels, window_warning, specific):
    source = rows(len(labels))
    for row, label in zip(source, labels, strict=True):
        row["is_bug_inducing"] = label
    result = core().run(source, config("anomaly_exclude", features=["ns"]))
    warnings = stat(result, "anomaly_exclude")["warnings"]
    assert any("abnormal positive ratio" in w.lower() for w in warnings) is window_warning
    if specific:
        assert any(specific in w.lower() for w in warnings)
    assert [row["is_bug_inducing"] for row in result["rows"]] == labels
    assert stat(result, "anomaly_exclude")["removed"] == 0


@pytest.mark.parametrize("ratio", [0.4, 0.6, 1.0])
def test_anomaly_window_inclusive_user_bounds(ratio):
    source = rows(10)
    for i, row in enumerate(source):
        row["is_bug_inducing"] = int(i < int(ratio * 10))
    params = {} if ratio != 1 else {"anomaly_exclude": {"positive_ratio_low": 0.9, "positive_ratio_high": 1}}
    result = core().run(source, config("anomaly_exclude", params=params))
    assert any("abnormal positive ratio" in w.lower() for w in stat(result, "anomaly_exclude")["warnings"])
    assert stat(result, "anomaly_exclude")["removed"] == 0


@pytest.mark.parametrize("plot_features", [["ns"], ["fix"]])
def test_plot_selection_does_not_limit_kamei13_scaling(plot_features):
    source = rows()
    for row, value in zip(source, [1, 5, 101, 901], strict=True):
        row["nd"] = value
    result = core().run(source, config("feature_align", "log_transform", "standardize", "time_split",
                                       split_ratio=0.5, features=plot_features))
    output = result["rows"]
    assert [row["nd"] for row in output] == pytest.approx([-1, 1, 49, 449])
    assert [row["ns"] for row in output] == pytest.approx([-1, 1, 3, 5])
    assert [row["fix"] for row in output] == [row["fix"] for row in source]
    snapshot = result["config"]["scaler"]
    scaled = [feature for feature in FEATURES if feature != "fix"]
    assert snapshot["features"] == snapshot["feature_names_in_"] == scaled
    assert snapshot["n_features_in_"] == 13
    assert snapshot["plot_features"] == plot_features
    assert snapshot["var_"][scaled.index("nd")] == 4
    assert snapshot["train_hashes"] == [row["commit_hash"] for row in source[:2]]
    assert result["config"]["features"] == plot_features
    assert result["config"]["feature_order"] == result["config"]["canonical_feature_order"] == FEATURES
    assert result["config"]["feature_version"] != "v1"
    assert set(result["feature_stats"]) == set(plot_features)
    assets = core().artifacts(result, "selected")
    assert {name for name in assets if name.endswith(".png")} == {
        f"clean_feature_distribution_{feature}_selected.png" for feature in plot_features}


@pytest.mark.parametrize("field,value", [
    ("commit_hash", "A" * 40), ("commit_hash", "a" * 39),
    ("parent_hash", "A" * 40), ("parent_hash", "a" * 40 + " " + "B" * 40),
    ("parent_hash", "a" * 40 + " " + "a" * 40), ("parent_hash", " " * 40),
    ("label_method", "arbitrary"), ("label_method", "SZZ"),
    ("repo_name", ""), ("repo_name", "  "), ("author_name", None),
    ("author_name", " \t"), ("message", ""), ("message", "  "),
])
def test_canonical_text_rejected_even_with_szz_disabled(field, value):
    source = rows()
    source[0][field] = value
    saved = copy.deepcopy(source)
    with pytest.raises(core().CleanError):
        core().run(source, config("label_validate", mode="preview"))
    assert source == saved


@pytest.mark.parametrize("method", [None, "szz", "szz_lite"])
@pytest.mark.parametrize("parent", [None, "a" * 40, "a" * 40 + " " + "b" * 40])
def test_canonical_label_methods_and_lowercase_parents_accepted(method, parent):
    source = rows(1)
    source[0].update(commit_hash="c" * 40, parent_hash=parent, label_method=method)
    result = core().run(source, config("label_validate", mode="preview"))
    assert result["rows"] == source


@pytest.mark.parametrize("version", ["v" * 33, "v" * 80])
def test_feature_version_storage_limit(version):
    with pytest.raises(core().CleanError, match="feature_version"):
        core().run(rows(), config("label_validate"), metadata={"feature_version": version})
    result = core().run(rows(), config("label_validate"), metadata={"feature_version": "v" * 32})
    assert result["config"]["feature_version"] == "v" * 32


def test_scaled_output_version_also_respects_storage_limit():
    result = core().run(rows(), config("feature_align", "standardize", "time_split"),
                        metadata={"feature_version": "v" * 32})
    version = result["config"]["feature_version"]
    assert len(version) <= 32 and version.endswith("-standardized")
    assert result["config"]["source_feature_version"] == "v" * 32
    repeat = core().run(rows(), config("feature_align", "standardize", "time_split"),
                        metadata={"feature_version": "v" * 32})
    assert repeat["config"]["feature_version"] == version


def test_every_excluded_hash_and_reason_recorded_in_stats_json():
    source = rows(101)
    for row in source:
        row["parent_hash"] = "a" * 40 + " " + "b" * 40
    result = core().run(source, config("merge_filter", mode="preview", features=["ns"]))
    excluded = stat(result, "merge_filter")["excluded_samples"]
    assert len(excluded) == stat(result, "merge_filter")["removed"] == 101
    assert [item["commit_hash"] for item in excluded] == [row["commit_hash"] for row in source]
    assert all(item["reason"] for item in excluded)
    assets = core().artifacts(result, "all-excluded")
    assert json.loads(assets["clean_steps_stats_all-excluded.json"])[0]["excluded_samples"] == excluded


def test_every_modified_hash_recorded_in_stats_json():
    result = core().run(rows(101), config("feature_align", "standardize", "time_split", features=["ns"]))
    modified = stat(result, "standardize")["modified_samples"]
    assert len(modified) == stat(result, "standardize")["modified"] == 101
    assets = core().artifacts(result, "all-modified")
    exported = next(item for item in json.loads(assets["clean_steps_stats_all-modified.json"])
                    if item["op"] == "standardize")
    assert exported["modified_samples"] == modified


def test_log_transform_skips_standardized_without_claiming_log_identity():
    source = rows()
    metadata = {"feature_version": "v1-standardized", "feature_state": "standardized_v1"}
    result = core().run(source, config("feature_align", "log_transform"), metadata=metadata)
    warnings = stat(result, "log_transform")["warnings"]
    assert any("skip" in w.lower() and "standardized" in w.lower() for w in warnings)
    assert not any("already contains log-v1" in w.lower() for w in warnings)
    assert result["config"]["feature_state"] == metadata["feature_state"]
    assert result["config"]["feature_version"] == metadata["feature_version"]
    assert result["rows"] == source and stat(result, "log_transform")["modified"] == 0


def test_szz_reuse_does_not_call_fix_predicate(monkeypatch):
    def unexpected(_):
        pytest.fail("Fix predicate belongs to D5, not SZZ evidence reuse")
    monkeypatch.setattr(core().original02, "is_fix_commit", unexpected)
    result = core().run(rows(), config("szz_label"))
    assert result["rows"] == rows()


def test_exported_xlsx_trailing_null_roundtrips_shared_codec():
    source = rows()
    source[-1].update(is_bug_inducing=None, labeled_at=None, label_method=None, author_email=None, parent_hash=None)
    result = core().run(source, config("label_validate", features=["ns"]))
    assets = core().artifacts(result, "trailing-null")
    columns, parsed = fc.read_table("output.xlsx", assets["clean_cleaned_trailing-null.xlsx"])
    assert tuple(columns) == fc.COMMITS_COLUMNS
    assert core()._rows(parsed) == result["rows"]


def test_malformed_undimensioned_xlsx_not_repaired_by_clean():
    source = rows()
    source[-1][fc.COMMITS_COLUMNS[-1]] = None
    content = fc.encode_table(fc.COMMITS_COLUMNS, source, "xlsx")
    with pytest.raises(fc.AppError):
        fc.read_table("malformed.xlsx", content)
    with pytest.raises(fc.AppError):
        core().parse_input("malformed.xlsx", content)


@pytest.mark.parametrize("target", ["chain", "input", "manifest"])
def test_cli_stats_size_before_read_and_does_not_echo_paths(tmp_path, monkeypatch, capsys, target):
    source = tmp_path / "private-input.csv"
    content = fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv")
    source.write_bytes(content)
    chain = tmp_path / "private-chain.json"
    chain.write_text(json.dumps({"steps": []}))
    companion = tmp_path / "private-manifest.json"
    companion.write_bytes(manifest(source.name, content))
    limit = len(content) + 1
    oversized = {"chain": chain, "input": source, "manifest": companion}[target]
    oversized.write_bytes(b" " * (limit + 1))
    monkeypatch.setattr(fc, "MAX_UPLOAD_BYTES", limit)
    read_bytes = Path.read_bytes
    def guarded_read(path):
        assert path != oversized, "Oversized file must be rejected by stat before reading"
        return read_bytes(path)
    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    chain_arg = str(chain) if target == "chain" else json.dumps({"steps": []})
    code = core().main(["run", "--input", str(source), "--chain", chain_arg, "--manifest", str(companion),
                        "--mode", "preview", "--out", str(tmp_path / "outputs")])
    captured = capsys.readouterr()
    assert code == 2
    assert str(tmp_path) not in captured.err
    assert "size" in json.loads(captured.err)["message"].lower()
    assert not (tmp_path / "outputs").exists()


@pytest.mark.parametrize("target", ["chain", "input", "manifest"])
def test_cli_missing_file_errors_do_not_echo_paths(tmp_path, capsys, target):
    source = tmp_path / "private-input.csv"
    content = fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv")
    source.write_bytes(content)
    companion = tmp_path / "private-manifest.json"
    companion.write_bytes(manifest(source.name, content))
    chain = tmp_path / "private-chain.json"
    chain.write_text(json.dumps({"steps": []}))
    {"chain": chain, "input": source, "manifest": companion}[target].unlink()
    chain_arg = str(chain) if target == "chain" else json.dumps({"steps": []})
    code = core().main(["run", "--input", str(source), "--chain", chain_arg, "--manifest", str(companion),
                        "--mode", "preview", "--out", str(tmp_path / "outputs")])
    assert code == 2
    captured = capsys.readouterr()
    assert str(tmp_path) not in captured.err
    assert json.loads(captured.err)["message"]


def test_core_imports_no_database_or_online_modules():
    core()
    assert "app.db" not in sys.modules and "app.services.storage" not in sys.modules
    assert "preparation.collect" not in sys.modules
