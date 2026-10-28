"""全站「默认模型」的唯一入口（契约三 §17）。

只有一个问题需要回答：**没显式指定模型时，这一处算的是哪个模型？**
列表 / 详情 / 趋势 / 单条预测 / 同步判据 / PR 门禁必须给同一个答案，否则切一次
`champion_model` 就会出现「同一提交在两个页面两个模型两份分」——这也是 #179 想
消灭、但只收口了读路径那一半的问题。

解析顺序（唯一定义，其他地方不得各自实现一遍）：

1. `runtime_setting.champion_model` 且该模型已加载且在 `prediction` 表里有行 → 用它；
2. 冠军未配置 / 未加载 / 还没有任何预测行 → 按 `version_key` 降序取**表里有行**的最新模型
   （降级而不是让列表空掉：冠军刚切到还没补齐数据的模型时，页面应该还能看；
   `MUST` 通过响应里的 `model_name` 回显实际所用模型，前端已按 #183 回显）；
3. 表里一行都没有（空库 / 历史库）→ 返回 `None`：读路径（列表 / 详情 / 趋势）不加模型过滤，
   列表为空即可；`services.predict.resolve_model_name` 侧因为必须给出一个模型名，
   在那里回退注册表冠军。回退只有一处实现，不在别处各写一遍。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import model_registry
from app.models import Model, Prediction


def _has_rows(session: Session, model_name: str) -> bool:
    """该模型是否存在任意预测行：走 `(model_name, risk_score)` 索引前缀，不做全表扫。"""
    return (
        session.execute(
            select(Prediction.commit_hash).where(Prediction.model_name == model_name).limit(1)
        ).first()
        is not None
    )


def resolve(session: Session) -> str | None:
    """按本模块文档里的三步解析；无可用模型时返回 None（调用方决定报错还是回退）。"""
    champ = model_registry.champion()
    if champ is not None and _has_rows(session, champ.name):
        return champ.name
    names = session.execute(select(Model.model_name)).scalars().all()
    for name in sorted(names, key=model_registry.version_key, reverse=True):
        if _has_rows(session, name):
            return name
    # 兜底：`model` 表为空的历史库（正常已由 `app.db` 迁移回填，走不到这里）
    legacy = session.execute(select(Prediction.model_name).distinct()).scalars().all()
    return max(legacy, key=model_registry.version_key) if legacy else None
