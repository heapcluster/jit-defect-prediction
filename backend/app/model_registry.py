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
    """惰性构造并缓存 SHAP explainer（审 3）；构造失败抛给 explain 降级。"""
    if entry.explainer is None:
        import shap

        if _is_tree_family(entry.model):
            entry.explainer = shap.TreeExplainer(entry.model)
        else:
            entry.explainer = shap.LinearExplainer(
                entry.model, _background_for(entry.model, config.FEATURE_COLUMNS)
            )
    return entry.explainer


def explain(entry: ModelEntry, vector: list[float]) -> list[dict]:
    """SHAP 逐特征解释（契约三冻结结论）；解释器不可用返回空数组并记日志。"""
    try:
        explainer = get_explainer(entry)
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
