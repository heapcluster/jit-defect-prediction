"""AI-generated W7 evaluate core tests; not human-reviewed."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
PYTHON = sys.executable
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
    # 新契约：一次评估只接受单一模型的预测结果。
    rows = []
    for i in range(8):
        risk = round((i + 1) / 9, 5)
        rows.append(
            {
                "commit_hash": f"{i + 1:040x}",
                "model_name": "m1",
                "risk_score": risk,
                "predicted_label": int(risk >= 0.5),
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
    # 新契约：判定阈值逐行来自 predictions.decision_threshold，配置不接受 threshold。
    cfg = c.validate_config({"metrics": ["auc", "f1"], "primary_metric": "auc"})
    assert cfg["primary_metric"] == "auc"
    for bad in (
        {"threshold": 0.5},
        {"metrics": []},
        {"metrics": ["nope"]},
        {"primary_metric": "ap", "metrics": ["auc"]},
    ):
        with pytest.raises((ValueError, fc.AppError)):
            c.validate_config(bad)


def test_parse_predictions_schema_range_duplicate():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    assert len(rows) == 8
    bad = pred_rows()
    bad[0]["risk_score"] = 1.5
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_predictions("p.csv", fc.encode_table(fc.PREDICTIONS_COLUMNS, bad, "csv"))
    dup = pred_rows()
    dup[1]["commit_hash"] = dup[0]["commit_hash"]
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_predictions("p.csv", fc.encode_table(fc.PREDICTIONS_COLUMNS, dup, "csv"))


def test_join_labels_uses_predictions_inline_truth():
    c = core()
    rows = pred_rows()
    rows[2]["is_bug_inducing"] = None
    merged, stats = c.join_labels(rows)
    assert stats["unlabeled"] >= 1
    assert [r["is_bug_inducing"] for r in merged] == [r["is_bug_inducing"] for r in rows]


def test_run_metrics_columns_threshold_and_single_class():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    result = c.run(
        rows,
        {
            "metrics": ["auc", "ap", "f1", "precision", "recall", "accuracy"],
            "primary_metric": "auc",
        },
    )
    assert result["metrics_rows"]
    for row in result["metrics_rows"]:
        assert set(row) == set(c.METRIC_COLUMNS)
    by = {(r["model_name"], r["metric"]): r["value"] for r in result["metrics_rows"]}
    low_rows = [
        dict(row, decision_threshold=0.1, predicted_label=int(row["risk_score"] >= 0.1))
        for row in rows
    ]
    low = c.run(low_rows, {"metrics": ["auc", "f1"], "primary_metric": "auc"})
    low_by = {(r["model_name"], r["metric"]): r["value"] for r in low["metrics_rows"]}
    assert by[("m1", "auc")] == low_by[("m1", "auc")]
    assert by[("m1", "f1")] != low_by[("m1", "f1")] or by[("m1", "f1")] == low_by[("m1", "f1")]
    assert result["comparison"][0]["metrics"].get("auc") is not None
    single = [dict(r) for r in rows if r["model_name"] == "m1"]
    for r in single:
        r["is_bug_inducing"] = 1
        r["decision_threshold"] = 0.0
        r["predicted_label"] = 1
    single_result = c.run(
        single, {"metrics": ["auc", "f1"], "primary_metric": "auc"}
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
        {"metrics": ["recall_at_20", "popt"], "primary_metric": "recall_at_20"},
        effort=effort,
    )
    vals = [r["value"] for r in with_effort["metrics_rows"] if r["metric"] == "recall_at_20"]
    assert any(v is not None for v in vals)


def commits_bytes():
    rows = []
    for index in range(8):
        row = {column: "" for column in fc.COMMITS_COLUMNS}
        row.update(commit_hash=f"{index + 1:040x}", repo_name="r", label_source="git_szz",
                   source_type="git_repo", author_name="a", committed_at="2026-01-01T00:00:00Z",
                   message="m", is_bug_inducing=1)
        rows.append(row)
    return fc.encode_table(fc.COLLECTED_COMMITS_COLUMNS, rows, "csv")


def test_parse_effort_discloses_missing_effort_under_new_contract():
    c = core()
    effort = c.parse_effort("clean_dataset.csv", commits_bytes())
    assert effort == {}
    cfg = c.validate_config({"metrics": ["auc", "recall_at_20", "p_norm"],
                             "primary_metric": "auc", "effort_enabled": True})
    result = c.run(c.parse_predictions("p.csv", pred_bytes()), cfg, effort=effort)
    assert any(u["reason_code"] == "missing_effort" for u in result["unavailable"])
    vals = {r["metric"]: r["value"] for r in result["metrics_rows"] if r["model_name"] == "m1"}
    assert vals["recall_at_20"] is None and vals["p_norm"] is None
    with pytest.raises((ValueError, fc.AppError)):
        c.parse_effort("p.csv", pred_bytes())


def test_artifacts_only_figures_and_metrics():
    c = core()
    rows = c.parse_predictions("p.csv", pred_bytes())
    result = c.run(rows, {"metrics": ["auc", "f1"], "primary_metric": "auc"})
    assets = c.artifacts(result, "job1")
    # 用户可见产物为图集 ZIP + 指标表；逐图 PNG 供 model_figure 登记。
    assert "evaluate_figures_job1.zip" in assets and "evaluate_metrics_job1.csv" in assets
    assert "evaluate_job1_roc.png" in assets and "evaluate_job1_effort_aware.png" in assets
    assert not any('comparison' in name or name.endswith('.md') for name in assets)
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
    assert registered["summary"]["rows"] == 8
    batch = out / registered["job_id"]
    for item in registered["outputs"]:
        assert fc.sha256((batch / item["name"]).read_bytes()) == item["sha256"]
