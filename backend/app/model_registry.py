"""模型加载器（方案 A）：启动时加载 MODEL_DIR 下 .pkl，供 POST /api/predict 实时推理。"""

from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from io import BytesIO
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
    line: str = "expert"


class ModelUnavailable(RuntimeError):
    """该模型当前无法在线预测（缺编码器/权重宽度不符等）；调用方映射为明确提示，不 500。"""


_REGISTRY: dict[str, ModelEntry] = {}
# 两线全部模型的元数据（name → 目录/线），权重懒加载；不含 model 对象
_CATALOG: dict[str, ModelEntry] = {}
_LINE_OF: dict[str, str] = {}
_LINE_WIDTH = {"expert": 14, "semantic": 768}


def _delivery_models(model_dir: Path) -> list[str] | None:
    """交付清单是在线模型与特征列序的唯一来源；缺失或漂移时拒绝加载。"""
    manifest = model_dir / "feature_order.txt"
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError:
        logger.error("model delivery manifest unavailable")
        return None

    section = ""
    names: list[str] = []
    columns: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == "models":
            name = line.split()[0]
            if re.fullmatch(r"[A-Za-z0-9_]+\.pkl", name) is None or name in names:
                logger.error("model delivery manifest has invalid model entry")
                return None
            names.append(name)
        elif section == "feature_order":
            match = re.fullmatch(r"\d+\.\s*([a-z_]+)", line)
            if match is None:
                logger.error("model delivery manifest has invalid feature order")
                return None
            columns.append(match.group(1))
    if not names or tuple(columns) != config.FEATURE_COLUMNS:
        logger.error("model delivery manifest does not match feature contract")
        return None
    return names


def _scan_manifest(models_dir: Path, manifest_name: str, line: str) -> None:
    """把一条线清单里的模型登记进 _CATALOG（只记路径，不加载权重）。"""
    manifest = models_dir / manifest_name
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except OSError:
        logger.warning("%s line manifest unavailable: %s", line, manifest)
        return
    section = ""
    for raw in lines:
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("[") and text.endswith("]"):
            section = text[1:-1]
            continue
        if section != "models":
            continue
        name = text.split()[0]
        if re.fullmatch(r"[A-Za-z0-9_]+\.pkl", name) is None or name in _CATALOG:
            continue
        path = models_dir / name
        if not path.is_file():
            logger.warning("%s line model missing: %s", line, name)
            continue
        _CATALOG[path.stem] = ModelEntry(path.stem, path, path.stat().st_mtime, None, line=line)
        _LINE_OF[path.stem] = line


def _scan_other_lines() -> None:
    """登记 semantic 线模型（懒加载，启动不读大权重）。"""
    pipelines = config.PIPELINES_DIR
    _scan_manifest(pipelines / "semantic" / "models", "load_manifest.txt", "semantic")


def load_models() -> None:
    model_code_dir = str((config.REPO_ROOT / "data_model").resolve())
    if model_code_dir not in sys.path:
        sys.path.insert(0, model_code_dir)
    _REGISTRY.clear()
    _CATALOG.clear()
    _LINE_OF.clear()
    _scan_other_lines()
    model_dir = config.MODEL_DIR
    if not model_dir.is_dir():
        logger.warning("model dir not found, predict will return 50000 until models are delivered")
        return
    failed: list[str] = []
    names = _delivery_models(model_dir)
    if names is None:
        return
    for name in names:
        path = model_dir / name
        if not path.is_file():
            logger.error("declared delivery model missing: %s", path.stem)
            failed.append(path.stem)
            continue
        try:
            model = joblib.load(path)
        except Exception:
            # 契约三：加载失败只写服务端日志，不回显文件路径
            logger.exception("model load failed: %s", path.stem)
            failed.append(path.stem)
            continue
        n_features = _feature_count(model)
        if n_features is not None and n_features != len(config.FEATURE_COLUMNS):
            # 交付说明：特征宽度不对不会报错、只会静默给出错误答案 —— 加载期就拒收（Issue #46）
            logger.error(
                "model skipped: expects %s features, contract has %s",
                n_features,
                len(config.FEATURE_COLUMNS),
            )
            failed.append(path.stem)
            continue
        _REGISTRY[path.stem] = ModelEntry(path.stem, path, path.stat().st_mtime, model)
    logger.info("loaded models: %s", sorted(_REGISTRY))
    if failed:
        logger.error("failed models: %s", failed)


def _feature_count(model: Any) -> int | None:
    n = getattr(model, "n_features_in_", None)
    if n is None and hasattr(model, "get_booster"):
        try:
            n = model.get_booster().num_features()
        except Exception:
            logger.exception("feature count unavailable")
            return None
    return int(n) if n is not None else None


def load_trained(name: str, weights: bytes) -> ModelEntry:
    """热加载本次训练自产的 expert 包权重（字节由本服务 joblib.dump 生成，非任意上传 pickle）。

    校验特征列宽后放入运行时注册表，不重启、不改默认模型配置。通用已登记工件的
    加载端点属 predict/模型管理（W6）安全面，不在此开放任意 zip 反序列化。
    """
    model = joblib.load(BytesIO(weights))
    width = _feature_count(model)
    if width is not None and width != len(config.FEATURE_COLUMNS):
        raise ValueError(f"trained model expects {width} features, contract has {len(config.FEATURE_COLUMNS)}")
    entry = ModelEntry(name, Path(name), time.time(), model, line="expert")
    _REGISTRY[name] = entry
    _LINE_OF[name] = "expert"
    return entry


_RUNTIME: dict[str, dict] = {}


def runtime_state(name: str) -> dict:
    if name in _RUNTIME:
        return _RUNTIME[name]
    return {"state": "loaded" if name in _REGISTRY else "unloaded", "error": None}


def load_artifact_package(name: str, zip_bytes: bytes, *, line: str) -> ModelEntry:
    """校验 §3.3 包（checksum/元数据/特征列宽）后再反序列化权重，失败保留旧实例。"""
    from app.services import file_contracts as fc
    from app.services import storage
    try:
        meta = storage.model_package(f"{name}.zip", zip_bytes)
        if meta["line"] != line:
            raise ValueError("model line disagrees with registration")
        members = fc.read_zip(f"{name}.zip", zip_bytes)
        weight_name = next(key for key in members if key.endswith(".pkl"))
        model = joblib.load(BytesIO(members[weight_name]))
        width = _feature_count(model)
        expected = _LINE_WIDTH.get(line)
        if expected is not None and width is not None and width != expected:
            raise ValueError(f"feature width {width} != contract {expected}")
        entry = ModelEntry(name, Path(name), time.time(), model, line=line)
        _REGISTRY[name] = entry
        _LINE_OF[name] = line
        _RUNTIME[name] = {"state": "loaded", "error": None}
        return entry
    except Exception as exc:
        state = "loaded" if name in _REGISTRY else "load_failed"
        _RUNTIME[name] = {"state": state, "error": str(exc)[:200]}
        raise


def unload(name: str) -> None:
    _REGISTRY.pop(name, None)
    _RUNTIME[name] = {"state": "unloaded", "error": None}


def get_model(name: str) -> ModelEntry:
    entry = _REGISTRY.get(name)
    if entry is not None:
        return entry
    meta = _CATALOG.get(name)
    if meta is None:
        raise KeyError(name)
    try:
        model = joblib.load(meta.path)
    except Exception as exc:
        logger.exception("lazy model load failed: %s", name)
        raise ModelUnavailable(f"{meta.line} 模型权重无法加载") from exc
    expected = _LINE_WIDTH.get(meta.line)
    n = _feature_count(model)
    if expected is not None and n is not None and n != expected:
        raise ModelUnavailable(f"{meta.line} 模型特征宽度 {n} 与契约 {expected} 不符")
    loaded = ModelEntry(name, meta.path, meta.mtime, model, line=meta.line)
    _REGISTRY[name] = loaded
    return loaded


def has(name: str) -> bool:
    return name in _REGISTRY or name in _CATALOG


def line_of(name: str) -> str:
    return _LINE_OF.get(name, "expert")


def expected_width(line: str) -> int | None:
    return _LINE_WIDTH.get(line)


def all_models() -> list[ModelEntry]:
    """已加载的全部模型（供「一次现算特征、逐模型打分」的批量场景使用，如 PR 同步）。"""
    return list(_REGISTRY.values())


def prewarm_model() -> ModelEntry | None:
    """任选一个已加载的 expert 模型用于启动预热，不是默认模型（运行入口必须显式选模型）。"""
    experts = [entry for entry in _REGISTRY.values() if entry.line == "expert"]
    if not experts:
        return None
    return max(experts, key=lambda entry: version_key(entry.name))


def warmup() -> None:
    """预热一个已加载模型的推理与 SHAP，避免首个并发请求承担解释器初始化尖峰（#230）。"""
    entry = prewarm_model()
    if entry is None:
        return
    vector = [0.0] * len(config.FEATURE_COLUMNS)
    try:
        predict_proba(entry.model, vector)
    except Exception:
        logger.exception("model warmup failed")


def predict_proba(model: Any, vector: list[float]) -> float:
    proba = model.predict_proba([vector])[0]
    classes = list(getattr(model, "classes_", [0, 1]))
    idx = classes.index(1) if 1 in classes else len(classes) - 1
    return float(proba[idx])
