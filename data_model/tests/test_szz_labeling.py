"""SZZ 打标判据与 diff/blame 解析的单元测试（蒋励，2026-10-13）。

对应 OpenSpec change: data-collection-and-szz-labeling（tasks.md「测试与验证」§1）
口径来源：data_model/02_szz_labeling.py 模块 docstring 的「判据（D4）」「两套方法（D3）」，
以及 docs/model/data-pipeline.md 第 7 节登记的外沿数字。

只测**纯函数**：不碰 git、不读仓库、不跑全链路。
跑法：cd data_model && python -m pytest -q

> 为什么先测这几条：判据正则（词首边界）是整条数据线的地基，
> 子串匹配会误收 dispatch/debug/prefix 词族（实测 122 条假阳性），
> 严格词表又会漏拼写错误的真修复 —— 这两类错都必须由测试钉住。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# 文件名以数字开头，不能直接 import，用 importlib 按路径加载
_SZZ = Path(__file__).resolve().parents[1] / "02_szz_labeling.py"
_spec = importlib.util.spec_from_file_location("szz_labeling", _SZZ)
szz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(szz)


# ── D4 判据：is_fix_commit ──────────────────────────────────────────────────


class TestIsFixCommit:
    """缺陷编号 且 修复语义词（词首边界），两者同时命中才算修复提交。"""

    @pytest.mark.parametrize(
        "message",
        [
            "CAMEL-8123 fix NPE in broker",
            "camel-1234: Fixed the dispatch regression",
            "[CAMEL-9999] PATCH for memory leak",
            "CAMEL-1 bugfix: handle null session",
            "CAMEL-42 fixe typo in config",  # 拼写错误的真修复，必须收
            "CAMEL-42 fixinng the patchh logic",  # 词首边界保留词形变化
        ],
    )
    def test_命中编号与修复词时判为修复提交(self, message):
        assert szz.is_fix_commit(message) is True

    @pytest.mark.parametrize(
        "message",
        [
            "CAMEL-8123 add new transport",  # 有编号无修复词
            "CAMEL-8123 refactor: extract helper",  # 有编号无修复词
            "fix the flaky test in module A",  # 有修复词无编号
            "CAMEL-8123 documentation update",  # 有编号无修复词
            "",  # 空消息
        ],
    )
    def test_缺任一类不判为修复提交(self, message):
        assert szz.is_fix_commit(message) is False

    @pytest.mark.parametrize(
        "message",
        [
            # 这些词天然含 fix / bug / patch 子串，但词不在词首 —— 子串匹配会误收
            "CAMEL-100 improve dispatch throughput",
            "CAMEL-101 add debug logging for prefix resolution",
            "CAMEL-103 support prefix-based routing",
            "CAMEL-104 rework the dispatcher internals",
        ],
    )
    def test_同词内嵌不得命中词首边界(self, message):
        """dispatch / debug / prefix 这类功能词误收会污染候选池（词首边界用以排除）。"""
        assert szz.is_fix_commit(message) is False

    def test_词首出现即算修复词(self):
        """同一条消息里 dispatch 与 fix 并存时，fix 在词首，应判为修复提交。"""
        assert szz.is_fix_commit("CAMEL-102 fix the message dispatch handling") is True

    def test_大小写不敏感(self):
        assert szz.is_fix_commit("camel-8123 FIX npe") is True
        assert szz.is_fix_commit("CAMEL-8123 Fix npe") is True
        assert szz.is_fix_commit("CAMEL-8123 PATCH npe") is True

    def test_编号必须带数字(self):
        assert szz.is_fix_commit("CAMEL- fix something") is False


# ── diff 解析：parse_old_ranges ──────────────────────────────────────────────


class TestParseOldRanges:
    """从 `git diff -U0` 取出父提交侧被改动掉的行区间。"""

    DIFF = """diff --git a/src/main/java/A.java b/src/main/java/A.java
--- a/src/main/java/A.java
+++ b/src/main/java/A.java
@@ -10,3 +10,3 @@ class A
-    old line 1
-    old line 2
+    new line 1
@@ -40 +40 @@ class A
-    another old line
+    another new line
diff --git a/src/main/java/B.java b/src/main/java/B.java
--- a/src/main/java/B.java
+++ b/src/main/java/B.java
@@ -5,0 +6,2 @@ class B
+pure addition
+another addition
"""

    def test_解析出旧侧行区间(self):
        got = szz.parse_old_ranges(self.DIFF)
        assert got == {"src/main/java/A.java": [(10, 3), (40, 1)]}

    def test_纯新增行数为零不收录(self):
        """count=0 表示父提交侧没有对应行，无从 blame。"""
        got = szz.parse_old_ranges(self.DIFF)
        assert "src/main/java/B.java" not in got

    def test_新增文件不收录(self):
        diff = """diff --git a/src/New.java b/src/New.java
--- /dev/null
+++ b/src/New.java
@@ -0,0 +1,2 @@
+line1
+line2
"""
        assert szz.parse_old_ranges(diff) == {}

    def test_多文件各自归集(self):
        diff = """diff --git a/a.java b/a.java
--- a/a.java
+++ b/a.java
@@ -1,2 +1,2 @@
-x
+y
diff --git a/b.java b/b.java
--- a/b.java
+++ b/b.java
@@ -7,1 +7,1 @@
-p
+q
"""
        assert szz.parse_old_ranges(diff) == {
            "a.java": [(1, 2)],
            "b.java": [(7, 1)],
        }

    def test_空_diff返回空(self):
        assert szz.parse_old_ranges("") == {}

    def test_无hunk头的diff返回空(self):
        diff = """diff --git a/x.java b/x.java
--- a/x.java
+++ b/x.java
"""
        assert szz.parse_old_ranges(diff) == {}


# ── 区间合并：merge_ranges ───────────────────────────────────────────────────


class TestMergeRanges:
    """相邻/接近的区间并起来，减少 blame 进程启动次数。"""

    def test_相邻区间合并(self):
        assert szz.merge_ranges([(10, 2), (12, 2)], gap=20) == [(10, 13)]

    def test_间隔小于阈值合并(self):
        # 10-11 与 25-26 之间隔 13 行 < 20，应合并
        assert szz.merge_ranges([(10, 2), (25, 2)], gap=20) == [(10, 26)]

    def test_间隔不小于阈值不合并(self):
        # 10-11 与 40-41 之间隔 28 行 >= 20，不合并
        assert szz.merge_ranges([(10, 2), (40, 2)], gap=20) == [(10, 11), (40, 41)]

    def test_乱序输入也能正确合并(self):
        assert szz.merge_ranges([(40, 2), (10, 2)], gap=20) == [(10, 11), (40, 41)]

    def test_零长区间被过滤(self):
        assert szz.merge_ranges([(10, 0), (12, 2)], gap=20) == [(12, 13)]

    def test_空输入(self):
        assert szz.merge_ranges([], gap=20) == []

    def test_默认阈值与模块常量一致(self):
        """不传 gap 时用模块级 MERGE_GAP，改常量必须同步改测试预期。

        合并条件是 `start - 上段止行 - 1 <= gap`：上段止行为 1 时，
        start=22（间隔 20）仍合并，start=23（间隔 21）才不合并。
        """
        assert szz.merge_ranges([(1, 1), (szz.MERGE_GAP + 2, 1)]) == [(1, szz.MERGE_GAP + 2)]
        assert szz.merge_ranges([(1, 1), (szz.MERGE_GAP + 3, 1)]) == [
            (1, 1), (szz.MERGE_GAP + 3, szz.MERGE_GAP + 3)]


# ── 缓存键：blame_cache_key ──────────────────────────────────────────────────


class TestBlameCacheKey:
    """同一个 (rev, path) 在不同修复提交下要 blame 的行不一样，键必须带区间。"""

    def test_键包含区间(self):
        k = szz.blame_cache_key("rev1", "a.java", ((10, 2),))
        assert k == ("rev1", "a.java", ((10, 2),))

    def test_同rev同path不同区间键不同(self):
        a = szz.blame_cache_key("rev1", "a.java", ((10, 2),))
        b = szz.blame_cache_key("rev1", "a.java", ((10, 3),))
        assert a != b

    def test_同区间不同rev键不同(self):
        a = szz.blame_cache_key("rev1", "a.java", ((10, 2),))
        b = szz.blame_cache_key("rev2", "a.java", ((10, 2),))
        assert a != b
