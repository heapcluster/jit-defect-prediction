# [AI生成] 本文件用例由 AI 编写，核心断言经人工复核。
"""app/diff.py 统一 diff 解析的三例单元测试（行级缺陷定位的解析底座）。"""

from __future__ import annotations

from app.diff import parse_unified_diff

DIFF = """diff --git a/a.txt b/a.txt
index 111..222 100644
--- a/a.txt
+++ b/a.txt
@@ -1 +1,3 @@
-old
+one
+two
diff --git a/b.txt b/b.txt
new file mode 100644
--- /dev/null
+++ b/b.txt
@@ -0,0 +1 @@
+hello
"""


def test_parse_extracts_added_lines_with_numbers():
    files = parse_unified_diff(DIFF)
    assert [f["path"] for f in files] == ["a.txt", "b.txt"]
    assert files[0]["added_lines"] == [
        {"number": 1, "content": "one"},
        {"number": 2, "content": "two"},
    ]
    assert files[1]["added_lines"] == [{"number": 1, "content": "hello"}]


def test_parse_skips_pure_deletion_and_binary():
    """纯删除 / 二进制（无新增行）的文件不收录。"""
    deletion = "diff --git a/c.txt b/c.txt\n--- a/c.txt\n+++ b/c.txt\n@@ -1,3 +1,0 @@\n-a\n-b\n-c\n"
    assert parse_unified_diff(deletion) == []
    binary = "diff --git a/x.bin b/x.bin\nindex abc..def 100644\nBinary files a/x.bin and b/x.bin differ\n"
    assert parse_unified_diff(binary) == []


def test_parse_metadata_lines_do_not_advance_line_numbers():
    """index / --- / new file mode 等元数据行不得污染新增行号。"""
    diff = "diff --git a/d.txt b/d.txt\nindex 1..2 100644\n--- a/d.txt\n+++ b/d.txt\n@@ -2 +2,2 @@\n-x\n+y\n"
    files = parse_unified_diff(diff)
    assert files[0]["added_lines"] == [{"number": 2, "content": "y"}]


def test_parse_empty_text():
    assert parse_unified_diff("") == []
