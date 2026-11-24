"""W5 训练注册表（CORE，file-only，无数据库）。

单一来源约束：
  · 分类器构造只来自 `pipelines/expert/model.py build_model(name, seed)`；
  · 超参 schema 的 **default 一律从 build_model(algo, 42).get_params() 现取**，
    本文件只提供 min/max/choices/type/description 元数据与可调子集 —— 不复制默认值，
    构造器改了这里自动跟上，不会漂移；
  · seed 是顶层参数（传给 build_model），不是超参。

按最新契约只保留 expert / semantic 两线，每线 12 个注册项
（8 个 DEFAULT_MODELS 默认启用，nb/dt/knn/mlp 注册但默认关闭）。
两线都能从 collected_commits 二维表训练：expert 内部从绑定仓库现算 14 维，
semantic 内部用预计算 npz 或绑定仓库的提交文本经冻结头 CodeBERT 编码为 768 维；
内部来源缺失时训练前置拒绝（40001），不伪造向量。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

LINES = ("expert", "semantic")

INPUT_REQUIREMENTS = {
    "expert": "collected_commits/clean_dataset table (14-dim features computed in-train from bound repo)",
    "semantic": "collected_commits/clean_dataset table (768-dim embeddings from precomputed npz "
    "or frozen CodeBERT encoding of bound repo commit text)",
}


class TrainError(ValueError):
    """训练前置校验失败（作业前 40001；与 CleanError 同口径）。"""

    code = 40001

    def __init__(self, message):
        self.message = message
        super().__init__(message)


def _expert():
    for source in (ROOT / "backend", ROOT / "data_model"):
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
    from pipelines.expert import config, model

    return config, model


def _invalid(message):
    raise TrainError(message)


# 可调子集 + 边界元数据（default 不在此处：从 build_model get_params 现取）。
# Pipeline 步前缀（lr__/svm__/knn__/mlp__/tabnet__）与构造器返回对象一致。
_TUNABLE = {
    "lr": {
        "lr__C": ("number", 1e-6, 1e6, None, "逆正则化强度（越大越弱正则）。"),
        "lr__max_iter": ("integer", 1, 100000, None, "求解器最大迭代次数。"),
    },
    "rf": {
        "n_estimators": ("integer", 1, 5000, None, "树的数量。"),
        "max_depth": ("integer", 1, 100, None, "单棵树最大深度。"),
        "min_samples_leaf": ("integer", 1, 10000, None, "叶节点最少样本数。"),
    },
    "xgb": {
        "n_estimators": ("integer", 1, 5000, None, "提升轮数。"),
        "learning_rate": ("number", 1e-4, 1.0, None, "学习率（eta）。"),
        "max_depth": ("integer", 1, 30, None, "单棵树最大深度。"),
        "subsample": ("number", 0.1, 1.0, None, "行采样比例。"),
        "colsample_bytree": ("number", 0.1, 1.0, None, "建树列采样比例。"),
    },
    "lgbm": {
        "n_estimators": ("integer", 1, 5000, None, "提升轮数。"),
        "learning_rate": ("number", 1e-4, 1.0, None, "学习率。"),
        "num_leaves": ("integer", 2, 1024, None, "单棵树叶子数上限。"),
        "subsample": ("number", 0.1, 1.0, None, "行采样比例（bagging，subsample_freq 已开）。"),
        "colsample_bytree": ("number", 0.1, 1.0, None, "建树列采样比例。"),
    },
    "et": {
        "n_estimators": ("integer", 1, 5000, None, "树的数量。"),
        "min_samples_leaf": ("integer", 1, 10000, None, "叶节点最少样本数。"),
    },
    "svm": {
        "svm__C": ("number", 1e-6, 1e6, None, "惩罚系数 C。"),
        "svm__gamma": ("string", None, None, ["scale", "auto"], "RBF 核系数口径。"),
    },
    "nb": {
        "var_smoothing": ("number", 1e-12, 1.0, None, "方差平滑项（占最大方差比例）。"),
    },
    "dt": {
        "max_depth": ("integer", 1, 100, None, "树最大深度。"),
        "min_samples_leaf": ("integer", 1, 10000, None, "叶节点最少样本数。"),
    },
    "knn": {
        "knn__n_neighbors": ("integer", 1, 1000, None, "近邻数 k。"),
    },
    "mlp": {
        "mlp__max_iter": ("integer", 1, 10000, None, "最大迭代轮数。"),
        "mlp__alpha": ("number", 1e-8, 1.0, None, "L2 正则系数。"),
    },
    "mlp_deep": {
        "mlp__max_iter": ("integer", 1, 10000, None, "最大迭代轮数。"),
        "mlp__alpha": ("number", 1e-8, 1.0, None, "L2 正则系数。"),
        "mlp__n_iter_no_change": ("integer", 1, 1000, None, "早停耐心轮数。"),
        "mlp__validation_fraction": ("number", 0.01, 0.5, None, "训练集内部早停验证比例。"),
    },
    "tabnet": {
        "tabnet__max_epochs": ("integer", 1, 1000, None, "最大训练轮数。"),
        "tabnet__patience": ("integer", 1, 1000, None, "早停耐心轮数。"),
        "tabnet__validation_fraction": ("number", 0.01, 0.5, None, "训练集内部早停验证比例。"),
    },
}


def _schema(algo):
    _, model = _expert()
    params = model.build_model(algo, 42).get_params()
    schema = []
    for name, (kind, minimum, maximum, choices, description) in _TUNABLE[algo].items():
        if name not in params:
            _invalid(f"Registry tunable {algo}.{name} absent from build_model get_params")
        schema.append(
            {
                "name": name,
                "type": kind,
                "default": params[name],
                "min": minimum,
                "max": maximum,
                "choices": choices,
                "description": description,
            }
        )
    return schema


def algorithms(line=None, enabled_only=False) -> list[dict]:
    """注册目录：expert/semantic 两线各 12 项，每线 8 项默认启用。"""
    if line is not None and line not in LINES:
        _invalid(f"Unknown line: {line}")
    config, model = _expert()
    items = []
    for current in LINES:
        if line is not None and current != line:
            continue
        entries = [
            {
                "algo": algo,
                "family": model.MODEL_CLASS[algo],
                "enabled": algo in config.DEFAULT_MODELS,
                "description": model.MODEL_NAMES[algo],
                "hyperparams_schema": _schema(algo),
            }
            for algo in model.MODEL_NAMES
        ]
        for entry in entries:
            if enabled_only and not entry["enabled"]:
                continue
            items.append(
                {"line": current, **entry, "input_requirements": INPUT_REQUIREMENTS[current]}
            )
    return items


def _check_value(spec, value, where):
    kind = spec["type"]
    if kind == "integer":
        if type(value) is not int:
            _invalid(f"{where} must be an integer, not boolean/float/string")
    elif kind == "number":
        if type(value) not in (int, float) or not math.isfinite(value):
            _invalid(f"{where} must be a finite native number, not a boolean or string")
    elif kind == "string":
        if not isinstance(value, str) or value not in (spec["choices"] or []):
            _invalid(f"{where} must be one of {spec['choices']}")
    else:
        _invalid(f"{where} has unsupported schema type {kind}")
    if kind in ("integer", "number"):
        if (
            spec["min"] is not None
            and value < spec["min"]
            or spec["max"] is not None
            and value > spec["max"]
        ):
            _invalid(f"{where} is out of range [{spec['min']}, {spec['max']}]")


def validate_selection(line, algos, hyperparams) -> dict:
    """作业前校验并归一化 {line, algos, hyperparams}；任何非法 → TrainError(40001)。

    expert / semantic 两线均可从 collected_commits 二维表训练，特征在训练内部生成；
    缺绑定仓库或编码器不可用时由 train 内核前置拒绝，不在此处一刀切拦截 semantic。
    """
    if not isinstance(line, str) or line not in LINES:
        _invalid(f"Unknown line: {line}")
    if not isinstance(algos, list) or not algos or any(not isinstance(a, str) for a in algos):
        _invalid("algos must be a nonempty list of algorithm names")
    if len(set(algos)) != len(algos):
        _invalid("algos must not contain duplicates")
    catalog = {item["algo"]: item for item in algorithms(line=line)}
    for algo in algos:
        if algo not in catalog:
            _invalid(f"Unknown algorithm for line {line}: {algo}")
        if not catalog[algo]["enabled"]:
            _invalid(f"Algorithm {algo} is registered but disabled (default-off); not selectable")
    if not isinstance(hyperparams, dict):
        _invalid("hyperparams must be an object keyed by algorithm")
    normalized = {}
    for algo, overrides in hyperparams.items():
        if algo not in algos:
            _invalid(f"hyperparams reference unselected or unknown algorithm: {algo}")
        if not isinstance(overrides, dict):
            _invalid(f"hyperparams[{algo}] must be an object")
        specs = {param["name"]: param for param in catalog[algo]["hyperparams_schema"]}
        applied = {}
        for name, value in overrides.items():
            if name not in specs:
                _invalid(f"Unknown hyperparameter for {algo}: {name}")
            _check_value(specs[name], value, f"{algo}.{name}")
            applied[name] = value
        normalized[algo] = applied
    return {"line": line, "algos": list(algos), "hyperparams": normalized}
