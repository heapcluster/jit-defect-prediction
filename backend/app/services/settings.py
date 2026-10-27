"""运行时阈值：DB 持久化 + 内存缓存，校准后立即生效、重启后仍生效。

为什么不在 `.env` 里改：`.env` 是启动配置，改完必须重启；而阈值是「运营参数」，
应当由质量看板按标签校准后热更新。DB 不可用时静默回退 `.env` 默认值，绝不让
一个配置读取失败拖垮查询接口。
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app import config
from app.db import SessionLocal
from app.errors import AppError
from app.models import RuntimeSetting
from app.timeutil import now_naive_utc

logger = logging.getLogger("backend.settings")

HIGH_KEY = "high_risk_threshold"
MID_KEY = "mid_risk_threshold"

# 进程内缓存：None 表示未加载过（首次调用或 reset_cache 后）
_cache: dict[str, float] | None = None


def _defaults() -> dict[str, float]:
    return {
        HIGH_KEY: float(config.HIGH_RISK_THRESHOLD),
        MID_KEY: float(config.MID_RISK_THRESHOLD),
    }


def reset_cache() -> None:
    """丢弃缓存（测试夹具在清表后调用，避免上一条用例的阈值串味）。"""
    global _cache
    _cache = None


def refresh() -> dict[str, float]:
    """从 DB 重新加载阈值；DB 不可用时退回 `.env` 默认值（不抛错）。"""
    global _cache
    values = _defaults()
    try:
        with SessionLocal() as session:
            for row in session.execute(select(RuntimeSetting)).scalars():
                if row.key not in values:
                    continue
                try:
                    values[row.key] = float(row.value)
                except (TypeError, ValueError):
                    logger.warning("忽略非法阈值配置：%s=%r", row.key, row.value)
    except Exception:  # noqa: BLE001 —— 配置读取失败必须降级，不能影响查询
        logger.exception("读取运行时阈值失败，回退 .env 默认值")
    _cache = values
    return dict(values)


def thresholds() -> dict[str, float]:
    return dict(_cache) if _cache is not None else refresh()


def high_threshold() -> float:
    return thresholds()[HIGH_KEY]


def mid_threshold() -> float:
    return thresholds()[MID_KEY]


def set_thresholds(high: float, mid: float) -> dict[str, float]:
    """写入并立即生效；约束 `0 <= mid <= high <= 1`，越界 → 40001。"""
    if not (0.0 <= mid <= high <= 1.0):
        raise AppError(
            40001, "参数非法：需满足 0.0 <= mid_risk_threshold <= high_risk_threshold <= 1.0"
        )
    with SessionLocal() as session:
        for key, value in ((HIGH_KEY, high), (MID_KEY, mid)):
            row = session.get(RuntimeSetting, key)
            if row is None:
                session.add(
                    RuntimeSetting(key=key, value=f"{value:.4f}", updated_at=now_naive_utc())
                )
            else:
                row.value = f"{value:.4f}"
                row.updated_at = now_naive_utc()
        session.commit()
    return refresh()
