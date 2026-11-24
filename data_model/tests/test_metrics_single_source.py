"""AI-generated/unreviewed W5 metrics single-source parity tests; no database.

evaluation/metrics.py must be the contract-named single source whose formulas
are EXACTLY (float-for-float) the expert line's effort_unaware / effort_aware
math, plus a degenerate-case safe_summary wrapper (not a second formula set).
"""
from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = ROOT / "data_model"
sys.path.insert(0, str(DATA_MODEL))
sys.path.insert(0, str(ROOT / "backend"))


def single():
    assert (DATA_MODEL / "evaluation/metrics.py").is_file(), "W5 metrics single source missing"
    return importlib.import_module("evaluation.metrics")


def expert():
    return importlib.import_module("pipelines.expert.metrics")


def expert_config():
    return importlib.import_module("pipelines.expert.config")


def assert_exact(a, b):
    """Recursive EXACT equality; NaN==NaN only for the documented NaN slots."""
    if isinstance(a, dict):
        assert isinstance(b, dict) and set(a) == set(b), (set(a), set(b))
        for key in a:
            assert_exact(a[key], b[key])
    elif isinstance(a, (list, tuple, np.ndarray)):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            assert_exact(x, y)
    elif isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b):
        return
    else:
        assert a == b, (a, b)


def data(n=80):
    rng = np.random.default_rng(7)
    y = rng.integers(0, 2, n)
    y[0], y[1] = 0, 1
    proba = rng.random(n)
    effort = rng.integers(1, 20, n).astype(float)  # many ties on purpose
    return y, proba, effort


def test_constants_match_expert_config():
    m, cfg = single(), expert_config()
    assert m.DECISION_THRESHOLD == cfg.DECISION_THRESHOLD == 0.5
    assert m.RANDOM_BASELINE_SEED == cfg.RANDOM_BASELINE_SEED == 0
    assert m.RANDOM_BASELINE_REPEATS == cfg.RANDOM_BASELINE_REPEATS == 200


def test_module_is_self_contained_no_expert_config_import():
    source = (DATA_MODEL / "evaluation/metrics.py").read_text(encoding="utf-8")
    assert "expert.config" not in source
    assert "from ." not in source
    assert "import config" not in source


@pytest.mark.parametrize("threshold", [None, 0.3, 0.7])
def test_effort_unaware_exact_float_parity(threshold):
    y, proba, _ = data()
    assert_exact(single().effort_unaware(y, proba, threshold),
                 expert().effort_unaware(y, proba, threshold))


@pytest.mark.parametrize("floor", [None, 10])
def test_effort_aware_exact_float_parity(floor):
    y, proba, effort = data()
    assert_exact(single().effort_aware_metrics(proba, y, effort, review_floor=floor),
                 expert().effort_aware_metrics(proba, y, effort, review_floor=floor))


def test_helpers_exact_parity():
    y, proba, effort = data()
    s, e = single(), expert()
    order = np.argsort(-proba, kind="stable")
    assert s.cumulative_area(order, effort, y) == e.cumulative_area(order, effort, y)
    xs1, ys1 = s.cumulative_curve(order, effort, y)
    xs2, ys2 = e.cumulative_curve(order, effort, y)
    assert np.array_equal(xs1, xs2) and np.array_equal(ys1, ys2)
    assert s.recall_and_count_at_effort(order, effort, y, 0.2) == e.recall_and_count_at_effort(order, effort, y, 0.2)
    assert s.recall_at_effort(order, effort, y, 0.5) == e.recall_at_effort(order, effort, y, 0.5)
    assert np.array_equal(s.budget_order(proba, effort, 10), e.budget_order(proba, effort, 10))
    assert_exact(s._spearman(proba, np.log(effort)), e._spearman(proba, np.log(effort)))


def test_safe_summary_empty_returns_none_and_warning():
    metrics, warnings = single().safe_summary(np.array([]), np.array([]))
    assert set(metrics) == {"auc", "f1", "precision", "recall", "accuracy"}
    assert all(value is None for value in metrics.values())
    assert warnings


@pytest.mark.parametrize("label", [0, 1])
@pytest.mark.parametrize("threshold", [0.5, 0.3])
def test_safe_summary_single_class_auc_none_others_sklearn(label, threshold):
    y, proba, _ = data()
    y = np.full(len(y), label)
    metrics, warnings = single().safe_summary(y, proba, threshold)
    assert metrics["auc"] is None
    assert "single_class_test_auc_undefined" in warnings
    pred = (proba >= threshold).astype(int)
    assert metrics["f1"] == float(f1_score(y, pred, zero_division=0))
    assert metrics["precision"] == float(precision_score(y, pred, zero_division=0))
    assert metrics["recall"] == float(recall_score(y, pred, zero_division=0))
    assert metrics["accuracy"] == float(accuracy_score(y, pred))


@pytest.mark.parametrize("threshold", [0.5, 0.3])
def test_safe_summary_non_degenerate_is_effort_unaware_verbatim(threshold):
    y, proba, _ = data()
    metrics, warnings = single().safe_summary(y, proba, threshold)
    assert warnings == []
    assert_exact(metrics, single().effort_unaware(y, proba, threshold))
    assert_exact(metrics, expert().effort_unaware(y, proba, threshold))