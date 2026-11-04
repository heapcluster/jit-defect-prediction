"""提交查询的共享组装逻辑（供 commits 路由与其它服务复用）。

只放「纯组装 / 查询片段」，不放 HTTP 相关东西；对外行为（字段、错误码）以
docs/api/commits.md 为准。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app import config, model_registry
from app.explain import with_labels
from app.models import CommitFeature


def default_model_in_table(session: Session | None = None) -> str | None:
    """「默认模型」= 已加载模型中 `version_key` 最大者（docs/database/model.md）。

    与列表 / 详情 / 趋势 / predict / sync 共用 `model_registry.default_model()` 一处实现，
    避免同一提交在多处拿到不同模型的不同分。
    """
    entry = model_registry.default_model()
    return entry.name if entry is not None else None


def feature_dict(feature: CommitFeature | None) -> dict | None:
    """14 项特征 → dict（fix 为整型，其余浮点）。"""
    if feature is None:
        return None
    out: dict = {}
    for name in config.FEATURE_COLUMNS:
        value = getattr(feature, name)
        out[name] = int(value) if name == "fix" else float(value)
    return out


def explanation_for(model_name: str | None, feature: CommitFeature | None) -> list[dict]:
    """SHAP 解释项（附中文因子名）；模型未注册或缺特征时返回空列表。"""
    if not model_name or feature is None or not model_registry.has(model_name):
        return []
    vector = [float(getattr(feature, name)) for name in config.FEATURE_COLUMNS]
    return with_labels(model_registry.explain(model_registry.get_model(model_name), vector))
