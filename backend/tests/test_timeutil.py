"""时间工具的三例单元测试（app/timeutil.py）。

`parse_time_param` 承载契约三 §1 的时间范围语义（闭区间、end 侧纯日期含结束日
全天、紧凑基本格式一律拒），此前只在 API 层间接覆盖，缺函数级三例。
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.errors import AppError
from app.timeutil import iso_z, now_naive_utc, parse_time_param


def test_iso_z_formats_naive_datetime_with_z():
    assert iso_z(datetime(2026, 8, 1, 8, 30, 0)) == "2026-08-01T08:30:00Z"


def test_iso_z_none_passes_through():
    """边界：None 原样返回（未预测 / 未标记字段）。"""
    assert iso_z(None) is None


def test_iso_z_aware_datetime_outputs_utc_z():
    """边界：tz-aware 一律按 UTC 输出，不带 +00:00 偏移。"""
    assert iso_z(datetime(2026, 8, 1, 8, 30, 0, tzinfo=UTC)) == "2026-08-01T08:30:00Z"


def test_now_naive_utc_has_no_tzinfo():
    """落库前统一去掉 tzinfo（MySQL DATETIME 秒级存储）。"""
    assert now_naive_utc().tzinfo is None


def test_parse_time_param_iso_with_z():
    parsed = parse_time_param("2026-08-01T08:30:00Z", "start_time")
    assert parsed == datetime(2026, 8, 1, 8, 30, 0)
    assert parsed.tzinfo is None


def test_parse_time_param_offset_converts_to_utc():
    parsed = parse_time_param("2026-08-01T08:30:00+08:00", "start_time")
    assert parsed == datetime(2026, 8, 1, 0, 30, 0)


def test_parse_time_param_end_pure_date_includes_whole_day():
    """边界：end 侧纯日期串含结束日全天（闭区间，契约三 1.5）。"""
    parsed = parse_time_param("2026-08-01", "end_time", role="end")
    assert parsed == datetime(2026, 8, 1, 23, 59, 59, 999999)


def test_parse_time_param_start_pure_date_stays_midnight():
    """边界：start 侧纯日期串仍是当天 00:00:00，不能一刀切也推到 23:59:59。"""
    parsed = parse_time_param("2026-08-01", "start_time", role="start")
    assert parsed == datetime(2026, 8, 1, 0, 0, 0)


@pytest.mark.parametrize(
    "bad",
    ["20260801", "20260801T083000Z", "20260801T083000+08:00"],
)
def test_parse_time_param_rejects_compact_basic_format(bad):
    """异常：紧凑基本格式一律拒（fromisoformat 收但它绕过纯日期串判定）。"""
    with pytest.raises(AppError) as exc:
        parse_time_param(bad, "start_time")
    assert exc.value.code == 40001


@pytest.mark.parametrize("bad", ["not-a-time", "2026-13-45", ""])
def test_parse_time_param_rejects_invalid_iso(bad):
    with pytest.raises(AppError) as exc:
        parse_time_param(bad, "start_time")
    assert exc.value.code == 40001
