"""模型加载格式与特征数自检（Issue #46）：joblib 格式可加载、特征宽度不符拒收。"""

from __future__ import annotations

import joblib
import numpy as np
import pytest
from sklearn.tree import DecisionTreeClassifier

from app import config, model_registry


def _fit(n_features: int = 14) -> DecisionTreeClassifier:
    rng = np.random.RandomState(7)
    X = rng.rand(40, n_features)
    y = (X[:, 3] > 0.5).astype(int)
    return DecisionTreeClassifier(max_depth=3, random_state=7).fit(X, y)


@pytest.fixture()
def restore_registry():
    yield
    model_registry.load_models()


def test_joblib_format_model_loads(tmp_path, monkeypatch, restore_registry):
    joblib.dump(_fit(), tmp_path / "joblib_v1.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert model_registry.has("joblib_v1")


def test_wrong_feature_count_skipped(tmp_path, monkeypatch, restore_registry):
    joblib.dump(_fit(n_features=7), tmp_path / "bad_v1.pkl")
    joblib.dump(_fit(), tmp_path / "good_v1.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert not model_registry.has("bad_v1")
    assert model_registry.has("good_v1")
