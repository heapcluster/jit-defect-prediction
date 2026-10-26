"""提交查询的共享组装逻辑（供 commits 路由与其它服务复用）。

只放「纯组装 / 查询片段」，不放 HTTP 相关东西；对外行为（字段、错误码）保持不变。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, model_registry
from app.explain import with_labels
from app.models import CommitFeature, CommitLabel, Prediction
from app.timeutil import iso_z

# 人工反馈标签的 label_method 取值：与 SZZ 自动标签靠唯一约束隔离
MANUAL_LABEL_METHOD = "manual"


def default_model_in_table(session: Session) -> str | None:
    """「默认最新」单一定义（审 2）：表内模型按 version_key 版本序取最大者。"""
    names = session.execute(select(Prediction.model_name).distinct()).scalars().all()
    return max(names, key=model_registry.version_key) if names else None


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


def label_for(session: Session, commit_hash: str) -> dict | None:
    """人工反馈标签；未标记返回 None（MUST NOT 返回占位空对象）。"""
    row = session.execute(
        select(CommitLabel).where(
            CommitLabel.commit_hash == commit_hash,
            CommitLabel.label_method == MANUAL_LABEL_METHOD,
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return {
        "commit_hash": commit_hash,
        "is_defect": bool(row.is_bug_inducing),
        "labeled_at": iso_z(row.labeled_at),
    }


def labeled_hashes_stmt():
    """已人工确认的 commit_hash 子查询（仅查看过滤用，不触发预测）。"""
    return select(CommitLabel.commit_hash).where(
        CommitLabel.label_method == MANUAL_LABEL_METHOD
    )
