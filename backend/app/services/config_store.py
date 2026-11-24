from __future__ import annotations

import copy
import json
import logging
import math
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from app import config, model_registry
from app.errors import AppError
from app.models import Dataset, Model, ModelArtifact, User, UserConfig
from app.timeutil import iso_z, now_naive_utc

logger = logging.getLogger("backend.config")

METRIC_KEYS = ("auc", "ap", "f1", "precision", "recall", "accuracy",
               "recall_at_20", "recall_at_50", "p_norm", "popt")

CONFIG_SCHEMA = {
    "decision_threshold": ("float", "缺陷判定阈值"),
    "risk_high_threshold": ("float", "高风险阈值"),
    "risk_mid_threshold": ("float", "中风险阈值"),
    "default_model": ("string", "默认模型"),
    "default_dataset": ("string", "默认数据集"),
    "default_xai": ("string", "默认解释技术"),
    "metrics_selected": ("list", "默认评估指标"),
    "primary_metric": ("string", "主排序指标"),
    "effort_enabled": ("bool", "启用 effort-aware 评估"),
    "page_prefs": ("object", "页面偏好"),
    "collect.allow_roots": ("list", "允许的本地仓库根目录"),
    "collect.protocol_whitelist": ("list", "允许的仓库协议"),
    "clean.chain_templates": ("object", "清洗链模板"),
    "train.templates": ("object", "训练模板"),
    "predict.batch_size": ("int", "预测批大小"),
    "predict.cache_ttl": ("int", "预测缓存秒数"),
    "predict.retry_max": ("int", "预测最大重试次数"),
    "explain.cache_ttl": ("int", "解释缓存秒数"),
    "explain.compare_enabled": ("bool", "启用解释对比"),
    "localization.weights": ("object", "定位权重"),
    "localization.top_n": ("object", "定位展示文件与行数"),
    "localization.file_size_max": ("int", "源码文件大小上限（字节）"),
    "localization.suggestion_sources": ("list", "修复建议来源"),
}

WEIGHT_DEFAULTS = {
    "file_types": {"source": 1.0, "other": 0.6, "document": 0.4, "test": 0.35, "generated": 0.1},
    "change": {"deleted": 2.0, "modified": 1.5},
    "hunk": 0.15,
    "line_content": {"empty": 0.1, "comment": 0.15, "import": 0.3, "suspicious": 1.5, "normal": 1.0},
    "line_path": {"source": 1.0, "other": 0.9, "document": 0.55, "test": 0.6, "generated": 0.35},
    "mix": {"base": 0.45, "file": 0.35, "hunk": 0.2},
}


def factory_defaults() -> dict:
    return {
        "decision_threshold": 0.5,
        "risk_high_threshold": config.HIGH_RISK_THRESHOLD,
        "risk_mid_threshold": config.MID_RISK_THRESHOLD,
        "default_model": "", "default_dataset": "", "default_xai": "shap",
        "metrics_selected": list(METRIC_KEYS[:6]), "primary_metric": "auc",
        "effort_enabled": True, "page_prefs": {},
        "collect.allow_roots": [str(config.SOURCE_REPO.parent.resolve())] if config.SOURCE_REPO else [],
        "collect.protocol_whitelist": ["https", "git"],
        "clean.chain_templates": {}, "train.templates": {},
        "predict.batch_size": 100, "predict.cache_ttl": 3600, "predict.retry_max": 3,
        "explain.cache_ttl": 3600, "explain.compare_enabled": False,
        "localization.weights": copy.deepcopy(WEIGHT_DEFAULTS),
        "localization.top_n": {"files": 5, "lines": 30},
        "localization.file_size_max": 1024 * 1024,
        "localization.suggestion_sources": ["template"],
    }


def _known_key(key: str) -> None:
    if key not in CONFIG_SCHEMA:
        raise AppError(40001, "未知或不允许保存的配置键")


def read_config(session: Session, keys: list[str] | None = None, user_id: str = "global", current: bool = False) -> list[dict]:
    selected = sorted(CONFIG_SCHEMA) if keys is None else keys
    for key in selected:
        _known_key(key)
    if user_id != "global":
        user = session.get(User, user_id)
        if user is None:
            raise AppError(40400, "配置用户不存在")
        if user.status != "active":
            raise AppError(40100, "用户已禁用")
    statement = select(UserConfig).where(
        UserConfig.user_id.in_({"global", user_id}), UserConfig.config_key.in_(selected))
    if current:
        # MySQL REPEATABLE READ 的旧快照不能用于写入前的跨键校验。
        statement = statement.with_for_update().execution_options(populate_existing=True)
    rows = session.scalars(statement).all()
    saved = {(row.user_id, row.config_key): row for row in rows}
    defaults = factory_defaults()
    items = []
    for key in selected:
        row = saved.get((user_id, key)) or saved.get(("global", key))
        items.append({
            "config_key": key,
            "value": json.loads(row.value_json) if row else defaults[key],
            "value_type": CONFIG_SCHEMA[key][0],
            "source": ("global" if row.user_id == "global" else "user") if row else "factory",
            "updated_at": iso_z(row.updated_at) if row else None,
        })
    return items


def get_value(key: str, session: Session | None = None):
    if session is not None:
        return read_config(session, [key])[0]["value"]
    from app.db import SessionLocal
    with SessionLocal() as owned:
        return read_config(owned, [key])[0]["value"]


def _invalid(key: str) -> None:
    raise AppError(40001, f"配置值非法：{key}")


def _number(value) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _validate_weights(value: dict, defaults: dict, key: str) -> None:
    if not value or set(value) - set(defaults):
        _invalid(key)
    for name, weight in value.items():
        if isinstance(defaults[name], dict):
            if not isinstance(weight, dict):
                _invalid(key)
            _validate_weights(weight, defaults[name], key)
        elif not _number(weight) or weight < 0:
            _invalid(key)


def _validate_value(session: Session, key: str, value) -> None:
    _known_key(key)
    value_type = CONFIG_SCHEMA[key][0]
    expected = {"int": int, "float": float, "string": str, "bool": bool, "list": list, "object": dict}[value_type]
    valid_type = _number(value) if value_type == "float" else type(value) is expected
    if not valid_type:
        _invalid(key)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError):
        _invalid(key)
    if len(encoded.encode("utf-8")) > 65535:
        _invalid(key)
    if key.endswith("threshold") and not 0 < value < 1:
        _invalid(key)
    if value_type == "int":
        minimum = 0 if key.endswith(("cache_ttl", "retry_max")) else 1
        if not minimum <= value <= 2147483647:
            _invalid(key)
    if key == "default_model" and value:
        model = session.get(Model, value)
        artifact = session.scalar(select(ModelArtifact).where(ModelArtifact.model_name == value))
        if model is None:
            raise AppError(40400, "默认模型未登记")
        if not model_registry.has(value) and (artifact is None or artifact.status != "available"):
            _invalid(key)
    if key == "default_dataset" and value:
        dataset = session.get(Dataset, value)
        if dataset is None:
            raise AppError(40400, "默认数据集未登记")
        if dataset.status != "ready":
            _invalid(key)
    if key == "default_xai" and value not in ("shap", "lime"):
        _invalid(key)
    if key in ("metrics_selected", "collect.protocol_whitelist", "localization.suggestion_sources"):
        allowed = {"metrics_selected": METRIC_KEYS, "collect.protocol_whitelist": ("https", "git"),
                   "localization.suggestion_sources": ("template", "llm", "history")}[key]
        if not value or any(type(item) is not str or item not in allowed for item in value) or len(set(value)) != len(value):
            _invalid(key)
    if key == "collect.allow_roots":
        if any(type(item) is not str or not Path(item).is_absolute() for item in value):
            _invalid(key)
        if len(set(value)) != len(value):
            _invalid(key)
    if key == "page_prefs":
        if set(value) - {"page_size", "remember_drawer", "explain_top_n", "collect_branch", "collect_mode"}:
            _invalid(key)
        if "collect_branch" in value and (type(value["collect_branch"]) is not str or len(value["collect_branch"]) > 255 or "\\" in value["collect_branch"] or any(ord(char) < 32 for char in value["collect_branch"])):
            _invalid(key)
        if "collect_mode" in value and value["collect_mode"] not in ("full", "incremental"):
            _invalid(key)
        if "page_size" in value and (type(value["page_size"]) is not int or value["page_size"] not in (10, 20, 50, 100)):
            _invalid(key)
        if "remember_drawer" in value and type(value["remember_drawer"]) is not bool:
            _invalid(key)
        if "explain_top_n" in value and (type(value["explain_top_n"]) is not int or not 1 <= value["explain_top_n"] <= 100):
            _invalid(key)
    if key == "localization.top_n":
        if set(value) != {"files", "lines"} or any(type(n) is not int or not 1 <= n <= 1000 for n in value.values()):
            _invalid(key)
    if key == "localization.weights":
        _validate_weights(value, WEIGHT_DEFAULTS, key)
    if key == "clean.chain_templates":
        from app.services.clean_run import validate_templates
        validate_templates(value)
    if key == "train.templates":
        from app.services.train_run import validate_templates
        validate_templates(value)


def _validate_cross_keys(values: dict) -> None:
    if values["risk_mid_threshold"] >= values["risk_high_threshold"]:
        raise AppError(40001, "中风险阈值必须小于高风险阈值")
    if values["primary_metric"] not in values["metrics_selected"]:
        raise AppError(40001, "主指标必须属于已选择指标")


def _validate_user_overrides(session: Session, global_values: dict, user_id: str) -> None:
    if user_id != "global":
        return
    overrides = session.scalars(select(UserConfig).where(UserConfig.user_id != "global")
                                .with_for_update().execution_options(populate_existing=True)).all()
    by_user = {}
    for row in overrides:
        by_user.setdefault(row.user_id, dict(global_values))[row.config_key] = json.loads(row.value_json)
    for effective in by_user.values():
        _validate_cross_keys(effective)


def _lock_owner(session: Session, user_id: str) -> None:
    seed = insert(User).values(user_id="global", display_name="全局默认", role="system",
                               status="active", created_at=now_naive_utc())
    session.execute(seed.on_duplicate_key_update(user_id=seed.inserted.user_id))
    users = session.scalars(select(User).where(User.user_id.in_({"global", user_id}))
                            .order_by(User.user_id).with_for_update()
                            .execution_options(populate_existing=True)).all()
    owner = next((user for user in users if user.user_id == user_id), None)
    if owner is None:
        raise AppError(40400, "配置用户不存在")
    if owner.status != "active":
        raise AppError(40100, "用户已禁用")


def write_config(session: Session, items: list[dict], user_id: str = "global") -> list[dict]:
    keys = [item["config_key"] for item in items]
    if not items or len(set(keys)) != len(keys):
        raise AppError(40001, "配置批量不能为空或含重复键")
    try:
        _lock_owner(session, user_id)
        current = {item["config_key"]: item["value"] for item in read_config(session, user_id=user_id, current=True)}
        for item in items:
            _validate_value(session, item["config_key"], item["value"])
            current[item["config_key"]] = item["value"]
        _validate_cross_keys(current)
        _validate_user_overrides(session, current, user_id)
        now = now_naive_utc()
        for item in items:
            row = session.get(UserConfig, (user_id, item["config_key"]))
            if row is None:
                row = UserConfig(user_id=user_id, config_key=item["config_key"])
                session.add(row)
            row.value_json = json.dumps(item["value"], ensure_ascii=False, allow_nan=False)
            row.value_type = CONFIG_SCHEMA[item["config_key"]][0]
            row.updated_at = now
        session.commit()
    except Exception:
        session.rollback()
        raise
    logger.info("config saved owner=%s keys=%s", user_id, keys)
    return read_config(session, keys, user_id=user_id)


def delete_config(session: Session, key: str, user_id: str = "global") -> dict:
    _known_key(key)
    try:
        _lock_owner(session, user_id)
        row = session.get(UserConfig, (user_id, key), populate_existing=True, with_for_update=True)
        if row is None:
            raise AppError(40400, "配置键未保存")
        session.delete(row)
        session.flush()
        effective = read_config(session, user_id=user_id, current=True)
        values = {item["config_key"]: item["value"] for item in effective}
        _validate_cross_keys(values)
        _validate_user_overrides(session, values, user_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    item = next(item for item in effective if item["config_key"] == key)
    logger.info("config deleted owner=%s key=%s", user_id, key)
    return {"config_key": key, "deleted": True, "fallback_source": item["source"], "value": item["value"]}


def schema_metadata(session: Session) -> dict:
    models = session.scalars(select(Model.model_name).order_by(Model.model_name)).all()
    datasets = session.scalars(select(Dataset.dataset_id).where(Dataset.status == "ready").order_by(Dataset.dataset_id)).all()
    choices = {"default_model": [""] + list(models), "default_dataset": [""] + list(datasets),
               "default_xai": ["shap", "lime"], "metrics_selected": list(METRIC_KEYS), "primary_metric": list(METRIC_KEYS),
               "collect.protocol_whitelist": ["https", "git"],
               "localization.suggestion_sources": ["template", "llm", "history"]}
    return {key: {"label": label, "value_type": kind, "choices": choices.get(key),
                  "group": key.split(".")[0] if "." in key else "global"}
            for key, (kind, label) in CONFIG_SCHEMA.items()}
