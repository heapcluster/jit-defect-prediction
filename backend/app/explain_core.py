from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

import numpy as np

_TECHNIQUES = [
    {
        "key": "shap",
        "name": "SHAP",
        "description": "有符号的逐特征可加贡献；支持树模型与线性模型。",
        "params_schema": [
            {
                "name": "background_size",
                "type": "int",
                "default": 32,
                "min": 1,
                "max": 128,
                "choices": None,
                "description": "使用背景数据的前若干行。",
            },
        ],
    },
    {
        "key": "lime",
        "name": "LIME",
        "description": "正类概率的局部代理系数，不是 SHAP 精确可加贡献。",
        "params_schema": [
            {
                "name": "num_samples",
                "type": "int",
                "default": 512,
                "min": 128,
                "max": 5000,
                "choices": None,
                "description": "局部扰动样本数量。",
            },
            {
                "name": "kernel_width",
                "type": "float",
                "default": 3.0,
                "min": 0.1,
                "max": 10.0,
                "choices": None,
                "description": "局部距离核宽度。",
            },
            {
                "name": "seed",
                "type": "int",
                "default": 42,
                "min": 0,
                "max": 2147483647,
                "choices": None,
                "description": "可重复的随机种子。",
            },
        ],
    },
]
_SYNTHETIC_WARNING = "未提供背景分布；使用零值及正负单位值合成参考，不是真实训练数据。"


def techniques() -> list[dict]:
    return deepcopy(_TECHNIQUES)


def validate_params(technique: str, params: dict | None = None) -> dict:
    if type(technique) is not str or technique not in {"shap", "lime"}:
        raise ValueError("未知的解释技术。")
    if params is None:
        params = {}
    if type(params) is not dict:
        raise ValueError("解释参数必须为参数对象。")
    schema = next(item["params_schema"] for item in _TECHNIQUES if item["key"] == technique)
    if any(key not in {item["name"] for item in schema} for key in params):
        raise ValueError("包含未知的解释参数。")
    normalized = {}
    for parameter in schema:
        value = params.get(parameter["name"], parameter["default"])
        expected_type = int if parameter["type"] == "int" else float
        if (expected_type is int and type(value) is not int) or (
            expected_type is float and type(value) not in (int, float)
        ):
            raise ValueError("解释参数类型不正确。")
        value = expected_type(value)
        if expected_type is float and not math.isfinite(value):
            raise ValueError("解释参数必须为有限数值。")
        if not parameter["min"] <= value <= parameter["max"]:
            raise ValueError("解释参数超出允许范围。")
        normalized[parameter["name"]] = value
    return normalized


def _parts(model: Any) -> tuple[Any, Any]:
    steps = getattr(model, "steps", None)
    if steps is not None and len(steps) == 2:
        transformer, inner = (step for _, step in steps)
        if callable(getattr(transformer, "transform", None)):
            return inner, transformer
    return model, None


def family(model: Any) -> str:
    inner, _ = _parts(model)
    modules = (cls.__module__ for cls in type(inner).__mro__)
    if any(
        module.startswith(("sklearn.tree", "sklearn.ensemble", "xgboost", "lightgbm"))
        for module in modules
    ):
        return "tree"
    if hasattr(inner, "coef_"):
        return "linear"
    if callable(getattr(model, "predict_proba", None)):
        return "tabular"
    return "text"


def compatibility() -> list[dict]:
    return [
        {
            "family": model_family,
            "technique": technique,
            "supported": supported,
            "reason_code": None if supported else "unsupported_model_family",
        }
        for model_family in ("tree", "linear", "tabular", "text")
        for technique in ("shap", "lime")
        for supported in [
            model_family in {"tree", "linear"}
            or (model_family == "tabular" and technique == "lime")
        ]
    ]


def _array(value: Any, dimensions: int, width: int) -> np.ndarray:
    try:
        array = np.asarray(value)
        if array.dtype.kind not in "iuf" or array.ndim != dimensions:
            raise ValueError
        if array.shape[-1] != width or (dimensions == 2 and array.shape[0] == 0):
            raise ValueError
        array = np.array(array, dtype=float, copy=True)
        if not np.isfinite(array).all():
            raise ValueError
        return array
    except (TypeError, ValueError, OverflowError):
        raise ValueError("特征或背景数据必须为列数匹配的有限数值。") from None


def _background(
    model: Any, inner: Any, provided: np.ndarray | None, width: int, limit: int, technique: str
) -> tuple[np.ndarray, str | None]:
    data = provided
    if data is None:
        data = getattr(model, "_jit_background", None)
    if data is None and inner is not model:
        data = getattr(inner, "_jit_background", None)
    if data is not None:
        return _array(data, 2, width)[:limit].copy(), None
    if technique == "lime":
        return np.stack([np.zeros(width), np.ones(width), -np.ones(width)]), _SYNTHETIC_WARNING
    return np.zeros((1, width)), None


def _shap_row(values: Any, width: int) -> np.ndarray:
    if isinstance(values, list):
        if len(values) not in (1, 2):
            raise ValueError
        values = values[1] if len(values) == 2 else values[0]
    array = np.asarray(values, dtype=float)
    if array.ndim == 3:
        if array.shape[2] not in (1, 2):
            raise ValueError
        array = array[:, :, 1 if array.shape[2] == 2 else 0]
    if array.shape != (1, width) or not np.isfinite(array).all():
        raise ValueError
    return array[0].copy()


def _shap_base(value: Any) -> float:
    array = np.asarray(value, dtype=float).reshape(-1)
    if array.size not in (1, 2) or not np.isfinite(array).all():
        raise ValueError
    return float(array[1 if array.size == 2 else 0])


def _shap(
    inner: Any, transformer: Any, vector: np.ndarray, background: np.ndarray, model_family: str
) -> tuple[np.ndarray, float]:
    import shap

    width = len(vector)
    rows = vector.reshape(1, -1).copy()
    if transformer is not None:
        rows = _array(transformer.transform(rows), 2, width)
        background = _array(transformer.transform(background.copy()), 2, width)
    if model_family == "tree":
        explainer = shap.TreeExplainer(inner, data=background)
    else:
        # SHAP's default background subsampling would change the caller's selected reference mean.
        masker = shap.maskers.Independent(background, max_samples=len(background))
        explainer = shap.LinearExplainer(inner, masker)
    # Scaled-space SHAP values already contain the scale factor; dividing again breaks additivity.
    return _shap_row(explainer.shap_values(rows), width), _shap_base(explainer.expected_value)


def _probability_callback(model: Any):
    classes = np.asarray(getattr(model, "classes_", None))
    if (
        classes.ndim != 1
        or len(classes) not in (1, 2)
        or any(label not in (0, 1) for label in classes)
        or len(set(classes.tolist())) != len(classes)
    ):
        raise ValueError

    def predict(rows: np.ndarray) -> np.ndarray:
        probabilities = np.asarray(model.predict_proba(np.array(rows, copy=True)), dtype=float)
        if (
            probabilities.shape != (len(rows), len(classes))
            or not np.isfinite(probabilities).all()
            or np.any(probabilities < 0)
            or np.any(probabilities > 1)
        ):
            raise ValueError
        result = np.zeros((len(rows), 2))
        for index, label in enumerate(classes):
            result[:, int(label)] = probabilities[:, index]
        return result

    return predict


def _lime(
    model: Any, vector: np.ndarray, names: list[str], background: np.ndarray, params: dict
) -> tuple[np.ndarray, float]:
    from lime.lime_tabular import LimeTabularExplainer

    callback = _probability_callback(model)
    explainer = LimeTabularExplainer(
        background,
        feature_names=list(names),
        class_names=["no defect", "defect"],
        mode="classification",
        discretize_continuous=False,
        random_state=params["seed"],
        kernel_width=params["kernel_width"],
    )
    explanation = explainer.explain_instance(
        vector.copy(), callback, num_features=len(names), num_samples=params["num_samples"]
    )
    coefficients = np.zeros(len(names))
    seen = set()
    for index, coefficient in explanation.local_exp[1]:
        if (
            not isinstance(index, (int, np.integer))
            or isinstance(index, (bool, np.bool_))
            or index < 0
            or index >= len(names)
            or index in seen
        ):
            raise ValueError
        seen.add(index)
        coefficients[index] = coefficient
    base = float(explanation.intercept[1])
    if len(seen) != len(names) or not np.isfinite(coefficients).all() or not math.isfinite(base):
        raise ValueError
    return coefficients, base


def _empty(reason: str, message: str, output_space: str) -> dict:
    return {
        "items": [],
        "reason_code": reason,
        "message": message,
        "base_value": None,
        "output_space": output_space,
    }


def explain(
    model: Any,
    vector: Any,
    *,
    feature_names: list[str],
    technique: str = "shap",
    params: dict | None = None,
    background: Any = None,
    top_n: int = 8,
) -> dict:
    normalized = validate_params(technique, params)
    if (
        type(feature_names) is not list
        or not feature_names
        or any(type(name) is not str for name in feature_names)
    ):
        raise ValueError("特征名称必须为非空字符串列表。")
    if type(top_n) is not int or not 1 <= top_n <= 1024:
        raise ValueError("解释数量必须为允许范围内的整数。")
    names = list(feature_names)
    row = _array(vector, 1, len(names))
    provided = _array(background, 2, len(names)) if background is not None else None
    output_space = "local_probability_coefficient" if technique == "lime" else "unknown"
    try:
        model_family = family(model)
        supported = model_family in {"tree", "linear"} or (
            model_family == "tabular" and technique == "lime"
        )
        if not supported:
            return _empty(
                "unsupported_model_family", "该模型类型不支持所选解释技术。", output_space
            )
        if technique == "shap":
            output_space = "log_odds" if model_family == "linear" else "tree_raw"
        inner, transformer = _parts(model)
        limit = normalized["background_size"] if technique == "shap" else 128
        reference, message = _background(model, inner, provided, len(names), limit, technique)
        if technique == "shap":
            coefficients, base = _shap(inner, transformer, row, reference, model_family)
        else:
            coefficients, base = _lime(model, row, names, reference, normalized)
        order = sorted(range(len(names)), key=lambda index: (-abs(coefficients[index]), index))
        items = [
            {
                "feature": names[index],
                "raw_value": float(row[index]),
                "contribution": float(coefficients[index]),
                "direction": "increase"
                if coefficients[index] > 0
                else ("decrease" if coefficients[index] < 0 else "neutral"),
                "rank": rank,
                "output_space": output_space,
            }
            for rank, index in enumerate(order[:top_n], 1)
        ]
        return {
            "items": items,
            "reason_code": None,
            "message": message,
            "base_value": base,
            "output_space": output_space,
        }
    except Exception:
        return _empty("explainer_failed", "解释生成失败，请检查模型与输入是否兼容。", output_space)


def _worker_main() -> None:
    import base64
    import io
    import json
    import os
    import sys
    from contextlib import redirect_stdout
    from pathlib import Path

    try:
        if os.name == "posix":
            import resource

            for limit, value in (
                (resource.RLIMIT_CPU, 90),
                (resource.RLIMIT_FSIZE, 32 * 1024 * 1024),
                (resource.RLIMIT_CORE, 0),
            ):
                _, hard = resource.getrlimit(limit)
                bound = value if hard == resource.RLIM_INFINITY else min(value, hard)
                resource.setrlimit(limit, (bound, bound))
        backend_root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(backend_root))
        sys.path.insert(0, str(backend_root.parent / "data_model"))
        payload = json.load(sys.stdin)
        # Deserialization is confined to the worker; the parent must apply its OS sandbox first.
        with redirect_stdout(sys.stderr):
            import ctypes
            import importlib

            import joblib

            importlib.import_module("shap")
            importlib.import_module("lime.lime_tabular")

            if sys.platform != "darwin" or not payload.get("sandbox_profile"):
                raise ValueError("OS sandbox required")
            library = ctypes.CDLL("/usr/lib/libsandbox.dylib")
            error = ctypes.c_char_p()
            if (
                library.sandbox_init(payload["sandbox_profile"].encode(), 0, ctypes.byref(error))
                != 0
            ):
                raise ValueError("OS sandbox initialization failed")
            model = joblib.load(io.BytesIO(base64.b64decode(payload["weights"], validate=True)))
            results = [
                {
                    "commit_hash": row["commit_hash"],
                    "technique": technique,
                    **explain(
                        model,
                        row["features"],
                        feature_names=payload["feature_names"],
                        technique=technique,
                        params=payload.get("params", {}).get(technique),
                        top_n=payload.get("top_n", 8),
                    ),
                }
                for row in payload["rows"]
                for technique in payload["techniques"]
            ]
        sys.stdout.write(json.dumps(results, ensure_ascii=False, allow_nan=False) + "\n")
    except Exception:
        sys.stderr.write("解释任务执行失败。\n")
        raise SystemExit(1) from None


if __name__ == "__main__":
    _worker_main()
