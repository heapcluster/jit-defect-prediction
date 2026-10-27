"""时间工具：统一 UTC、ISO 8601、带 Z 后缀；以及查询时间参数的解析口径。

契约三要求时间字段统一 UTC 且以 `_at` 结尾；`iso_z` 是唯一格式化入口。
`parse_time_param` 承载 §1「时间范围语义」（闭区间 + end 侧纯日期串含结束日全天），
此前只在 `api/commits.py` 内部，`trends` / `quality` 需要同一口径，故上移到这里。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.errors import AppError


def iso_z(value: datetime | None) -> str | None:
    """`datetime` → `YYYY-MM-DDTHH:MM:SSZ`；`None` 原样返回（未预测 / 未标记字段）。"""
    if value is None:
        return None
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


def now_naive_utc() -> datetime:
    """当前 UTC（naive）：MySQL DATETIME 是秒级存储，落库前统一去掉 tzinfo。"""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_time_param(value: str, param: str, role: str = "start") -> datetime:
    """解析 ISO 8601 时间查询参数（契约三 §1 时间范围语义）。"""
    # 紧凑基本格式一律拒（含 Z/偏移后缀变体，#62 复审 1+3）：头 8 位数字后接 T 或
    # 结束即基本格式；fromisoformat 收但它绕过纯日期串判定，end 会静默停 00:00
    if re.fullmatch(r"\d{8}(T\S*)?", value):
        raise AppError(
            40001, f"参数非法：{param} 不接受紧凑基本格式，请用 YYYY-MM-DD 或带分隔符的 ISO 8601"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AppError(40001, f"参数非法：{param} 需为 ISO 8601 时间") from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    # 契约三 1.5 区间语义（#61）：闭区间；end 侧纯日期串含结束日全天，
    # start 侧纯日期串仍是当天 00:00:00（不能一刀切）；带时间分量按原样
    if role == "end" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
    return parsed
