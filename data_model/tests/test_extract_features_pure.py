# [AI生成] 本文件用例由 AI 编写，核心断言经人工复核。
"""03_extract_features.py 纯函数的三例单元测试。

`log_v1` / `subsystem_of` / `directory_of` / `to_epoch` / `entropy_series` 均可
脱离 git 子进程直接断言，此前零覆盖。`log_v1` 在 0 附近的不连续是契约本身的
缺陷（模块 docstring 第 3 条），测试只锁「现状」不擅自修正。
"""

from __future__ import annotations

import importlib.util
import math
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "preparation" / "03_extract_features.py"
_spec = importlib.util.spec_from_file_location("extract_features_pure", SCRIPT)
assert _spec and _spec.loader
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)


def _commit(ts: int, files: list[tuple[int, int, str]]) -> dict:
    return {"ts": ts, "email": "a@b.c", "name": "A", "files": files}


# ── subsystem_of：Kamei 的 subsystem = 路径根目录名 ─────────────────────────


class TestSubsystemOf:
    def test_多级路径取根目录(self):
        assert extract.subsystem_of("camel-core/src/Foo.java") == "camel-core"

    def test_根目录下的文件单列一组(self):
        assert extract.subsystem_of("pom.xml") == "(root)"

    def test_空串按无目录处理(self):
        assert extract.subsystem_of("") == "(root)"


# ── directory_of：去文件名后的目录 ──────────────────────────────────────────


class TestDirectoryOf:
    def test_多级路径保留目录前缀(self):
        assert extract.directory_of("a/b/c.txt") == "a/b"

    def test_单级文件无目录(self):
        assert extract.directory_of("Foo.java") == "(root)"

    def test_空串无目录(self):
        assert extract.directory_of("") == "(root)"


# ── log_v1：契约第四节对数变换的三条补充 ────────────────────────────────────


class TestLogV1:
    def test_正数取自然对数(self):
        assert extract.log_v1(math.e) == pytest.approx(1.0)
        assert extract.log_v1(1.0) == 0.0

    def test_零按_log1p_口径记零(self):
        assert extract.log_v1(0.0) == 0.0

    def test_非正数不抛错记零(self):
        # 契约缺陷：0 附近不连续（ln(1+0)=0 但 ln 分支在 0 处跳变），只锁现状
        assert extract.log_v1(-5.0) == 0.0


# ── to_epoch：契约时间格式 → UTC 秒 ─────────────────────────────────────────


class TestToEpoch:
    def test_按模块格式解析(self):
        assert extract.to_epoch("2026-01-01 00:00:00") == int(
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC).timestamp()
        )

    def test_非法格式抛错而不是静默(self):
        with pytest.raises(ValueError):
            extract.to_epoch("2026-01-01T00:00:00Z")


# ── entropy_series：两周窗口改动信息熵 ───────────────────────────────────────


class TestEntropySeries:
    def test_单文件改动熵为零(self):
        commits = {"h1": _commit(1_000_000, [(1, 0, "a.txt")])}
        assert extract.entropy_series(commits, [2_000_000]) == [0.0]

    def test_两文件各改一次熵为一(self):
        commits = {"h1": _commit(1_000_000, [(1, 0, "a.txt"), (1, 0, "b.txt")])}
        assert extract.entropy_series(commits, [2_000_000]) == [pytest.approx(1.0)]

    def test_空历史熵为零(self):
        assert extract.entropy_series({}, [2_000_000]) == [0.0]

    def test_窗口外的改动不计入(self):
        # 窗口 (T-14天, T]：恰好早 14 天的提交被排除（严格大于下界）
        boundary = 2_000_000 - extract.ENTROPY_WINDOW_SECONDS
        commits = {"h1": _commit(boundary, [(1, 0, "a.txt")])}
        assert extract.entropy_series(commits, [2_000_000]) == [0.0]
