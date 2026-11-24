import base64
import importlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

# LIME 是可选重依赖：环境未安装时整个 LIME 组跳过，不伪装通过。
pytest.importorskip("lime")

CORE_PATH = Path(__file__).resolve().parents[1] / "app" / "explain_core.py"
NAMES = [f"feature_{index}" for index in range(14)]


def test_core_module_exists():
    assert importlib.util.find_spec("app.explain_core") is not None, (
        "missing module: app.explain_core"
    )


@pytest.fixture(scope="module")
def core():
    return importlib.import_module("app.explain_core")


@pytest.fixture(scope="module")
def trained():
    rng = np.random.RandomState(19)
    data = rng.normal(size=(180, 14)) * np.arange(1, 15) + np.arange(14)
    data[:, -1] = 7.0
    labels = (data[:, 0] - data[:, 1] / 2 + data[:, 2] / 3 > 0).astype(int)
    linear = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=500, random_state=9)),
        ]
    ).fit(data, labels)
    forest = RandomForestClassifier(n_estimators=12, max_depth=4, random_state=9).fit(data, labels)
    tabular = SVC(probability=True, random_state=9).fit(data, labels)
    vector = np.array([2.0, 5.0, -4.0, *range(3, 14)], dtype=float)
    return SimpleNamespace(
        data=data, labels=labels, linear=linear, forest=forest, tabular=tabular, vector=vector
    )


def assert_items(result, vector, names=NAMES):
    assert result["reason_code"] is None, result
    assert len(result["items"]) == len(names)
    assert np.isfinite(result["base_value"])
    positions = {name: index for index, name in enumerate(names)}
    magnitudes = [abs(item["contribution"]) for item in result["items"]]
    assert magnitudes == sorted(magnitudes, reverse=True)
    for rank, item in enumerate(result["items"], 1):
        assert item["rank"] == rank
        assert item["raw_value"] == vector[positions[item["feature"]]]
        value = item["contribution"]
        assert np.isfinite(value)
        assert item["direction"] == (
            "increase" if value > 0 else "decrease" if value < 0 else "neutral"
        )
        assert item["output_space"] == result["output_space"]


def test_techniques_and_compatibility(core, trained):
    catalog = core.techniques()
    assert [entry["key"] for entry in catalog] == ["shap", "lime"]
    expected = {
        "shap": {"background_size": ("int", 32, 1, 128)},
        "lime": {
            "num_samples": ("int", 512, 128, 5000),
            "kernel_width": ("float", 3.0, 0.1, 10.0),
            "seed": ("int", 42, 0, 2147483647),
        },
    }
    for technique in catalog:
        assert technique["name"] and technique["description"]
        for parameter in technique["params_schema"]:
            assert set(parameter) == {
                "name",
                "type",
                "default",
                "min",
                "max",
                "choices",
                "description",
            }
            assert (
                tuple(parameter[key] for key in ("type", "default", "min", "max"))
                == (expected[technique["key"]][parameter["name"]])
            )
            assert parameter["description"]
    catalog[0]["params_schema"][0]["default"] = 0
    assert core.validate_params("shap") == {"background_size": 32}
    assert core.validate_params("lime") == {"num_samples": 512, "kernel_width": 3.0, "seed": 42}
    assert core.family(trained.linear) == "linear"
    assert core.family(trained.forest) == "tree"
    assert core.family(trained.tabular) == "tabular"
    assert core.family(SimpleNamespace(coef_=np.zeros((1, 14)))) == "linear"
    assert core.family(type("TreePretender", (), {})()) == "text"
    entries = core.compatibility()
    assert len(entries) == 8
    for entry in entries:
        supported = entry["family"] in {"tree", "linear"} or (
            entry["family"] == "tabular" and entry["technique"] == "lime"
        )
        assert entry["supported"] is supported
        assert entry["reason_code"] == (None if supported else "unsupported_model_family")


@pytest.mark.parametrize(
    "technique,params",
    [
        ("other", None),
        (True, None),
        ("shap", []),
        ("lime", "bad"),
        ("shap", {"secret/path": 1}),
        ("shap", {"background_size": True}),
        ("shap", {"background_size": "32"}),
        ("shap", {"background_size": 32.0}),
        ("shap", {"background_size": 0}),
        ("shap", {"background_size": 129}),
        ("shap", {"background_size": np.int64(32)}),
        ("lime", {"num_samples": 127}),
        ("lime", {"num_samples": 5001}),
        ("lime", {"seed": -1}),
        ("lime", {"seed": 2147483648}),
        ("lime", {"seed": False}),
        ("lime", {"kernel_width": "3.0"}),
        ("lime", {"kernel_width": True}),
        ("lime", {"kernel_width": float("nan")}),
        ("lime", {"kernel_width": float("inf")}),
        ("lime", {"kernel_width": 0.0}),
        ("lime", {"kernel_width": 11.0}),
    ],
)
def test_strict_safe_parameter_validation(core, technique, params):
    with pytest.raises(ValueError) as error:
        core.validate_params(technique, params)
    assert any("\u4e00" <= character <= "\u9fff" for character in str(error.value))
    assert "secret/path" not in str(error.value)


def test_parameter_boundaries_and_no_mutation(core):
    params = {"num_samples": 128, "kernel_width": 0.1, "seed": 0}
    assert core.validate_params("lime", params) == params
    assert core.validate_params("lime", params) is not params
    assert core.validate_params("shap", {"background_size": 128}) == {"background_size": 128}
    assert (
        core.validate_params(
            "lime", {"num_samples": 5000, "kernel_width": 10.0, "seed": 2147483647}
        )["seed"]
        == 2147483647
    )


def test_linear_signed_shap_additivity_and_zero_items(core, trained):
    result = core.explain(trained.linear, trained.vector, feature_names=NAMES, top_n=14)
    assert_items(result, trained.vector)
    assert result["output_space"] == "log_odds"
    expected_base = trained.linear.decision_function(np.zeros((1, 14)))[0]
    expected_score = trained.linear.decision_function(trained.vector.reshape(1, -1))[0]
    assert result["base_value"] == pytest.approx(expected_base, abs=1e-6)
    assert result["base_value"] + sum(item["contribution"] for item in result["items"]) == (
        pytest.approx(expected_score, abs=1e-6)
    )
    assert {item["direction"] for item in result["items"]} == {"increase", "decrease", "neutral"}
    top = core.explain(trained.linear, trained.vector, feature_names=NAMES)
    assert top["items"] == result["items"][:8]


def test_background_scaler_parity_precedence_and_limit(core, trained):
    model = trained.linear
    scaler, inner = (step for _, step in model.steps)
    provided = trained.data[:7].copy()
    attached = trained.data[20:25].copy()
    model._jit_background = attached
    try:
        result = core.explain(
            model,
            trained.vector,
            feature_names=NAMES,
            background=provided,
            params={"background_size": 3},
            top_n=14,
        )
        assert_items(result, trained.vector)
        transformed = scaler.transform(provided[:3])
        expected = inner.coef_[0] * (
            scaler.transform([trained.vector])[0] - transformed.mean(axis=0)
        )
        contributions = {item["feature"]: item["contribution"] for item in result["items"]}
        np.testing.assert_allclose([contributions[name] for name in NAMES], expected, atol=1e-6)
        assert result["base_value"] == pytest.approx(
            model.decision_function(provided[:3]).mean(), abs=1e-6
        )
        fallback = core.explain(model, trained.vector, feature_names=NAMES, top_n=14)
        assert fallback["base_value"] == pytest.approx(
            model.decision_function(attached).mean(), abs=1e-6
        )
        np.testing.assert_array_equal(provided, trained.data[:7])
        np.testing.assert_array_equal(attached, trained.data[20:25])
    finally:
        del model._jit_background


def test_real_forest_shap_positive_class(core, trained):
    result = core.explain(trained.forest, trained.vector, feature_names=NAMES, top_n=14)
    assert_items(result, trained.vector)
    assert result["output_space"] == "tree_raw"
    assert result["base_value"] + sum(item["contribution"] for item in result["items"]) == (
        pytest.approx(trained.forest.predict_proba([trained.vector])[0, 1], abs=1e-6)
    )


@pytest.mark.parametrize("model_name", ["linear", "forest"])
def test_shap_readonly_training_objects(core, trained, model_name):
    model = getattr(trained, model_name)
    before = io.BytesIO()
    joblib.dump(model, before)
    data = trained.data.copy()
    vector = trained.vector.copy()
    data.setflags(write=False)
    vector.setflags(write=False)
    probabilities = model.predict_proba([vector]).copy()
    result = core.explain(model, vector, feature_names=NAMES, background=data, top_n=14)
    assert_items(result, vector)
    np.testing.assert_array_equal(model.predict_proba([vector]), probabilities)
    np.testing.assert_array_equal(data, trained.data)
    np.testing.assert_array_equal(vector, trained.vector)
    after = io.BytesIO()
    joblib.dump(model, after)
    assert before.getvalue() == after.getvalue()


@pytest.mark.parametrize("model_name", ["linear", "forest", "tabular"])
def test_real_lime_repeatability_and_readonly(core, trained, model_name):
    model = getattr(trained, model_name)
    before = io.BytesIO()
    joblib.dump(model, before)
    data = trained.data.copy()
    vector = trained.vector.copy()
    data.setflags(write=False)
    vector.setflags(write=False)
    probabilities = model.predict_proba([vector]).copy()
    kwargs = dict(feature_names=NAMES, technique="lime", background=data, top_n=14)
    first = core.explain(model, vector, **kwargs)
    second = core.explain(model, vector, **kwargs)
    assert_items(first, vector)
    assert first == second
    assert first["output_space"] == "local_probability_coefficient"
    assert first["message"] is None
    np.testing.assert_array_equal(model.predict_proba([vector]), probabilities)
    np.testing.assert_array_equal(data, trained.data)
    np.testing.assert_array_equal(vector, trained.vector)
    after = io.BytesIO()
    joblib.dump(model, after)
    assert before.getvalue() == after.getvalue()


def test_synthetic_lime_warning_and_unsupported(core, trained):
    result = core.explain(
        trained.linear, trained.vector, feature_names=NAMES, technique="lime", top_n=14
    )
    assert_items(result, trained.vector)
    assert "合成" in result["message"]
    assert "训练数据" in result["message"]
    for model, technique in [(object(), "shap"), (object(), "lime"), (trained.tabular, "shap")]:
        result = core.explain(model, trained.vector, feature_names=NAMES, technique=technique)
        assert result["reason_code"] == "unsupported_model_family"
        assert result["items"] == [] and result["base_value"] is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"vector": [1.0]},
        {"vector": [[0.0] * 14]},
        {"vector": [float("nan")] * 14},
        {"vector": [float("inf")] * 14},
        {"vector": ["1"] * 14},
        {"vector": [True] * 14},
        {"top_n": 0},
        {"top_n": 1025},
        {"top_n": True},
        {"top_n": 2.0},
        {"feature_names": "names"},
        {"feature_names": [1] * 14},
        {"feature_names": []},
        {"background": np.zeros((2, 13))},
        {"background": np.zeros(14)},
        {"background": np.zeros((0, 14))},
        {"background": np.full((1, 14), np.nan)},
        {"background": [["0"] * 14]},
        {"params": {"background_size": False}},
    ],
)
def test_invalid_caller_boundary_raises(core, trained, kwargs):
    arguments = dict(vector=trained.vector, feature_names=NAMES)
    arguments.update(kwargs)
    with pytest.raises(ValueError):
        core.explain(trained.linear, **arguments)


@pytest.mark.parametrize("shape", ["list", "three_dimensional", "two_dimensional"])
def test_shap_shapes_sign_and_stable_ties(core, trained, monkeypatch, shape):
    import shap

    values = np.array([[2.0, -2.0, 0.0]])
    if shape == "list":
        values = [-values, values]
    elif shape == "three_dimensional":
        values = np.stack([-values, values], axis=-1)
    monkeypatch.setattr(
        shap,
        "TreeExplainer",
        lambda model, **kwargs: SimpleNamespace(
            shap_values=lambda vector: values, expected_value=np.array([0.8, 0.2])
        ),
    )
    result = core.explain(
        trained.forest, [9.0, 8.0, 7.0], feature_names=["z", "a", "neutral"], top_n=3
    )
    assert_items(result, [9.0, 8.0, 7.0], ["z", "a", "neutral"])
    assert [item["feature"] for item in result["items"]] == ["z", "a", "neutral"]
    assert [item["contribution"] for item in result["items"]] == [2.0, -2.0, 0.0]
    assert result["base_value"] == 0.2


@pytest.mark.parametrize("values", [np.ones((1, 13)), np.full((1, 14), np.inf)])
def test_bad_explainer_outputs_fail_safely(core, trained, monkeypatch, values):
    import shap

    monkeypatch.setattr(
        shap,
        "TreeExplainer",
        lambda model, **kwargs: SimpleNamespace(
            shap_values=lambda vector: values, expected_value=0.2
        ),
    )
    result = core.explain(trained.forest, trained.vector, feature_names=NAMES)
    assert result["reason_code"] == "explainer_failed"
    assert result["items"] == [] and result["base_value"] is None
    assert "Traceback" not in result["message"]


def test_exception_message_is_safe(core, trained, monkeypatch):
    import shap

    def fail(model, **kwargs):
        raise RuntimeError("/private/model.pkl secret traceback")

    monkeypatch.setattr(shap, "TreeExplainer", fail)
    result = core.explain(trained.forest, trained.vector, feature_names=NAMES)
    assert result["reason_code"] == "explainer_failed"
    assert "/private" not in result["message"] and "secret" not in result["message"]


@pytest.mark.parametrize(
    "classes,probabilities,expected",
    [
        ([1, 0], [0.7, 0.3], [0.3, 0.7]),
        ([0], [1.0], [1.0, 0.0]),
        ([1], [1.0], [0.0, 1.0]),
    ],
)
def test_lime_callback_class_mapping_and_arguments(
    core, monkeypatch, classes, probabilities, expected
):
    from lime import lime_tabular

    observed = {}

    class Explainer:
        def __init__(self, background, **kwargs):
            observed.update(background=background.copy(), **kwargs)

        def explain_instance(self, vector, callback, **kwargs):
            np.testing.assert_array_equal(callback(np.array([vector])), [expected])
            observed.update(kwargs)
            return SimpleNamespace(local_exp={1: [(1, -0.25), (0, 0.5)]}, intercept={1: 0.1})

    monkeypatch.setattr(lime_tabular, "LimeTabularExplainer", Explainer)
    model = SimpleNamespace(
        classes_=np.array(classes),
        predict_proba=lambda rows: np.tile(probabilities, (len(rows), 1)),
    )
    background = np.arange(400.0).reshape(200, 2)
    result = core.explain(
        model,
        [4.0, 8.0],
        feature_names=["first", "second"],
        technique="lime",
        background=background,
        top_n=2,
    )
    assert_items(result, [4.0, 8.0], ["first", "second"])
    assert observed["background"].shape == (128, 2)
    np.testing.assert_array_equal(observed["background"], background[:128])
    assert observed["class_names"] == ["no defect", "defect"]
    assert observed["mode"] == "classification"
    assert observed["discretize_continuous"] is False
    assert observed["random_state"] == 42 and observed["kernel_width"] == 3.0
    assert observed["num_features"] == 2 and observed["num_samples"] == 512
    assert result["base_value"] == 0.1
    assert [item["contribution"] for item in result["items"]] == [0.5, -0.25]


@pytest.mark.parametrize(
    "classes,probabilities",
    [
        ([2], [1.0]),
        ([0, 1], [np.nan, 0.5]),
        ([0, 1], [0.5]),
    ],
)
def test_lime_invalid_model_probabilities_fail(core, monkeypatch, classes, probabilities):
    from lime import lime_tabular

    class Explainer:
        def __init__(self, *args, **kwargs):
            pass

        def explain_instance(self, vector, callback, **kwargs):
            callback(np.array([vector]))
            return SimpleNamespace(local_exp={1: [(0, 0.1)]}, intercept={1: 0.0})

    monkeypatch.setattr(lime_tabular, "LimeTabularExplainer", Explainer)
    model = SimpleNamespace(
        classes_=np.array(classes),
        predict_proba=lambda rows: np.tile(probabilities, (len(rows), 1)),
    )
    result = core.explain(model, [1.0], feature_names=["x"], technique="lime")
    assert result["reason_code"] == "explainer_failed"


def test_import_is_pure_and_worker_json(core, trained):
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    check = (
        "import sys; "
        f"sys.path.insert(0, {str(CORE_PATH.parent)!r}); "
        "import explain_core; "
        "assert 'joblib' not in sys.modules; "
        "assert not any(name in sys.modules for name in "
        "['app.config', 'app.db', 'app.model_registry'])"
    )
    imported = subprocess.run(
        [sys.executable, "-B", "-c", check],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
    )
    assert imported.returncode == 0, imported.stderr
    buffer = io.BytesIO()
    joblib.dump(trained.linear, buffer)
    payload = {
        "weights": base64.b64encode(buffer.getvalue()).decode("ascii"),
        "rows": [{"commit_hash": "abc123", "features": trained.vector.tolist()}],
        "feature_names": NAMES,
        "techniques": ["shap", "lime"],
        "params": {"shap": {}, "lime": {}},
        "top_n": 14,
    }
    worker = subprocess.run(
        [sys.executable, "-B", str(CORE_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        timeout=90,
    )
    assert worker.returncode != 0, 'worker must reject execution without OS sandbox policy'
    from app import config
    from app.services.explain_run import isolated_results
    params = {t: core.validate_params(t, {}) for t in ('shap', 'lime')}
    results = isolated_results(buffer.getvalue(), payload['rows'], payload['techniques'], params, 14)
    for result in results:
        for item in result['items']:
            item['feature'] = NAMES[list(config.FEATURE_COLUMNS).index(item['feature'])]
    assert isinstance(results, list) and len(results) == 2
    for result, technique in zip(results, ["shap", "lime"], strict=True):
        assert result["commit_hash"] == "abc123" and result["technique"] == technique
        assert_items(result, trained.vector)
    assert (
        results[0]["items"]
        == core.explain(trained.linear, trained.vector, feature_names=NAMES, top_n=14)["items"]
    )
