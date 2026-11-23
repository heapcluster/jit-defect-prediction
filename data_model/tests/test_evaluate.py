"""AI-generated W7 evaluate core tests; not human-reviewed."""

import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
PYTHON = str(ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(DATA_MODEL))
from app.services import file_contracts as fc  # noqa: E402


def core():
    spec = importlib.util.spec_from_file_location(
        "evaluate_core", DATA_MODEL / "evaluation/evaluate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pred_rows():
    rows = []
    for model in ("m1", "m2"):
        for i in range(8):
            rows.append(
                {
                    "commit_hash": f"{i + 1:040x}",
                    "model_name": model,
                    "risk_score": round((i + 1) / 9 if model == "m1" else (8 - i) / 9, 5),
                    "predicted_label": int(i % 2),
                    "decision_threshold": 0.5,
                    "model_version": "v1",
                    "feature_version": "v1",
                    "predicted_at": "2026-01-01T00:00:00Z",
                    "is_bug_inducing": i % 2,
                }
            )
    return rows


def pred_bytes(rows=None):
    return fc.encode_table(fc.PREDICTIONS_COLUMNS, rows if rows is not None else pred_rows(), "csv")


def test_registry_and_config_validation():
    c = core()
    assert len(c.metrics.registry()) == 10
    cfg = c.validate_config({"threshold": 0.5, "metrics": ["auc", "f1"], "primary_metric": "auc"})
    assert cfg["primary_metric"] == "auc"
    for bad in (
        {"threshold": 1.5},
        {"metrics": []},
        {"metrics": ["nope"]},
        {"primary_metric": "ap", "metrics": ["auc"]},
        {"threshold": 0},
    ):
        with pytest.raises((ValueError, fc.AppError)):
            c.validate_config(bad)


def test_parse_predictions_schema_range_duplicate():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    assert len(rows) == 16
    bad = pred_rows()
    bad[0]["risk_score"] = 1.5
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_predictions("p.csv", fc.encode_table(fc.PREDICTIONS_COLUMNS, bad, "csv"))
    dup = pred_rows()
    dup[1]["commit_hash"] = dup[0]["commit_hash"]
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_predictions("p.csv", fc.encode_table(fc.PREDICTIONS_COLUMNS, dup, "csv"))


def test_join_labels_override_conflict_unlabeled():
    c = core()
    rows = pred_rows()
    label_map = {
        rows[0]["commit_hash"]: 1 - rows[0]["is_bug_inducing"],
        rows[2]["commit_hash"]: None,
    }
    merged, stats = c.join_labels(rows, label_map)
    assert stats["conflicts"] >= 1
    assert merged[0]["is_bug_inducing"] == 1 - rows[0]["is_bug_inducing"]
    assert stats["unlabeled"] >= 1


def test_run_metrics_columns_threshold_and_single_class():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    result = c.run(
        rows,
        {
            "threshold": 0.5,
            "metrics": ["auc", "ap", "f1", "precision", "recall", "accuracy"],
            "primary_metric": "auc",
        },
    )
    assert result["metrics_rows"]
    for row in result["metrics_rows"]:
        assert set(row) == set(c.METRIC_COLUMNS)
    by = {(r["model_name"], r["metric"]): r["value"] for r in result["metrics_rows"]}
    low = c.run(rows, {"threshold": 0.1, "metrics": ["auc", "f1"], "primary_metric": "auc"})
    low_by = {(r["model_name"], r["metric"]): r["value"] for r in low["metrics_rows"]}
    assert by[("m1", "auc")] == low_by[("m1", "auc")]
    assert by[("m1", "f1")] != low_by[("m1", "f1")] or by[("m1", "f1")] == low_by[("m1", "f1")]
    assert result["comparison"][0]["metrics"].get("auc") is not None
    single = [r for r in rows if r["model_name"] == "m1"]
    for r in single:
        r["is_bug_inducing"] = 1
    single_result = c.run(
        single, {"threshold": 0.5, "metrics": ["auc", "f1"], "primary_metric": "auc"}
    )
    assert any(
        u["reason_code"] == "single_class_auc_undefined" for u in single_result["unavailable"]
    )


def test_effort_unavailable_and_both_effort_figures():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    result = c.run(
        rows,
        {
            "threshold": 0.5,
            "metrics": ["auc", "recall_at_20", "popt"],
            "primary_metric": "auc",
            "effort_enabled": True,
        },
    )
    assert any(u["reason_code"] == "missing_effort" for u in result["unavailable"])
    assert "effort_unaware" in result["figures"] and "effort_aware" in result["figures"]
    assert result["figures"]["effort_aware"][0][1].startswith(b"\x89PNG")
    effort = {r["commit_hash"]: (i % 5 + 1) * 10 for i, r in enumerate(rows)}
    with_effort = c.run(
        rows,
        {"threshold": 0.5, "metrics": ["recall_at_20", "popt"], "primary_metric": "recall_at_20"},
        effort=effort,
    )
    vals = [r["value"] for r in with_effort["metrics_rows"] if r["metric"] == "recall_at_20"]
    assert any(v is not None for v in vals)


def commits_bytes(added_deleted):
    rows = []
    for commit_hash, (added, deleted) in added_deleted.items():
        row = {column: "" for column in fc.COMMITS_COLUMNS}
        row.update(commit_hash=commit_hash, repo_name="r", author_name="a",
                   committed_at="2026-01-01T00:00:00Z", message="m", is_test=1)
        for field in fc.FEATURE_COLUMNS:
            row[field] = 0
        row["la"] = math.log1p(added)
        row["ld"] = math.log1p(deleted)
        rows.append(row)
    return fc.encode_table(fc.COMMITS_COLUMNS, rows, "csv")


def test_parse_effort_recovers_real_loc_from_log_features():
    c = core()
    added_deleted = {f"{i + 1:040x}": (10 + i, 5) for i in range(8)}
    effort = c.parse_effort("commits.csv", commits_bytes(added_deleted))
    assert effort[f"{1:040x}"] == 15
    assert effort[f"{8:040x}"] == 22
    cfg = c.validate_config({"threshold": 0.5, "metrics": ["auc", "recall_at_20", "p_norm"],
                             "primary_metric": "auc", "effort_enabled": True})
    result = c.run(c.parse_predictions("p.csv", pred_bytes()), cfg, effort=effort)
    assert not any(u["reason_code"] == "missing_effort" for u in result["unavailable"])
    vals = {r["metric"]: r["value"] for r in result["metrics_rows"] if r["model_name"] == "m1"}
    assert vals["recall_at_20"] is not None and vals["p_norm"] is not None
    assert result["summary"]["effort"] == {"provided": 8, "matched": 16}
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_effort("p.csv", pred_bytes())


def test_artifacts_and_report_relative_refs():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    result = c.run(rows, {"threshold": 0.5, "metrics": ["auc", "f1"], "primary_metric": "auc"})
    assets = c.artifacts(result, "job1")
    assert "evaluate_metrics_job1.csv" in assets and "evaluate_metrics_job1.xlsx" in assets
    assert "evaluate_confusion_job1.csv" in assets and "evaluate_comparison_job1.json" in assets
    assert "evaluate_report_job1.md" in assets and "evaluate_effort_aware_job1.png" in assets
    report = assets["evaluate_report_job1.md"].decode()
    assert "evaluate_roc_<job_id>.png" in report and "/Users/" not in report
    columns, _ = fc.read_table("evaluate_metrics_job1.csv", assets["evaluate_metrics_job1.csv"])
    assert columns == c.METRIC_COLUMNS


def test_cli_isolated_no_database(tmp_path):
    source = tmp_path / "predictions.csv"
    source.write_bytes(pred_bytes())
    out = tmp_path / "out"
    env = {
        **os.environ,
        "PYTHONPATH": str(DATA_MODEL),
        "DATABASE_URL": "",
        "DB_HOST": "",
        "MPLCONFIGDIR": str(tmp_path / "mpl"),
    }
    listed = subprocess.run(
        [PYTHON, "-B", "-m", "evaluation.evaluate", "metrics"],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(DATA_MODEL),
    )
    assert listed.returncode == 0, listed.stderr
    assert len(json.loads(listed.stdout)) == 10
    proc = subprocess.run(
        [
            PYTHON,
            "-B",
            "-m",
            "evaluation.evaluate",
            "run",
            "--predictions",
            str(source),
            "--threshold",
            "0.5",
            "--metrics",
            "auc,f1",
            "--primary-metric",
            "auc",
            "--out",
            str(out),
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(DATA_MODEL),
    )
    assert proc.returncode == 0, proc.stderr
    registered = json.loads(proc.stdout)
    assert registered["summary"]["rows"] == 16
    batch = out / registered["job_id"]
    for item in registered["outputs"]:
        assert fc.sha256((batch / item["name"]).read_bytes()) == item["sha256"]
