"""Regression: expert / semantic / fused must register the SAME classifier set.

The three lines exist so that the only variable is the input feature space
(14-dim Kamei / 768-dim CodeBERT / 782-dim concatenation). If one line loses
or renames a classifier, the cross-line comparison silently stops being about
the feature modality. During the four-package split, expert kept the legacy
8-model list while docs/model/model-line-plan.md declared lgbm/et/svm/tabnet
shipped -- and build_model raised "未知模型" for all four.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_model.pipelines.expert import model as expert_m  # noqa: E402
from data_model.pipelines.expert.config import DEFAULT_MODELS as EXPERT_DEFAULT  # noqa: E402
from data_model.pipelines.fused import model as fused_m      # noqa: E402
from data_model.pipelines.fused.config import DEFAULT_MODELS as FUSED_DEFAULT  # noqa: E402
from data_model.pipelines.semantic import model as semantic_m  # noqa: E402
from data_model.pipelines.semantic.config import DEFAULT_MODELS as SEMANTIC_DEFAULT  # noqa: E402

EXPECTED = {
    "lr", "rf", "xgb", "lgbm", "et", "svm",
    "nb", "dt", "knn", "mlp", "mlp_deep", "tabnet",
}


def test_expert_registry_declares_expected_models():
    assert set(expert_m.MODEL_NAMES) == EXPECTED


def test_semantic_and_fused_match_expert_registry():
    assert set(semantic_m.MODEL_NAMES) == set(expert_m.MODEL_NAMES)
    assert set(fused_m.MODEL_NAMES) == set(expert_m.MODEL_NAMES)


def test_all_three_lines_share_the_same_default_model_set():
    """train.py reads each line's own config; if the defaults drift, a plain
    `python -m pipelines.<line>.train` silently compares different model sets
    and the cross-line comparison is no longer about the feature modality."""
    assert list(EXPERT_DEFAULT) == list(SEMANTIC_DEFAULT) == list(FUSED_DEFAULT)
    assert set(EXPERT_DEFAULT) == EXPECTED


def test_every_registered_model_builds():
    """build_model must accept every name the registry advertises."""
    for name in sorted(EXPECTED):
        for pkg, mod in (("expert", expert_m), ("semantic", semantic_m),
                         ("fused", fused_m)):
            m = mod.build_model(name, seed=0)
            assert m is not None, "%s.%s returned None" % (pkg, name)


@pytest.mark.parametrize("mod", [expert_m, semantic_m, fused_m],
                         ids=["expert", "semantic", "fused"])
def test_unknown_model_is_rejected_with_clear_error(mod):
    with pytest.raises(ValueError, match="未知模型"):
        mod.build_model("not-a-model", seed=0)


def _tiny(n=40, d=14):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, d)).astype(np.float32)
    y = (X[:, 0] > 0).astype(int)
    return X, y


@pytest.mark.parametrize("name", ["lgbm", "et", "svm"])
def test_new_classical_models_fit_and_predict(name):
    """Small-sample fit proves the migrated models are wired, not just declared."""
    pytest.importorskip("lightgbm")
    X, y = _tiny()
    m = expert_m.build_model(name, seed=0)
    m.fit(X, y)
    proba = m.predict_proba(X)
    assert proba.shape == (X.shape[0], 2)
    assert np.isfinite(proba).all()
