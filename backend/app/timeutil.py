"""时间格式化：统一 UTC、ISO 8601、带 Z 后缀（契约三：时间字段以 _at 结尾且统一 UTC）。

此前 `iso_z` 在 commits / feedback / health / predict 四处各写一份，口径一旦漂移
（比如有一处漏掉 Z 后缀）前端就会拿到两种时间格式。集中一处，MUST NOT 再复制。
"""

from __future__ import annotations

from datetime import UTC, datetime


def iso_z(value: datetime | None) -> str | None:
    """`datetime` → `YYYY-MM-DDTHH:MM:SSZ`；`None` 原样返回（未预测 / 未标记字段）。"""
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def now_naive_utc() -> datetime:
    """当前 UTC（naive）：MySQL DATETIME 是秒级存储，落库前统一去掉 tzinfo。"""
    return datetime.now(UTC).replace(tzinfo=None)
