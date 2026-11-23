"""AI-generated/unreviewed W5 train CORE tests; synthetic fixtures, no database.

Covers registry counts/schema single source, config validation, strict temporal
split, unlabeled exclusion, REAL per-algo failure isolation (tabnet stratify),
model package structure + GNU checksum, determinism, artifacts and isolated CLI.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
PYTHON = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
sys.path.insert(0, str(DATA_MODEL))
sys.path.insert(0, str(ROOT / "backend"))
from app.services import file_contracts as fc

FEATURES = list(fc.FEATURE_COLUMNS)
METRIC_KEYS = ("auc", "f1", "precision", "recall", "accuracy")
METRICS_COLUMNS = ("model_name", "line", "metric", "value", "threshold", "n", "pos_rate",
                   "dataset_version", "model_version", "computed_at")


def core():
    assert (DATA_MODEL / "pipelines/train.py").is_file(), "W5 train core missing"
    return importlib.import_module("pipelines.train")


def registry():
    assert (DATA_MODEL / "pipelines/registry.py").is_file(), "W5 registry missing"
    return importlib.import_module("pipelines.registry")


def expert_model():
    return importlib.import_module("pipelines.expert.model")


def expert_config():
    return importlib.import_module("pipelines.expert.config")


def rows(count=40, seed=0):
    rng = np.random.default_rng(seed)
    base = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for i in range(count):
        label = i % 2
        row = dict.fromkeys(fc.COMMITS_COLUMNS, None)
        row.update(commit_hash=f"{i + 1:040x}", repo_name="fixture", author_name="测试",
                   author_email="test@example.invalid",
                   committed_at=(base + timedelta(seconds=i)).isoformat().replace("+00:00", "Z"),
                   message="Feature change", parent_hash=f"{i:040x}" if i else None,
                   is_bug_inducing=label, labeled_at="2026-02-01T00:00:00Z", is_test=0,
                   label_method="szz")
        row.update({feature: float(rng.normal()) for feature in FEATURES})
        row["ns"] = float(label * 3 + rng.normal())
        row["fix"] = label
        result.append(row)
    return result


def config(algos=("lr",), **extra):
    return {"line": "expert", "algos": list(algos), **extra}


def subitem(result, algo):
    return next(item for item in result["models"] if item["algo"] == algo)


# ── registry ────────────────────────────────────────────────────────────────

def test_registry_counts_families_and_requirements():
    reg = registry()
    assert reg.LINES == ("expert", "semantic", "fused", "e2e")
    catalog = reg.algorithms()
    assert len(catalog) == 37
    assert sum(item["enabled"] for item in catalog) == 25
    for line, total, enabled in (("expert", 12, 8), ("semantic", 12, 8), ("fused", 12, 8), ("e2e", 1, 1)):
        items = [item for item in catalog if item["line"] == line]
        assert len(items) == total and sum(item["enabled"] for item in items) == enabled
    assert len({item["family"] for item in catalog}) >= 2
    defaults = set(expert_config().DEFAULT_MODELS)
    for item in catalog:
        assert set(item) == {"line", "algo", "family", "enabled", "description",
                             "hyperparams_schema", "input_requirements"}
        assert type(item["enabled"]) is bool
        if item["line"] != "e2e":
            assert item["enabled"] is (item["algo"] in defaults)
            assert item["family"] == expert_model().MODEL_CLASS[item["algo"]]
    e2e = next(item for item in catalog if item["line"] == "e2e")
    assert e2e["algo"] == "codebert_e2e" and e2e["enabled"] is True
    assert e2e["family"] == "神经网络（深度学习）"
    requirements = {item["line"]: item["input_requirements"] for item in catalog}
    assert requirements["expert"] == "canonical commits/cleaned table (Kamei14)"
    assert requirements["semantic"] == ("768-dim CodeBERT embeddings npz keyed by commit_hash "
                                        "(not provided by table upload contract)")
    assert requirements["fused"] == "Kamei14 + 768-dim embeddings"
    assert requirements["e2e"] == "commit_text message+diff dataset + transformers fine-tuning"


def test_registry_line_and_enabled_filters():
    reg = registry()
    assert len(reg.algorithms(line="expert")) == 12
    assert len(reg.algorithms(line="expert", enabled_only=True)) == 8
    assert len(reg.algorithms(enabled_only=True)) == 25
    assert [item["algo"] for item in reg.algorithms(line="e2e")] == ["codebert_e2e"]


def test_schema_defaults_equal_build_model_get_params():
    reg, model = registry(), expert_model()
    by_line = {}
    for item in reg.algorithms():
        if item["line"] == "e2e":
            continue
        params = model.build_model(item["algo"], 42).get_params()
        schema = item["hyperparams_schema"]
        assert schema, item["algo"]
        for param in schema:
            assert set(param) == {"name", "type", "default", "min", "max", "choices", "description"}
            assert param["name"] in params, (item["algo"], param["name"])
            assert param["default"] == params[param["name"]], (item["algo"], param["name"])
        by_line.setdefault(item["algo"], {})[item["line"]] = schema
    for algo, lines in by_line.items():
        assert lines["expert"] == lines["semantic"] == lines["fused"], algo
    tuned = {item["algo"]: {p["name"] for p in item["hyperparams_schema"]}
             for item in reg.algorithms(line="expert")}
    assert tuned["lr"] == {"lr__C", "lr__max_iter"}
    assert tuned["rf"] == {"n_estimators", "max_depth", "min_samples_leaf"}
    assert tuned["xgb"] == {"n_estimators", "learning_rate", "max_depth", "subsample", "colsample_bytree"}
    assert tuned["lgbm"] == {"n_estimators", "learning_rate", "num_leaves", "subsample", "colsample_bytree"}
    assert tuned["et"] == {"n_estimators", "min_samples_leaf"}
    assert tuned["svm"] == {"svm__C", "svm__gamma"}
    assert tuned["nb"] == {"var_smoothing"}
    assert tuned["dt"] == {"max_depth", "min_samples_leaf"}
    assert tuned["knn"] == {"knn__n_neighbors"}
    assert tuned["mlp"] == {"mlp__max_iter", "mlp__alpha"}
    assert tuned["mlp_deep"] == {"mlp__max_iter", "mlp__alpha", "mlp__n_iter_no_change", "mlp__validation_fraction"}
    assert tuned["tabnet"] == {"tabnet__max_epochs", "tabnet__patience", "tabnet__validation_fraction"}
    gamma = next(p for p in tuned if p == "svm")
    schema = next(item["hyperparams_schema"] for item in reg.algorithms(line="expert") if item["algo"] == gamma)
    assert next(p["choices"] for p in schema if p["name"] == "svm__gamma") == ["scale", "auto"]


@pytest.mark.parametrize("line,algos,hyperparams", [
    ("bogus", ["lr"], {}),
    ("expert", ["not-a-model"], {}),
    ("expert", ["nb"], {}),  # registered but default-off
    ("expert", ["mlp"], {}),
    ("semantic", ["lr"], {}),  # input requirements unsatisfiable from table upload
    ("fused", ["lr"], {}),
    ("e2e", ["codebert_e2e"], {}),
    ("expert", ["lr"], {"lr": {"bogus": 1}}),
    ("expert", ["lr"], {"lr": {"lr__C": -1}}),
    ("expert", ["lr"], {"lr": {"lr__C": "1"}}),
    ("expert", ["rf"], {"rf": {"n_estimators": True}}),
    ("expert", ["rf"], {"rf": {"n_estimators": 1.5}}),
    ("expert", ["rf"], {"rf": {"n_estimators": 0}}),
    ("expert", ["svm"], {"svm": {"svm__gamma": "linear"}}),
    ("expert", ["lr"], {"rf": {"n_estimators": 10}}),
    ("expert", [], {}),
    ("expert", ["lr", "lr"], {}),
])
def test_validate_selection_rejects(line, algos, hyperparams):
    reg = registry()
    with pytest.raises(reg.TrainError) as excinfo:
        reg.validate_selection(line, algos, hyperparams)
    assert excinfo.value.code == 40001


def test_validate_selection_normalizes():
    reg = registry()
    raw = {"lr": {"lr__C": 0.5}}
    saved = copy.deepcopy(raw)
    normalized = reg.validate_selection("expert", ["lr", "rf"], raw)
    assert normalized["line"] == "expert" and normalized["algos"] == ["lr", "rf"]
    assert normalized["hyperparams"]["lr"] == {"lr__C": 0.5}
    assert raw == saved


# ── config validation ───────────────────────────────────────────────────────

def test_validate_config_defaults():
    normalized = core().validate_config(config())
    assert normalized["split"] == {"ratio": 0.7}
    assert normalized["seed"] == 42
    assert normalized["decision_threshold"] == 0.5
    assert normalized["register"] is False and normalized["auto_load"] is False
    assert normalized["hyperparams"] == {}


@pytest.mark.parametrize("change", [
    {"unknown": 1}, {"algos": []}, {"algos": ["lr", "lr"]}, {"algos": "lr"},
    {"split": {"random": True}}, {"split": {"ratio": 0.7, "time_boundary": "2026-01-01T00:00:20Z"}},
    {"split": {"ratio": 0}}, {"split": {"ratio": 1}}, {"split": {"ratio": "0.7"}},
    {"split": {"ratio": True}}, {"split": {}}, {"split": {"time_boundary": "2026-01-01"}},
    {"seed": True}, {"seed": -1}, {"seed": 1.0},
    {"decision_threshold": 0}, {"decision_threshold": 1}, {"decision_threshold": "0.5"},
    {"register": 1}, {"auto_load": "yes"}, {"hyperparams": []},
])
def test_validate_config_rejects(change):
    with pytest.raises(core().TrainError):
        core().validate_config({**config(), **change})


def test_validate_config_time_boundary_normalized_to_z():
    normalized = core().validate_config(config(split={"time_boundary": "2026-01-01T00:00:20+00:00"}))
    assert normalized["split"] == {"time_boundary": "2026-01-01T00:00:20Z"}


def test_train_error_is_value_error_with_code():
    error = core().TrainError("x")
    assert isinstance(error, ValueError) and error.code == 40001


# ── run: split / labels ─────────────────────────────────────────────────────

def test_run_rejects_empty_and_same_second_boundary():
    source = rows(4)
    source[2]["committed_at"] = "2026-01-01T00:00:01.5Z"  # same second as row 1
    with pytest.raises(core().TrainError):
        core().run(source, config(split={"ratio": 0.5}))
    for count in (0, 1):
        with pytest.raises(core().TrainError):
            core().run(rows(count), config())


def test_run_excludes_unlabeled_sorts_and_records_split():
    source = rows(40)
    for index in (3, 17):
        source[index].update(is_bug_inducing=None, labeled_at=None, label_method=None)
    excluded = {source[3]["commit_hash"], source[17]["commit_hash"]}
    result = core().run(list(reversed(source)), config())
    summary = result["summary"]
    assert summary["input_rows"] == 40 and summary["labeled_rows"] == 38
    assert summary["unlabeled_rows"] == 2
    assert summary["train_rows"] == 26 and summary["test_rows"] == 12  # floor(38*0.7)
    split = result["config"]["split"]
    assert split["ratio"] == 0.7
    hashes = split["train_hashes"] + split["test_hashes"]
    assert len(hashes) == 38 and not excluded & set(hashes)
    assert split["train_max"] < split["test_min"]
    ordered = sorted((r for r in source if r["is_bug_inducing"] is not None),
                     key=lambda r: (r["committed_at"], r["commit_hash"]))
    assert hashes == [r["commit_hash"] for r in ordered]
    assert result["config"]["feature_version"] == "v1"
    assert re.fullmatch(r"[0-9a-f]{64}", result["config"]["input_sha"])


def test_run_time_boundary_inclusive_train_side():
    source = rows(40)
    boundary = source[19]["committed_at"]
    result = core().run(source, config(split={"time_boundary": boundary}))
    assert result["summary"]["train_rows"] == 20 and result["summary"]["test_rows"] == 20
    split = result["config"]["split"]
    assert split["time_boundary"] == boundary
    assert split["train_max"] == boundary and split["test_min"] == source[20]["committed_at"]
    assert split["train_hashes"] == [r["commit_hash"] for r in source[:20]]
    for bad in ("2025-12-31T00:00:00Z", "2027-01-01T00:00:00Z"):
        with pytest.raises(core().TrainError):
            core().run(source, config(split={"time_boundary": bad}))


# ── run: success path / metrics rows ────────────────────────────────────────

def test_run_success_subitems_metrics_rows_and_comparison():
    result = core().run(rows(), config(("lr", "rf", "et")))
    assert result["summary"]["success_count"] == 3 and result["summary"]["failed_count"] == 0
    for item in result["models"]:
        assert set(item) >= {"algo", "model_name", "version_key", "feature_version", "status",
                             "metrics", "warnings", "error", "elapsed_ms", "hyperparams"}
        assert item["status"] == "success" and item["error"] is None
        assert re.fullmatch(rf"{item['algo']}_[0-9a-f]{{8}}_v1", item["model_name"])
        assert re.fullmatch(r"[0-9a-f]{16}", item["version_key"])
        assert set(item["metrics"]) == set(METRIC_KEYS)
        assert item["elapsed_ms"] >= 0
    assert len(result["metrics_rows"]) == 15
    test_pos = sum(r["is_bug_inducing"] for r in rows()[28:])
    for row in result["metrics_rows"]:
        assert tuple(row) == METRICS_COLUMNS
        assert row["n"] == 12 and row["pos_rate"] == test_pos / 12
        assert row["threshold"] == 0.5
        assert row["dataset_version"] == result["config"]["input_sha"]
        assert row["model_version"] == subitem(result, row["model_name"].split("_")[0])["version_key"]
    comparison = result["comparison"]
    assert comparison["line"] == "expert" and comparison["seed"] == 42
    assert comparison["models"] == result["models"]
    assert comparison["feature_version"] == "v1"
    assert comparison["input_sha"] == result["config"]["input_sha"]
    assert comparison["split"] == result["config"]["split"]


def test_run_progress_events():
    events = []
    core().run(rows(), config(("lr", "rf")), progress=lambda *args: events.append(args))
    assert [algo for algo, _, _ in events] == ["lr", "rf"]
    assert [done for _, done, _ in events] == [1, 2]
    assert all(total == 2 for _, _, total in events)


# ── REAL failure isolation ──────────────────────────────────────────────────

def single_positive_rows():
    """Train side (first 14 of 20) has exactly ONE positive: tabnet's internal
    stratified validation split must fail while lr still fits both classes."""
    source = rows(20)
    labels = [0] * 14 + [1, 0, 1, 0, 1, 0]
    labels[5] = 1
    for row, label in zip(source, labels, strict=True):
        row["is_bug_inducing"] = label
        row["fix"] = label
    return source


def test_failure_isolation_tabnet_stratify_fails_lr_succeeds():
    result = core().run(single_positive_rows(), config(("lr", "tabnet")))
    lr, tabnet = subitem(result, "lr"), subitem(result, "tabnet")
    assert lr["status"] == "success" and lr["error"] is None
    assert tabnet["status"] == "failed" and tabnet["error"]
    assert "class" in tabnet["error"].lower()  # sklearn stratify least-populated-class
    assert tabnet["metrics"] is None
    assert result["summary"]["success_count"] == 1 and result["summary"]["failed_count"] == 1
    assets = core().artifacts(result, "iso-job")
    assert "train_lr_model_package_iso-job.zip" in assets
    assert not any("tabnet" in name for name in assets)
    assert len(result["metrics_rows"]) == 5
    assert "tabnet" in result["log"] and tabnet["error"][:40] in result["log"]


def test_single_class_train_side_fails_lr_tabnet_but_rf_degenerates_cleanly():
    source = rows(12)
    for i, row in enumerate(source):
        row["is_bug_inducing"] = 0 if i < 8 else 1
        row["fix"] = row["is_bug_inducing"]
    result = core().run(source, config(("lr", "tabnet", "rf")))
    assert subitem(result, "lr")["status"] == "failed"
    assert subitem(result, "tabnet")["status"] == "failed"
    rf = subitem(result, "rf")
    assert rf["status"] == "success"
    assert rf["metrics"]["auc"] is None
    assert "single_class_test_auc_undefined" in rf["warnings"]
    assert result["summary"]["success_count"] == 1 and result["summary"]["failed_count"] == 2
    assets = core().artifacts(result, "degenerate")
    assert "train_rf_model_package_degenerate.zip" in assets
    csv_text = assets["train_metrics_degenerate.csv"].decode("utf-8-sig")
    auc_line = next(line for line in csv_text.splitlines() if ",auc," in line)
    assert auc_line.split(",")[3] == ""  # None -> empty, not 0


# ── package structure / checksum ────────────────────────────────────────────

def test_package_structure_meta_and_gnu_checksum():
    result = core().run(rows(), config())
    item = subitem(result, "lr")
    assets = core().artifacts(result, "pkg-job")
    package = assets["train_lr_model_package_pkg-job.zip"]
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        names = archive.namelist()
        assert set(names) == {"lr.pkl", "feature_order.txt", "model_meta.json", "checksum.sha256"}
        assert archive.read("lr.pkl")
        model = joblib.load(io.BytesIO(archive.read("lr.pkl")))
        assert hasattr(model, "predict_proba")
        assert archive.read("feature_order.txt") == ("\n".join(FEATURES) + "\n").encode()
        meta = json.loads(archive.read("model_meta.json"))
        assert meta["model_name"] == item["model_name"]
        assert meta["line"] == "expert" and meta["algo"] == "lr"
        assert meta["version_key"] == item["version_key"]
        assert meta["feature_version"] == "v1" and meta["seed"] == 42
        assert meta["trained_at"].endswith("Z")
        assert meta["hyperparams_snapshot"] == {}
        assert meta["feature_order"] == FEATURES
        split = meta["split"]
        assert split["ratio"] == 0.7
        assert set(split) == {"ratio", "train_max", "test_min", "train_hashes", "test_hashes"}
        assert split["train_hashes"] == result["config"]["split"]["train_hashes"]
        checksum = archive.read("checksum.sha256").decode()
        covered = {}
        for line in checksum.splitlines():
            match = re.fullmatch(r"([0-9a-f]{64})  (\S+)", line)
            assert match, line
            covered[match.group(2)] = match.group(1)
        assert set(covered) == set(names) - {"checksum.sha256"}
        for name, digest in covered.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest


# ── determinism / hyperparams ───────────────────────────────────────────────

def test_determinism_same_seed_same_identity_and_metrics():
    overrides = {"rf": {"n_estimators": 10, "min_samples_leaf": 1}}
    first = core().run(rows(), config(("lr", "rf"), hyperparams=overrides, seed=42))
    second = core().run(rows(), config(("lr", "rf"), hyperparams=overrides, seed=42))
    for algo in ("lr", "rf"):
        a, b = subitem(first, algo), subitem(second, algo)
        assert a["model_name"] == b["model_name"]
        assert a["version_key"] == b["version_key"]
        assert a["metrics"] == b["metrics"]  # exact floats, not weight bytes
    other = core().run(rows(), config(("lr",), seed=43))
    assert subitem(other, "lr")["version_key"] != subitem(first, "lr")["version_key"]


def test_hyperparam_overrides_applied_and_fingerprinted():
    overrides = {"lr": {"lr__C": 0.5, "lr__max_iter": 200}}
    result = core().run(rows(), config(hyperparams=overrides))
    item = subitem(result, "lr")
    assert item["hyperparams"] == overrides["lr"]
    baseline = core().run(rows(), config())
    assert item["model_name"] != subitem(baseline, "lr")["model_name"]
    assets = core().artifacts(result, "hp-job")
    with zipfile.ZipFile(io.BytesIO(assets["train_lr_model_package_hp-job.zip"])) as archive:
        meta = json.loads(archive.read("model_meta.json"))
        assert meta["hyperparams_snapshot"] == overrides["lr"]
        model = joblib.load(io.BytesIO(archive.read("lr.pkl")))
        assert model.get_params()["lr__C"] == 0.5
        assert model.get_params()["lr__max_iter"] == 200


# ── artifacts / figures / code version ──────────────────────────────────────

def test_artifacts_names_figures_log_and_comparison():
    result = core().run(rows(), config(("lr", "rf")))
    assets = core().artifacts(result, "art-job")
    expected = {"train_lr_model_package_art-job.zip", "train_rf_model_package_art-job.zip",
                "train_metrics_art-job.csv", "train_comparison_art-job.json",
                "train_roc_art-job.png", "train_pr_art-job.png",
                "train_confusion_art-job.png", "train_metric_bars_art-job.png",
                "train_log_art-job.md"}
    assert set(assets) == expected
    for name in ("train_roc_art-job.png", "train_pr_art-job.png",
                 "train_confusion_art-job.png", "train_metric_bars_art-job.png"):
        assert assets[name].startswith(b"\x89PNG")
    assert json.loads(assets["train_comparison_art-job.json"]) == result["comparison"]
    log = assets["train_log_art-job.md"].decode()
    assert "lr" in log and "rf" in log and "elapsed" in log
    columns, table = fc.read_table("train_metrics_art-job.csv", assets["train_metrics_art-job.csv"])
    assert tuple(columns) == METRICS_COLUMNS and len(table) == 10
    repeat = core().artifacts(core().run(rows(), config(("lr", "rf"))), "art-job")
    for name in ("train_roc_art-job.png", "train_pr_art-job.png",
                 "train_confusion_art-job.png", "train_metric_bars_art-job.png"):
        assert assets[name] == repeat[name]  # deterministic figure bytes


def test_figures_annotate_single_class_test_side():
    source = rows(12)
    for i, row in enumerate(source):
        row["is_bug_inducing"] = 0 if i < 8 else 1
        row["fix"] = row["is_bug_inducing"]
    result = core().run(source, config(("rf",)))
    assets = core().artifacts(result, "single-class")
    assert assets["train_roc_single-class.png"].startswith(b"\x89PNG")
    assert assets["train_pr_single-class.png"].startswith(b"\x89PNG")


def test_code_version_stable():
    version = core().code_version()
    assert version == core().code_version()
    assert version.startswith("train-sha256:")


# ── isolated CLI (python -I, no DB) ─────────────────────────────────────────

def cli_prefix(module):
    prefix = [str(PYTHON), "-I", "-B"]
    if module:
        prefix += ["-c", f"import runpy,sys; sys.path.insert(0, {str(DATA_MODEL)!r}); "
                   "runpy.run_module('pipelines.train', run_name='__main__')"]
    else:
        prefix += [str(DATA_MODEL / "pipelines/train.py")]
    return prefix


def cli_env(tmp_path):
    return {**os.environ, "DATABASE_URL": "", "DB_HOST": "", "MPLCONFIGDIR": str(tmp_path / "mpl")}


@pytest.mark.parametrize("module", [False, True])
def test_cli_algorithms_run_compare_isolated(tmp_path, module):
    prefix = cli_prefix(module)
    env = cli_env(tmp_path)
    listed = subprocess.run(prefix + ["algorithms", "--line", "expert", "--enabled-only"],
                            env=env, capture_output=True, text=True)
    assert listed.returncode == 0, listed.stderr
    items = json.loads(listed.stdout)
    assert len(items) == 8 and all(item["enabled"] for item in items)
    source = tmp_path / "input.csv"
    content = fc.encode_table(fc.COMMITS_COLUMNS, rows(), "csv")
    source.write_bytes(content)
    hyperparams = tmp_path / "hyperparams.json"
    hyperparams.write_text(json.dumps({"lr": {"lr__C": 0.5}}))
    out = tmp_path / "outputs"
    args = ["run", "--input", str(source), "--line", "expert", "--algos", "lr,rf",
            "--hyperparams", str(hyperparams), "--split-ratio", "0.7", "--seed", "42",
            "--threshold", "0.5", "--out", str(out)]
    batches = []
    job_id = None
    for _ in range(2):
        proc = subprocess.run(prefix + args, env=env, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        registered = json.loads(proc.stdout)
        job_id = registered["job_id"]
        assert registered["summary"]["success_count"] == 2
        batch = out / job_id
        batches.append(batch)
        for item in registered["outputs"]:
            assert fc.sha256((batch / item["name"]).read_bytes()) == item["sha256"]
        package = f"train_lr_model_package_{job_id}.zip"
        verified = fc.verify_manifest(package, (batch / package).read_bytes(),
                                      (batch / f"train_lr_model_package_{job_id}.manifest.json").read_bytes())
        assert verified["module"] == "train"
        assert verified["inputs"] == [{"name": "input.csv", "sha256": fc.sha256(content), "rows": 40}]
        assert verified["config"]["hyperparams"] == {"lr": {"lr__C": 0.5}}
        assert verified["config"]["register"] is False and verified["config"]["auto_load"] is False
    assert batches[0] != batches[1] and all(batch.is_dir() for batch in batches)
    compared = subprocess.run(prefix + ["compare", "--job", job_id, "--out", str(out)],
                              env=env, capture_output=True, text=True)
    assert compared.returncode == 0, compared.stderr
    ranking = json.loads(compared.stdout)
    aucs = [item["auc"] for item in ranking["models"]]
    assert aucs == sorted(aucs, reverse=True)
    failed = subprocess.run(prefix + ["run", "--input", str(source), "--line", "expert",
                                      "--algos", "bogus", "--out", str(out)],
                            env=env, capture_output=True, text=True)
    assert failed.returncode != 0
    assert json.loads(failed.stderr)["code"] == 40001
    assert set(out.iterdir()) == set(batches)  # no partial batch on error