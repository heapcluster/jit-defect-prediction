"""Regression: the official entry point must import without path injection.

The official way to run a model line is documented as::

    cd data_model
    python -m pipelines.<line>.train

Under that cwd the package namespace is ``pipelines.*`` -- NOT
``data_model.pipelines.*``. A TabNet branch that hard-coded
``from data_model.pipelines.expert.model import ...`` therefore raised
``ModuleNotFoundError: No module named 'data_model'`` on the documented
command, while the unit tests (which inject the repo root into sys.path)
passed and hid the breakage.

These tests spawn a clean interpreter with cwd=data_model and NO sys.path
manipulation, exactly reproducing the reviewer's repro.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_MODEL = REPO_ROOT / "data_model"

PROBE = (
    "from pipelines.{line}.model import build_model;"
    "m = build_model('tabnet', 42);"
    "print(type(m.steps[-1][1]).__name__)"
)


def _run_probe(code: str, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run a probe with cwd=data_model and an untouched sys.path."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", code],
                          cwd=str(DATA_MODEL), capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          env=env, timeout=timeout)


@pytest.mark.parametrize("line", ["semantic", "fused"])
def test_tabnet_imports_under_official_namespace(line):
    r = _run_probe(PROBE.format(line=line))
    assert r.returncode == 0, (
        "official entry broken for %s:\nstdout: %s\nstderr: %s"
        % (line, r.stdout, r.stderr[-1200:]))
    assert "TabNet" in r.stdout, r.stdout


@pytest.mark.parametrize("line", ["semantic", "fused"])
def test_all_registered_names_build_under_official_namespace(line):
    """Every advertised name must build via the documented entry, not just tabnet."""
    probe = (
        "from pipelines.{line}.model import build_model;"
        "from pipelines.{line}.config import DEFAULT_MODELS;"
        "expected = 'lr,rf,xgb,lgbm,et,svm,nb,dt,knn,mlp,mlp_deep,tabnet'.split(',');"
        "assert set(DEFAULT_MODELS) == set(expected), DEFAULT_MODELS;"
        "[build_model(n, 42) for n in DEFAULT_MODELS];"
        "print('OK', len(DEFAULT_MODELS))"
    ).format(line=line)
    r = _run_probe(probe)
    assert r.returncode == 0, (
        "%s: %s\nstderr: %s" % (line, r.stdout, r.stderr[-1200:]))
    assert "OK 12" in r.stdout
