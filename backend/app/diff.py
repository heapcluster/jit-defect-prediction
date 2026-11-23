"""统一 diff（-U0）解析：提取每个文件的新增行（number + content），供行级缺陷定位。

输入来自 `git show <hash> --format= --unified=0 --no-renames`。只取「新增行」——
JIT 缺陷定位的常用近似：新增行最可能是引入缺陷的位置。二进制 / 重命名差异不解析。

本模块是纯函数，不碰 git 子进程，可脱离仓库直接单测。
"""

from __future__ import annotations


def parse_unified_diff(diff_text: str) -> list[dict]:
    """把 -U0 统一 diff 解析成文件级新增行 + hunk 明细。

    返回 [{"path", "added_lines", "deleted_count", "hunks"}]。
    无新增行的文件（纯删除 / 二进制）不收录；元数据行（index / --- / new file mode /
    ``\\ No newline``）跳过，只有空格开头的上下文行推进新行号。
    hunk 明细用于行级定位：先按 hunk 打分，再只展示高分 hunk 里的新增行。
    """
    files: list[dict] = []
    cur: dict | None = None
    hunk: dict | None = None
    new_line = 0

    for raw in diff_text.split('\n'):
        raw = raw.removesuffix('\r')
        if raw.startswith("diff --git "):
            cur = {"path": "", "added_lines": [], "deleted_count": 0, "hunks": []}
            files.append(cur)
            hunk = None
            new_line = 0
            continue
        if cur is None:
            continue
        if raw.startswith("+++ b/"):
            cur["path"] = raw[6:]
            continue
        if raw.startswith("--- ") or raw.startswith("+++ "):
            continue
        if raw.startswith("@@ "):
            # @@ -old_start,old_count +new_start,new_count @@
            plus = raw.split("+", 1)[1]
            new_line = int(plus.split(" ")[0].split(",")[0])
            hunk = {"added_lines": [], "deleted_count": 0}
            cur["hunks"].append(hunk)
            continue
        if raw.startswith("+"):
            line = {"number": new_line, "content": raw[1:]}
            cur["added_lines"].append(line)
            if hunk is not None:
                hunk["added_lines"].append(line)
            new_line += 1
        elif raw.startswith("-"):
            cur["deleted_count"] += 1
            if hunk is not None:
                hunk["deleted_count"] += 1
        elif raw.startswith(" "):
            # 上下文行：-U0 下极少出现，仍推进新行号
            new_line += 1
        # 其余（index / new file mode / \ No newline）跳过

    return [f for f in files if f["path"] and f["added_lines"]]
