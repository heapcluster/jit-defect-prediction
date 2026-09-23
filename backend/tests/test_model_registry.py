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


def _explain_of(tmp_path, monkeypatch, model, name):
    joblib.dump(model, tmp_path / f"{name}.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert model_registry.has(name)
    rows = model_registry.explain(model_registry.get_model(name), [0.5] * 14)
    assert rows, "explanation must not degrade to empty for delivered-model shapes"
    assert all(set(r) == {"feature", "contribution", "direction"} for r in rows)
    assert all(r["feature"] in config.FEATURE_COLUMNS for r in rows)


def test_explain_linear_pipeline(tmp_path, monkeypatch, restore_registry):
    """lr_v1 真形态：Pipeline(StandardScaler → LogisticRegression)（Issue #50）。"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.RandomState(3)
    X = rng.rand(60, 14)
    y = (X[:, 3] + 0.5 * X[:, 0] > 0.7).astype(int)
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=500, random_state=3)),
        ]
    ).fit(X, y)
    _explain_of(tmp_path, monkeypatch, pipe, "pipe_v1")


def test_explain_random_forest(tmp_path, monkeypatch, restore_registry):
    """rf_v1 真形态：多树森林，shap 0.52 返回 (n, 14, 2) 三维数组（Issue #50）。"""
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.RandomState(5)
    X = rng.rand(60, 14)
    y = (X[:, 3] > 0.5).astype(int)
    forest = RandomForestClassifier(
        n_estimators=10, min_samples_leaf=2, random_state=5
    ).fit(X, y)
    _explain_of(tmp_path, monkeypatch, forest, "forest_v1")
