"""解释因子中文名：14 项 Kamei 特征的统一中文标签（契约二 feature_columns）。

集中一处维护，供 `predict`、commit 详情与 PR 理由共用 —— MUST NOT 在各处各写一份字典，
否则新增/改名特征时口径会漂移（PR 理由说「改动量大」而详情说「LA 高」）。
"""

from __future__ import annotations

FEATURE_LABELS: dict[str, str] = {
    "ns": "变更子系统多",
    "nd": "变更目录多",
    "nf": "改动文件多",
    "entropy": "改动分散",
    "la": "代码改动量大",
    "ld": "删除代码多",
    "lt": "测试改动少",
    "fix": "历史修复标记",
    "ndev": "涉及开发者多",
    "age": "文件陈旧",
    "nuc": "近期改动频繁",
    "exp": "作者历史经验低",
    "rexp": "作者项目经验低",
    "sexp": "作者近期经验低",
}


def explain_label(feature: str) -> str:
    """取因子中文名；未知因子回退为原名，MUST NOT 报错或返回空。"""
    return FEATURE_LABELS.get(feature, feature)


def with_labels(explanation: list[dict]) -> list[dict]:
    """给解释项列表补 `label` 字段（返回新列表，不改原对象）。"""
    return [{**item, "label": explain_label(item.get("feature", ""))} for item in explanation]
