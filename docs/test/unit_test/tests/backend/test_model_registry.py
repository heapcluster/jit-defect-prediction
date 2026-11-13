"""模型加载格式与特征数自检（Issue #46）：joblib 格式可加载、特征宽度不符拒收。"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from app import config, model_registry
from sklearn.tree import DecisionTreeClassifier


def _fit(n_features: int = 14) -> DecisionTreeClassifier:
    rng = np.random.RandomState(7)
    X = rng.rand(40, n_features)
    y = (X[:, 3] > 0.5).astype(int)
    return DecisionTreeClassifier(max_depth=3, random_state=7).fit(X, y)


def _manifest(directory, *names):
    (directory / "feature_order.txt").write_text(
        "[models]\n"
        + "\n".join(f"{name}.pkl" for name in names)
        + "\n[feature_order]\n"
        + "\n".join(f"{i}. {name}" for i, name in enumerate(config.FEATURE_COLUMNS, 1))
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture()
def restore_registry():
    yield
    model_registry.load_models()


def test_joblib_format_model_loads(tmp_path, monkeypatch, restore_registry):
    joblib.dump(_fit(), tmp_path / "joblib_v1.pkl")
    _manifest(tmp_path, "joblib_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert model_registry.has("joblib_v1")


def test_wrong_feature_count_skipped(tmp_path, monkeypatch, restore_registry):
    joblib.dump(_fit(n_features=7), tmp_path / "bad_v1.pkl")
    joblib.dump(_fit(), tmp_path / "good_v1.pkl")
    _manifest(tmp_path, "bad_v1", "good_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert not model_registry.has("bad_v1")
    assert model_registry.has("good_v1")


def _explain_of(tmp_path, monkeypatch, model, name):
    joblib.dump(model, tmp_path / f"{name}.pkl")
    _manifest(tmp_path, name)
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
    forest = RandomForestClassifier(n_estimators=10, min_samples_leaf=2, random_state=5).fit(X, y)
    _explain_of(tmp_path, monkeypatch, forest, "forest_v1")


def test_explain_linear_pipeline_shap_additivity(tmp_path, monkeypatch, restore_registry):
    """SHAP 可加性：线性 Pipeline 的贡献和 == margin(x)−margin(background)，禁止再折算（#52 复审 10-06）。"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.RandomState(3)
    X = rng.rand(200, 14)
    y = (X[:, 3] + 0.5 * X[:, 0] > 0.7).astype(int)
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(max_iter=500, random_state=3)),
        ]
    ).fit(X, y)
    joblib.dump(pipe, tmp_path / "pipe_v1.pkl")
    _manifest(tmp_path, "pipe_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    rows = model_registry.explain(model_registry.get_model("pipe_v1"), [0.5] * 14)
    signed = sum(r["contribution"] * (1 if r["direction"] == "increase" else -1) for r in rows)
    sc = pipe.named_steps["scaler"]
    lr = pipe.named_steps["lr"]
    expected = float(
        lr.decision_function(sc.transform([[0.5] * 14]))[0]
        - lr.decision_function(sc.transform(np.zeros((1, 14))))[0]
    )
    # explain() 对贡献 round 到 6 位并丢弃 0 项，容差 1e-4 仍远小于 /scale_ 级错误（O(1)）
    assert abs(signed - expected) < 1e-4


def test_only_declared_delivery_models_load(tmp_path, monkeypatch, restore_registry):
    for name in ("lr_v1", "rf_v1", "xgb_v1", "tabnet_v1"):
        joblib.dump(_fit(), tmp_path / f"{name}.pkl")
    _manifest(tmp_path, "lr_v1", "rf_v1", "xgb_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert sorted(model_registry._REGISTRY) == ["lr_v1", "rf_v1", "xgb_v1"]


def test_manifest_missing_or_wrong_feature_order_loads_nothing(
    tmp_path, monkeypatch, restore_registry
):
    joblib.dump(_fit(), tmp_path / "lr_v1.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert not model_registry._REGISTRY
    _manifest(tmp_path, "lr_v1")
    manifest = tmp_path / "feature_order.txt"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("1. ns", "1. wrong"), encoding="utf-8"
    )
    model_registry.load_models()
    assert not model_registry._REGISTRY


def test_manifest_rejects_invalid_or_duplicate_model_entry(tmp_path, monkeypatch, restore_registry):
    """[models] 段：带路径分隔符的文件名、以及重复条目，都必须让整份清单失效。

    覆盖 `model_registry._read_manifest` 的两个拒收分支（此前只有「列序不符」被覆盖）。
    """
    joblib.dump(_fit(), tmp_path / "lr_v1.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    _manifest(tmp_path, "lr_v1")
    manifest = tmp_path / "feature_order.txt"
    good = manifest.read_text(encoding="utf-8")

    # 1) 非法文件名：带 ../ 的路径穿越写法
    manifest.write_text(good.replace("lr_v1.pkl", "../lr_v1.pkl", 1), encoding="utf-8")
    model_registry.load_models()
    assert not model_registry._REGISTRY

    # 2) 重复条目：同一文件名出现两次
    manifest.write_text(good.replace("lr_v1.pkl", "lr_v1.pkl\nlr_v1.pkl", 1), encoding="utf-8")
    model_registry.load_models()
    assert not model_registry._REGISTRY


def test_manifest_rejects_feature_order_without_index(tmp_path, monkeypatch, restore_registry):
    """[feature_order] 段：`1. ns` 少了序号前缀 → 整份清单失效（走 invalid feature order 分支）。"""
    joblib.dump(_fit(), tmp_path / "lr_v1.pkl")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    _manifest(tmp_path, "lr_v1")
    manifest = tmp_path / "feature_order.txt"
    good = manifest.read_text(encoding="utf-8")
    manifest.write_text(good.replace("1. ns", "ns", 1), encoding="utf-8")
    model_registry.load_models()
    assert not model_registry._REGISTRY


def test_repository_model_module_loads_in_clean_process(tmp_path):
    code_dir = tmp_path / "data_model"
    package = code_dir / "pipelines"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "delivery_fixture.py").write_text(
        "class DeliveryModel:\n    n_features_in_ = 14\n", encoding="utf-8"
    )
    weights = tmp_path / "weights"
    weights.mkdir()
    _manifest(weights, "custom_v1")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    producer = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys, joblib; sys.path.insert(0, sys.argv[1]); "
                "import pipelines.delivery_fixture as delivery; "
                "joblib.dump(delivery.DeliveryModel(), sys.argv[2])"
            ),
            str(code_dir),
            str(weights / "custom_v1.pkl"),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert producer.returncode == 0, producer.stderr
    consumer = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys, importlib.util; from pathlib import Path; "
                "from app import config, model_registry; "
                "assert importlib.util.find_spec('pipelines') is None; "
                "config.REPO_ROOT = Path(sys.argv[1]); "
                "config.MODEL_DIR = Path(sys.argv[2]); "
                "model_registry.load_models(); "
                "assert model_registry.has('custom_v1'); "
                "assert model_registry.get_model('custom_v1').model.n_features_in_ == 14; "
                "model_registry.load_models(); "
                "assert sys.path.count(str((config.REPO_ROOT / 'data_model').resolve())) == 1"
            ),
            str(tmp_path),
            str(weights),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert consumer.returncode == 0, consumer.stderr


def test_import_path_comes_from_repo_not_weights(tmp_path, monkeypatch, restore_registry):
    repo = tmp_path / "repo"
    weights = tmp_path / "external-weights"
    weights.mkdir()
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(config, "REPO_ROOT", repo)
    monkeypatch.setattr(config, "MODEL_DIR", weights)
    model_registry.load_models()
    model_registry.load_models()
    assert sys.path.count(str((repo / "data_model").resolve())) == 1
    assert str(weights) not in sys.path


def test_failed_models_summary_includes_corrupt_and_wrong_width(
    tmp_path, monkeypatch, caplog, restore_registry
):
    (tmp_path / "broken_v1.pkl").write_bytes(b"not a pickle")
    joblib.dump(_fit(), tmp_path / "good_v1.pkl")
    joblib.dump(_fit(7), tmp_path / "wide_v1.pkl")
    _manifest(tmp_path, "broken_v1", "good_v1", "wide_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    with caplog.at_level(logging.INFO, logger="backend.model_registry"):
        model_registry.load_models()
    assert sorted(model_registry._REGISTRY) == ["good_v1"]
    summaries = [r for r in caplog.records if r.message.startswith("failed models:")]
    assert len(summaries) == 1
    assert summaries[0].levelno == logging.ERROR
    assert summaries[0].message == "failed models: ['broken_v1', 'wide_v1']"
    assert "loaded models: ['good_v1']" in caplog.text
    assert any(r.exc_info for r in caplog.records)


def test_declared_but_missing_weight_enters_failed_summary(
    tmp_path, monkeypatch, caplog, restore_registry
):
    joblib.dump(_fit(), tmp_path / "good_v1.pkl")
    _manifest(tmp_path, "absent_v1", "good_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    with caplog.at_level(logging.INFO, logger="backend.model_registry"):
        model_registry.load_models()
    assert sorted(model_registry._REGISTRY) == ["good_v1"]
    assert "declared delivery model missing: absent_v1" in caplog.text
    assert "failed models: ['absent_v1']" in caplog.text


def test_failed_summary_does_not_persist_after_success(
    tmp_path, monkeypatch, caplog, restore_registry
):
    path = tmp_path / "recover_v1.pkl"
    path.write_bytes(b"not a pickle")
    _manifest(tmp_path, "recover_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert not model_registry.has("recover_v1")
    caplog.clear()
    joblib.dump(_fit(), path)
    with caplog.at_level(logging.INFO, logger="backend.model_registry"):
        model_registry.load_models()
    assert model_registry.has("recover_v1")
    assert not any(r.levelno >= logging.ERROR for r in caplog.records)


def test_main_module_model_is_reported_without_alias(
    tmp_path, monkeypatch, caplog, restore_registry
):
    producer = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys, joblib\n"
                "class TabNetWithEarlyStop:\n    n_features_in_ = 14\n"
                "joblib.dump(TabNetWithEarlyStop(), sys.argv[1])\n"
            ),
            str(tmp_path / "tabnet_v1.pkl"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert producer.returncode == 0, producer.stderr
    _manifest(tmp_path, "tabnet_v1")
    monkeypatch.delattr(sys.modules["__main__"], "TabNetWithEarlyStop", raising=False)
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    with caplog.at_level(logging.ERROR, logger="backend.model_registry"):
        model_registry.load_models()
    assert not model_registry.has("tabnet_v1")
    assert "failed models: ['tabnet_v1']" in caplog.text
    assert not hasattr(sys.modules["__main__"], "TabNetWithEarlyStop")


def test_missing_model_directory_clears_registry(tmp_path, monkeypatch, restore_registry):
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    joblib.dump(_fit(), tmp_path / "valid_v1.pkl")
    _manifest(tmp_path, "valid_v1")
    model_registry.load_models()
    assert model_registry.has("valid_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path / "missing")
    model_registry.load_models()
    assert not model_registry._REGISTRY


def test_is_tree_family_covers_lightgbm():
    """#139 实测：LGBMClassifier 模块是 lightgbm.sklearn、类名无 Tree/Forest/Boost，
    不显式识别会掉进 LinearExplainer 报 InvalidModelError 把归因降级为空。"""
    lgbm = type("LGBMClassifier", (), {"__module__": "lightgbm.sklearn"})()
    assert model_registry._is_tree_family(lgbm)
    xgb = type("XGBClassifier", (), {"__module__": "xgboost.sklearn"})()
    assert model_registry._is_tree_family(xgb)
    svc = type("SVC", (), {"__module__": "sklearn.svm._classes"})()
    assert not model_registry._is_tree_family(svc)


def test_explain_lightgbm_uses_tree_explainer(tmp_path, monkeypatch, restore_registry):
    """lgbm_v1 真形态：LGBMClassifier 走 TreeExplainer，归因非空（#139 上线前为降级空）。"""
    lightgbm = pytest.importorskip("lightgbm")
    rng = np.random.RandomState(11)
    X = rng.rand(80, 14)
    y = (X[:, 3] > 0.5).astype(int)
    model = lightgbm.LGBMClassifier(
        n_estimators=20, min_child_samples=2, random_state=11, verbose=-1
    ).fit(X, y)
    _explain_of(tmp_path, monkeypatch, model, "lgbm_v1")


def test_explain_kernel_model_degrades_to_empty_without_raising(
    tmp_path, monkeypatch, restore_registry
):
    """svm/mlp_deep/tabnet 的设计内降级：核/深度模型无高效精确 SHAP 解释器，
    explain() 返回空数组且不抛异常（契约三 §4 允许这三个模型归因为空，见 #139 裁定）。"""
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC

    rng = np.random.RandomState(13)
    X = rng.rand(60, 14)
    y = (X[:, 3] > 0.5).astype(int)
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("svc", SVC(kernel="rbf", probability=True, random_state=13)),
        ]
    ).fit(X, y)
    joblib.dump(pipe, tmp_path / "svm_v1.pkl")
    _manifest(tmp_path, "svm_v1")
    monkeypatch.setattr(config, "MODEL_DIR", tmp_path)
    model_registry.load_models()
    assert model_registry.has("svm_v1")
    # 预测照常工作（500ms 靶子内的推理路径不受解释器影响）
    risk = model_registry.predict_proba(pipe, [0.5] * 14)
    assert 0.0 <= risk <= 1.0
    # 归因降级：空数组、不抛异常
    assert model_registry.explain(model_registry.get_model("svm_v1"), [0.5] * 14) == []
