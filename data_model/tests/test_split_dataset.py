"""时间序切分与守恒断言的单元测试（蒋励，2026-10-13）。

对应 OpenSpec change: model-training-and-delivery（tasks.md「测试与验证」§1）
口径来源：data_model/05_split_dataset.py 模块 docstring「一条断言」，
以及 docs/model/data-pipeline.md 的「前 70% 训练、后 30% 检验，禁止随机切分」。

为什么必须测：`exp` / `nuc` / `rexp` / `sexp` 这些历史类特征与时间相关，
随机切分会把「未来」提交放进训练集，指标好看但没有意义。
切分一旦错位不会报错，只会让后面所有指标悄悄变成假的 —— 所以断言必须由测试钉住。

跑法：cd data_model && python -m pytest -q
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

_SPLIT = Path(__file__).resolve().parents[1] / "preparation" / "05_split_dataset.py"
_spec = importlib.util.spec_from_file_location("split_dataset", _SPLIT)
split = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(split)

FMT = split.TIMESTAMP_FORMAT


def _row(ts: str, hash_suffix: str = "a") -> dict:
    """造一行最小样本：只要 committed_at 与 commit_hash 两个键。"""
    return {
        "committed_at": ts,
        "commit_hash": hash_suffix * 40,
    }


def _rows_in_order(n: int) -> list[dict]:
    """造 n 行严格按时间升序、且同秒内 hash 可区分次序的样本。"""
    base = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    out = []
    for i in range(n):
        ts = base.replace(minute=i % 60, hour=i // 60).strftime(FMT)
        # hash 后缀按 i 取模，保证同秒内也有稳定次序
        suffix = "0123456789abcdef"[i % 16]
        out.append({"committed_at": ts, "commit_hash": suffix * 40})
    return out


# ── split_index：向下取整，避免把检验集切空 ─────────────────────────────────


class TestSplitIndex:
    def test_向下取整(self):
        # 10893 * 0.70 = 7625.1 -> 7625（脚本注释里登记的期望值）
        assert split.split_index(10893, 0.70) == 7625

    def test_整除时不多切(self):
        assert split.split_index(100, 0.70) == 70

    def test_极小样本不切空检验集(self):
        # 1 行 * 0.7 = 0.7 -> 0，训练集为空，交给 validate_split 报错
        assert split.split_index(1, 0.70) == 0

    def test_默认比例与模块常量一致(self):
        assert split.split_index(1000, split.DEFAULT_RATIO) == 700


# ── sort_key：同秒内用 commit_hash 兜底，保证可复现 ─────────────────────────


class TestSortKey:
    def test_同秒内按hash排序(self):
        a = _row("2026-01-01 00:00:00", "a")
        b = _row("2026-01-01 00:00:00", "b")
        assert split.sort_key(a) < split.sort_key(b)

    def test_不同时间按时间排序(self):
        early = _row("2026-01-01 00:00:00")
        late = _row("2026-06-01 00:00:00")
        assert split.sort_key(early) < split.sort_key(late)

    def test_排序稳定可复现(self):
        rows = _rows_in_order(50)
        once = sorted(rows, key=split.sort_key)
        rows.reverse()
        twice = sorted(rows, key=split.sort_key)
        assert [r["commit_hash"] for r in once] == [r["commit_hash"] for r in twice]

    def test_时间戳两侧空格被容忍(self):
        assert split.sort_key(_row("  2026-01-01 00:00:00  ")) == split.sort_key(
            _row("2026-01-01 00:00:00")
        )


# ── validate_split：守恒 + 时间序两条铁律 ───────────────────────────────────


class TestValidateSplit:
    def test_正常切分无失败项(self):
        rows = _rows_in_order(100)
        train, test = rows[:70], rows[70:]
        assert split.validate_split(train, test, 100) == []

    def test_行数不守恒被拦住(self):
        rows = _rows_in_order(100)
        train, test = rows[:70], rows[70:95]  # 丢掉 5 行
        failures = split.validate_split(train, test, 100)
        assert len(failures) == 1
        assert "行数不守恒" in failures[0]

    def test_时间序被破坏被拦住(self):
        """检验集最早不晚于训练集最晚 —— 这是本脚本存在的原因。"""
        rows = _rows_in_order(100)
        # 把一条晚提交挪进训练集，制造错位
        bad_train = rows[:70] + [rows[99]]
        bad_test = rows[70:99]
        failures = split.validate_split(bad_train, bad_test, 100)
        assert any("时间序被破坏" in f for f in failures)

    def test_一侧为空直接报错并不再继续算(self):
        failures = split.validate_split([], _rows_in_order(10), 10)
        assert failures == ["训练集或检验集为空（切分把一侧切没了）"]

    def test_同秒边界严格大于(self):
        """训练集最晚与检验集最早同一秒时，断言必须拦住（严格大于）。"""
        train = [_row("2026-01-01 00:00:00", "a")]
        test = [_row("2026-01-01 00:00:00", "b")]
        failures = split.validate_split(train, test, 2)
        assert any("时间序被破坏" in f for f in failures)

    def test_错误信息带时间戳便于定位(self):
        train = [_row("2026-03-01 12:00:00", "a")]
        test = [_row("2026-01-01 00:00:00", "b")]
        failures = split.validate_split(train, test, 2)
        assert any("2026-03-01 12:00:00" in f and "2026-01-01 00:00:00" in f for f in failures)


# ── parse_ts：格式契约 ──────────────────────────────────────────────────────


class TestParseTs:
    def test_按模块格式解析(self):
        assert split.parse_ts("2026-09-16 08:30:00") == datetime(2026, 9, 16, 8, 30, 0, tzinfo=UTC)

    def test_非法格式抛错而不是静默返回(self):
        import pytest

        with pytest.raises(ValueError):
            split.parse_ts("2026-09-16T08:30:00Z")  # ISO 带 T 与 Z，不符合契约格式

    def test_前后空格被strip(self):
        assert split.parse_ts(" 2026-09-16 08:30:00 ") == datetime(
            2026, 9, 16, 8, 30, 0, tzinfo=UTC
        )
