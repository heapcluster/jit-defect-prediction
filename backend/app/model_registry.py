"""模型加载器（方案 A）：启动时加载 MODEL_DIR 下 .pkl，供 POST /api/predict 实时推理。"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app import config

logger = logging.getLogger("backend.model_registry")


@dataclass
class ModelEntry:
    name: str
    path: Path
    mtime: float
    model: Any = field(repr=False)


_REGISTRY: dict[str, ModelEntry] = {}


def load_models() -> None:
    _REGISTRY.clear()
    model_dir = config.MODEL_DIR
    if not model_dir.is_dir():
        logger.warning("model dir not found, predict will return 50000 until models are delivered")
        return
    for path in sorted(model_dir.glob("*.pkl")):
        try:
            with open(path, "rb") as fh:
                model = pickle.load(fh)
        except Exception:
            # 契约三：加载失败只写服务端日志，不回显文件路径
            logger.exception("model load failed")
            continue
        _REGISTRY[path.stem] = ModelEntry(path.stem, path, path.stat().st_mtime, model)
    logger.info("loaded models: %s", sorted(_REGISTRY))


def get_model(name: str) -> ModelEntry:
    return _REGISTRY[name]


def has(name: str) -> bool:
    return name in _REGISTRY


def default_model() -> ModelEntry | None:
    if not _REGISTRY:
        return None
    return max(_REGISTRY.values(), key=lambda entry: entry.mtime)


def predict_proba(model: Any, vector: list[float]) -> float:
    proba = model.predict_proba([vector])[0]
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else len(classes) - 1
    return float(proba[idx])


def explain(model: Any, vector: list[float]) -> list[dict]:
    """SHAP 逐特征解释（契约三冻结结论）；不支持的解释器返回空数组并记日志。"""
    try:
        import shap

        if _is_tree_family(model):
            explainer = shap.TreeExplainer(model)
        else:
            explainer = shap.LinearExplainer(model, _background_for(model, vector))
        values = explainer.shap_values([vector])
        if isinstance(values, list):
            values = values[-1]
        row = [float(v) for v in values[0]]
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
