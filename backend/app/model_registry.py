"""模型加载器（方案 A）：启动时加载 MODEL_DIR 下 .pkl，供 POST /api/predict 实时推理。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib

from app import config

logger = logging.getLogger("backend.model_registry")


def version_key(name: str) -> tuple[str, int]:
    """「最新模型」的单一定义：模型名尾数字段的版本序（xgb_v2 > xgb_v1）。

    同族前缀比尾数；不同族退化为按名字典序。predicted_at / mtime 只反映
    「谁最后被跑过 / 文件最后被改过」，不代表版本新旧（PR #30 审 2）。
    """
    m = re.match(r"^(.*?)(\d+)$", name)
    return (m.group(1), int(m.group(2))) if m else (name, -1)


@dataclass
class ModelEntry:
    name: str
    path: Path
    mtime: float
    model: Any = field(repr=False)
    explainer: Any = field(default=None, repr=False)


_REGISTRY: dict[str, ModelEntry] = {}


def load_models() -> None:
    _REGISTRY.clear()
    model_dir = config.MODEL_DIR
    if not model_dir.is_dir():
        logger.warning("model dir not found, predict will return 50000 until models are delivered")
        return
    for path in sorted(model_dir.glob("*.pkl")):
        try:
            model = joblib.load(path)
        except Exception:
            # 契约三：加载失败只写服务端日志，不回显文件路径
            logger.exception("model load failed")
            continue
        n_features = _feature_count(model)
        if n_features is not None and n_features != len(config.FEATURE_COLUMNS):
            # 交付说明：特征宽度不对不会报错、只会静默给出错误答案 —— 加载期就拒收（Issue #46）
            logger.error(
                "model skipped: expects %s features, contract has %s",
                n_features,
                len(config.FEATURE_COLUMNS),
            )
            continue
        _REGISTRY[path.stem] = ModelEntry(path.stem, path, path.stat().st_mtime, model)
    logger.info("loaded models: %s", sorted(_REGISTRY))


def _feature_count(model: Any) -> int | None:
    n = getattr(model, "n_features_in_", None)
    if n is None and hasattr(model, "get_booster"):
        try:
            n = model.get_booster().num_features()
        except Exception:
            logger.exception("feature count unavailable")
            return None
    return int(n) if n is not None else None


def get_model(name: str) -> ModelEntry:
    return _REGISTRY[name]


def has(name: str) -> bool:
    return name in _REGISTRY


def default_model() -> ModelEntry | None:
    if not _REGISTRY:
        return None
    return max(_REGISTRY.values(), key=lambda entry: version_key(entry.name))


def predict_proba(model: Any, vector: list[float]) -> float:
    proba = model.predict_proba([vector])[0]
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else len(classes) - 1
    return float(proba[idx])


def get_explainer(entry: ModelEntry):
    """惰性构造并缓存 SHAP explainer（审 3）；构造失败抛给 explain 降级。

    线性 Pipeline（scaler → 线性模型，交付包 lr_v1 形态）解包为内层估计器构造，
    shap 0.52 的 LinearExplainer 不接受 Pipeline 本体（Issue #50）。
    """
    if entry.explainer is None:
        import shap

        inner, scaler = _linear_pipeline_parts(entry.model)
        if _is_tree_family(inner):
            entry.explainer = shap.TreeExplainer(inner)
        else:
            background = _background_for(inner, config.FEATURE_COLUMNS)
            if scaler is not None:
                background = scaler.transform(background)
            entry.explainer = shap.LinearExplainer(inner, background)
    return entry.explainer


def _linear_pipeline_parts(model: Any) -> tuple[Any, Any]:
    """Pipeline(scaler → 线性模型) → (内层模型, scaler)；其余形态原样返回 (model, None)。"""
    steps = getattr(model, "steps", None)
    if steps is not None and len(steps) == 2:
        scaler, inner = (step for _, step in steps)
        if (
            hasattr(scaler, "transform")
            and hasattr(scaler, "scale_")
            and hasattr(inner, "coef_")
        ):
            return inner, scaler
    return model, None


def _first_row(values: Any) -> list[float]:
    """shap_values 输出归一化为单行：list 取正类；3 维数组（shap 0.52 对森林按类返回）取 [:, :, 1]。"""
    import numpy as np

    if isinstance(values, list):
        values = values[-1]
    arr = np.asarray(values)
    if arr.ndim == 3:
        arr = arr[:, :, 1] if arr.shape[2] > 1 else arr[:, :, 0]
    return [float(v) for v in arr[0]]


def explain(entry: ModelEntry, vector: list[float]) -> list[dict]:
    """SHAP 逐特征解释（契约三冻结结论）；解释器不可用返回空数组并记日志。"""
    try:
        import numpy as np

        _, scaler = _linear_pipeline_parts(entry.model)
        X = np.array([vector], dtype=float)
        if scaler is not None:
            X = scaler.transform(X)
        row = _first_row(get_explainer(entry).shap_values(X))
        if scaler is not None:
            # 线性变换下 SHAP 贡献可严格折算回原始特征量纲：raw = scaled / scale_（符号不变）
            row = [value / float(scale) for value, scale in zip(row, scaler.scale_)]
    except Exception:
        logger.exception("shap explanation unavailable")
        return []
    return [
        {
            "feature": name,
            "contribution": round(abs(value), 6),
            "direction": "increase" if value > 0 else "decrease",
        }
        for name, value in zip(config.FEATURE_COLUMNS, row)
        if value != 0
    ]


def _is_tree_family(model: Any) -> bool:
    module = type(model).__module__ or ""
    name = type(model).__name__
    return (
        module.startswith(("sklearn.tree", "sklearn.ensemble", "xgboost"))
        or "Tree" in name
        or "Forest" in name
        or "Boost" in name
    )


def _background_for(model: Any, vector: list[float]):
    import numpy as np

    background = getattr(model, "_jit_background", None)
    if background is not None:
        return background
    return np.zeros((1, len(vector)))
