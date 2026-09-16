"""02 SZZ 打标：找出修缺陷提交，回溯到引入缺陷的那次提交。

对应 OpenSpec change: data-collection-and-szz-labeling
规格: openspec/changes/data-collection-and-szz-labeling/specs/szz-labeling/spec.md
决策: openspec/changes/data-collection-and-szz-labeling/design.md（D3/D4/D5/D6）

字段口径以 docs/contracts/data-fields.md 表二 `commit_label` 为准，不在此处发明列名。

── 判据（D4）────────────────────────────────────────────────────────────
一条提交被判为「修缺陷提交」需要同时命中两类：
  ① 含缺陷编号 `AMQ-<数字>`
  ② 含修复语义词 fix / bug / patch，且该词出现在**词首边界**（`\b`）
只用编号会把 54.7% 的提交拉进候选池（含新功能与文档），故必须加 ②。

② 为什么卡词首边界、而不是子串：ActiveMQ 的词汇里 `dispatch` / `debug` / `prefix`
天然含 `patch` / `bug` / `fix` 子串，而「消息分发」正是本仓库的核心功能词。实测在固定
版本上，子串匹配会多收 122 条这样的提交（dispatch 词族 83 条、debug 17 条、prefix 9 条，
其余为同类），**没有一条是真修复**；反过来收窄成「严格词表」又会漏掉 `fixe` /
`fixinng` / `patchh` 这类拼写错误的**真**修复。故取两者中间的词首边界：保留词形变化
（fixes / fixed / patching / bugfix），排除同词内嵌（dispatch / debug / prefix）。
这条界定的理由在规格上必须落到文字，故与 docs/data-pipeline.md 第 7 节同步维护。

命中外沿数字登记在 docs/data-pipeline.md 第 7 节「打标判据（2026-09-16 实测）」。

── 两套方法（D3）────────────────────────────────────────────────────────
同一固定版本各打一次标，靠 label_method 区分，互不覆盖：

  szz       行级回溯（标准 SZZ）：对修复提交「删除/修改掉的每一个代码行」，
            在父提交上做 git blame，blame 到谁就记谁。
            精确，但要为每个文件跑一次 blame，调用量 = 修复提交数 × 改动文件数。

  szz_lite  文件级回溯（自研简化版）：不看具体行，只问「这个被改的文件在父提交时
            最后一次被谁改动」，把那次提交当引入方候选。
            只需 git log -1，快一个量级，代价是粒度粗 —— 文件里只有一行过时，
            整个文件的最近改动者也会被牵连进来。

两套的差异必须量化并出示（规格 szz-labeling 「两套方法结果不一致」），不静默取其一。

> 关于方法名：契约表二把 `szz` 标注为「PySZZ」。经实测 **PySZZ 不在 PyPI**
> （https://pypi.org/pypi/pyszz/json 返回 404），其官方仓库依赖 gitlog 数据格式，
> 属研究专用工具，Sprint 0 内跑通不现实。故按 docs/data-pipeline.md 第 7 节的兜底策略
> 切换自研实现：`szz` 由本脚本实现标准行级 SZZ 算法，`label_method` 取值仍只在契约
> 定义的集合内。此偏离已在统计表中注明，需走契约变更流程把「（PySZZ）」这个括注改掉。

── 排除口径（D5）────────────────────────────────────────────────────────
回溯未命中的修复提交 **既不入样本集也不记 0**，只在统计中单列数量。
把「找不到引入方」记成 0 会把本该是 1 的样本污染成负样本，既压低正样本比例又引入噪声。

── 复现性 ───────────────────────────────────────────────────────────────
同版本重复执行，标签列（commit_hash / is_bug_inducing / bug_fix_hash）逐行一致。
`labeled_at` 是元数据，重跑取当前时间；要逐字节一致请用 --labeled-at 钉住。
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_REPO = BASE / "data" / "activemq"
DEFAULT_COMMITS = BASE / "data" / "commits.csv"
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"

# 与 docs/contracts/data-fields.md 表二 `commit_label` 逐字对齐（id 由数据库自增，CSV 不落）
LABEL_FIELDS = ["commit_hash", "is_bug_inducing", "label_method", "bug_fix_hash", "labeled_at"]

# ── 判据（D4）──────────────────────────────────────────────────────────────
BUG_ID_RE = re.compile(r"AMQ-\d+", re.IGNORECASE)
# 修复语义词：**卡词首边界**。子串匹配会误收 dispatch/debug/prefix（实测 122 条，全为假阳性），
# 严格词表又会漏掉 fixe/fixinng/patchh 这类拼写错误的真修复 —— 词首边界是二者的中点。
FIX_WORD_RE = re.compile(r"\b(fix|bug|patch)", re.IGNORECASE)

# docs/data-pipeline.md 第 7 节登记的外沿数字，用于自检判据实现是否与文档一致。
# 这三个数是在**完整固定版本**（11,050 条非合并提交）上算出来的，故只在全量运行时可比。
# 2026-09-16 由旧登记值 6041 / 2538 / 1865 改为实测可复现值：旧值无法从提交清单复现
# （1865 用任何自然正则都算不出），且 2538 那一项用的是子串口径、含 122 条假阳性。
EXPECTED_OUTER = {"has_id": 6042, "id_and_fix_word": 2417, "id_and_fix_form": 1939}
FULL_COMMIT_COUNT = 11050  # docs/data-pipeline.md 第 2 节登记的完整版本非合并提交数
FIX_FORM_RE = re.compile(r"\bfix", re.IGNORECASE)  # 与 FIX_WORD_RE 同一套词首语义

# ── diff / blame 解析 ─────────────────────────────────────────────────────
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
BLAME_HEADER_RE = re.compile(r"^([0-9a-f]{40}) (\d+) (\d+) (\d+)$")

# 相邻行区间合并阈值：间隔小于该值就并成一次 blame 调用，减少进程启动开销
MERGE_GAP = 20

# 正样本比例异常区间（规格 szz-labeling「正样本比例异常时先自查」）
ABNORMAL_LOW, ABNORMAL_HIGH = 0.40, 0.60

METHODS = ("szz", "szz_lite")
_GIT = shutil.which("git") or shutil.which("git.exe")


# ══ 通用 ═══════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SZZ 打标：识别修缺陷提交并回溯引入缺陷的提交",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--repo", type=Path, default=DEFAULT_REPO, help=f"仓库副本路径（默认 {DEFAULT_REPO}）")
    p.add_argument("--commits", type=Path, default=DEFAULT_COMMITS, help=f"01 产出的提交清单（默认 {DEFAULT_COMMITS}）")
    p.add_argument(
        "--method",
        choices=(*METHODS, "both"),
        default="both",
        help="打标方法（默认 both：两套都跑，产出的差异用于对照）",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="只跑前 N 个修复提交（烟雾测试用，0=不限）。跑通链路后再去掉",
    )
    p.add_argument(
        "--labeled-at",
        default=None,
        help="钉住打标时间（ISO，如 2026-09-16T12:00:00）。不传=当前 UTC。用于验证逐字节复现",
    )
    p.add_argument(
        "--tag",
        default="",
        help="输出文件名后缀，用于把窗口子集与全量的标签分开放（例：--tag window2023 → commit_labels_window2023_szz.csv）",
    )
    return p.parse_args()


def _git(repo_dir: Path, *args: str) -> str:
    """执行一条只读 git 命令，返回 stdout 文本。

    用 subprocess 而不是 GitPython 的 blame 封装：--line-porcelain 会带回源码原文，
    仓库里若有非 UTF-8 字节，GitPython 的解码会直接抛异常；这里用 errors=replace 兜住。
    """
    proc = subprocess.run(
        [_GIT, "-C", str(repo_dir), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()[:300]
        raise RuntimeError(f"git {' '.join(args)} 失败（exit {proc.returncode}）：{detail}")
    return proc.stdout.decode("utf-8", "replace")


def load_commits(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"找不到提交清单：{path}（先跑 01_extract_commits.py）")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (r["committed_at"], r["commit_hash"]))
    return rows


def is_fix_commit(message: str) -> bool:
    """D4 判据：缺陷编号 且 修复语义（词首边界），两者同时命中。"""
    if not BUG_ID_RE.search(message):
        return False
    return bool(FIX_WORD_RE.search(message))


# ══ diff 解析 ═════════════════════════════════════════════════════════════


def parse_old_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
    """从 `git diff -U0` 输出里取出「父提交侧被改动掉的行区间」。

    返回 {旧侧路径: [(起始行, 行数), ...]}。只保留行数 > 0 的区间：
    行数为 0 表示该处是纯新增，在父提交里没有对应行，无从 blame。
    """
    files: dict[str, list[tuple[int, int]]] = {}
    cur: str | None = None
    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            cur = None
        elif line.startswith("--- "):
            raw = line[4:].split("\t")[0].strip()
            # /dev/null 表示这是新增文件，旧侧没有内容；带引号的路径（含空格/非 ASCII）不解析
            cur = raw[2:] if raw.startswith("a/") else None
            if cur is not None:
                files.setdefault(cur, [])
        elif line.startswith("@@") and cur is not None:
            m = HUNK_RE.match(line)
            if not m:
                continue
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) is not None else 1
            if count > 0:
                files[cur].append((start, count))
    return {p: v for p, v in files.items() if v}


def merge_ranges(ranges: list[tuple[int, int]], gap: int = MERGE_GAP) -> list[tuple[int, int]]:
    """把相邻/接近的行区间并起来，返回 [(起, 止), ...]，减少 blame 调用次数。"""
    out: list[list[int]] = []
    for start, count in sorted(r for r in ranges if r[1] > 0):
        end = start + count - 1
        if out and start - out[-1][1] - 1 <= gap:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return [(a, b) for a, b in out]


def blame_lines(repo_dir: Path, rev: str, path: str, ranges: list[tuple[int, int]]) -> dict[int, str]:
    """在 rev 上对 path 的指定行区间做 blame，返回 {行号: 提交哈希}。"""
    result: dict[int, str] = {}
    for start, end in merge_ranges(ranges):
        out = _git(repo_dir, "blame", "--line-porcelain", f"-L{start},{end}", rev, "--", path)
        cur_sha: str | None = None
        cur_line: int | None = None
        for line in out.split("\n"):
            m = BLAME_HEADER_RE.match(line)
            if m:
                cur_sha, cur_line = m.group(1), int(m.group(3))
            elif line.startswith("\t") and cur_sha is not None and cur_line is not None:
                result[cur_line] = cur_sha
    return result


def blame_cache_key(rev: str, path: str, ranges: tuple[tuple[int, int], ...] = ()) -> tuple:
    """缓存键带上区间：同一个 (rev, path) 在不同修复提交下要 blame 的行不一样，键不能省区间。"""
    return rev, path, ranges


# ══ 打标 ══════════════════════════════════════════════════════════════════


def backtrack_szz(
    repo_dir: Path,
    fix_hash: str,
    parent_hash: str,
    diff_text: str,
    blame_memo: dict[tuple[str, str], dict[int, str]],
) -> set[str]:
    """行级回溯：blame 父提交上「被这次修复改动掉的那些行」。"""
    candidates: set[str] = set()
    for path, ranges in parse_old_ranges(diff_text).items():
        merged = tuple(merge_ranges(ranges))
        key = blame_cache_key(parent_hash, path, merged)
        if key not in blame_memo:
            blame_memo[key] = blame_lines(repo_dir, parent_hash, path, ranges)
        covered = blame_memo[key]
        for ln in _lines_of(ranges):
            sha = covered.get(ln)
            if sha:
                candidates.add(sha)
    return candidates


def _lines_of(ranges: list[tuple[int, int]]):
    for start, count in ranges:
        for ln in range(start, start + count):
            yield ln


def backtrack_szz_lite(
    repo_dir: Path,
    fix_hash: str,
    parent_hash: str,
    diff_text: str,
    touch_memo: dict[tuple[str, str], str],
) -> set[str]:
    """文件级回溯：把「被改文件在父提交时的最后一次改动」当引入方候选。"""
    candidates: set[str] = set()
    for path in parse_old_ranges(diff_text).items():
        p = path[0]
        key = blame_cache_key(parent_hash, p)
        if key not in touch_memo:
            out = _git(repo_dir, "log", "-1", "--format=%H", parent_hash, "--", p).strip()
            touch_memo[key] = out.split("\n")[0] if out else ""
        sha = touch_memo[key]
        if sha:
            candidates.add(sha)
    return candidates


def run_method(
    method: str,
    repo_dir: Path,
    commits: list[dict[str, str]],
    fix_rows: list[dict[str, str]],
    limit: int,
) -> dict:
    """跑一套打标方法，返回结果与统计。"""
    sample_hashes = {r["commit_hash"] for r in commits}
    blame_memo: dict = {}
    touch_memo: dict = {}

    labels: dict[str, str] = {}       # 引入方提交哈希 -> 触发它的修复提交哈希
    unresolved: set[str] = set()      # 回溯未命中的修复提交（不入样本）
    out_of_window = 0                 # 其中「引入方落在窗口/版本之外」的条数
    no_parent = 0                     # 其中「根提交无父提交」的条数
    diff_failed = 0

    todo = fix_rows[:limit] if limit > 0 else fix_rows
    t0 = time.time()
    for i, row in enumerate(todo, 1):
        fix_hash = row["commit_hash"]
        parent_hash = row["parent_hash"]
        if not parent_hash:
            no_parent += 1
            unresolved.add(fix_hash)
            continue
        try:
            diff_text = _git(repo_dir, "diff", "-U0", "--no-color", "--no-renames", parent_hash, fix_hash)
        except RuntimeError:
            # 单个提交的 diff 取不到不该拖停整条流程，计入统计继续
            diff_failed += 1
            unresolved.add(fix_hash)
            continue

        if method == "szz":
            raw = backtrack_szz(repo_dir, fix_hash, parent_hash, diff_text, blame_memo)
        else:
            raw = backtrack_szz_lite(repo_dir, fix_hash, parent_hash, diff_text, touch_memo)

        raw.discard(fix_hash)  # 自己不能是自己的引入方
        in_sample = sorted(c for c in raw if c in sample_hashes)
        if not in_sample:
            unresolved.add(fix_hash)
            if raw:
                out_of_window += 1
            continue
        for c in in_sample:
            labels.setdefault(c, fix_hash)  # 修复提交按时间序，先到先得 ⇒ 记最早的那次修复

        if i % 100 == 0:
            print(f"    [{method}] {i}/{len(todo)} 条修复提交，已用 {time.time() - t0:.0f}s", flush=True)

    elapsed = time.time() - t0

    # D5：回溯未命中的修复提交排除出样本集（除非它本身被别的修复提交指控为引入方）
    excluded = {h for h in unresolved if h not in labels}
    sample = [r for r in commits if r["commit_hash"] not in excluded]
    pos = len(labels)
    neg = len(sample) - pos
    ratio = pos / len(sample) if sample else 0.0

    if pos == 0:
        raise RuntimeError(f"[{method}] 正样本数为 0，打标逻辑有问题，终止（继续跑只会产出空训练集）")

    return {
        "method": method,
        "labels": labels,
        "sample": sample,
        "excluded": excluded,
        "fix_total": len(todo),
        "unresolved": len(unresolved),
        "out_of_window": out_of_window,
        "no_parent": no_parent,
        "diff_failed": diff_failed,
        "pos": pos,
        "neg": neg,
        "ratio": ratio,
        "elapsed": elapsed,
        "blame_calls": len(blame_memo) + len(touch_memo),
    }


def write_labels(path: Path, method: str, result: dict, labeled_at: str) -> None:
    rows = []
    for r in result["sample"]:
        h = r["commit_hash"]
        is_bug = 1 if h in result["labels"] else 0
        rows.append(
            {
                "commit_hash": h,
                "is_bug_inducing": is_bug,
                "label_method": method,
                "bug_fix_hash": result["labels"].get(h, ""),
                "labeled_at": labeled_at,
            }
        )
    rows.sort(key=lambda r: r["commit_hash"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)


# ══ 报告 ══════════════════════════════════════════════════════════════════


def judge_selfcheck(commits: list[dict[str, str]]) -> tuple[dict[str, int], bool | None, bool]:
    """按登记在 docs/data-pipeline.md 第 7 节的三条判据复算外沿，核对是否与文档一致。

    文档登记的是**完整固定版本**上的外沿。子集运行（01 带 --since）时提交数不足，
    这组数字天然对不上 —— 那种情况下返回 comparable=False，报告里标「不可比」而不是
    标「❌」，否则每次跑子集都会报一个假警报。
    """
    got = {
        "has_id": sum(1 for r in commits if BUG_ID_RE.search(r["message"])),
        "id_and_fix_word": sum(1 for r in commits if is_fix_commit(r["message"])),
        "id_and_fix_form": sum(
            1 for r in commits if BUG_ID_RE.search(r["message"]) and FIX_FORM_RE.search(r["message"])
        ),
    }
    comparable = len(commits) >= FULL_COMMIT_COUNT
    ok = all(got[k] == v for k, v in EXPECTED_OUTER.items()) if comparable else None
    return got, ok, comparable


def write_report(
    path: Path,
    commits: list[dict[str, str]],
    fix_rows: list[dict[str, str]],
    results: list[dict],
    selfcheck: tuple[dict[str, int], bool | None, bool],
    limit: int,
    tag: str = "",
) -> None:
    got, ok, comparable = selfcheck
    L: list[str] = []
    L.append("# SZZ 打标统计（02_szz_labeling.py 产出）\n")
    L.append("> 本文件可入库，是链路可复现与标签可信度的证据（见 `docs/data-pipeline.md` 第 3、6 节）\n")
    L.append("## 输入与判据\n")
    L.append("| 项 | 值 |\n|---|---|")
    L.append(f"| 样本提交数（01 产出） | {len(commits)} |")
    L.append(f"| 时间跨度 | {commits[0]['committed_at']} ~ {commits[-1]['committed_at']} |")
    L.append(f"| 识别为修缺陷提交（判据 D4 双命中） | {len(fix_rows)} |")
    if tag:
        L.append(f"| 运行标记 | `{tag}` |")
    if limit:
        L.append(f"| **本次仅处理前 N 条修复提交（烟雾测试）** | **{limit}** |")
    L.append(
        "\n判据 D4 = 含缺陷编号 `AMQ-<数字>` **且** 含修复语义 `fix`/`bug`/`patch`"
        "（词首边界 `\\b`，故 `dispatch`/`debug`/`prefix` 不算命中）。\n"
    )
    L.append("### 判据自检（与 docs/data-pipeline.md 第 7 节登记的外沿对照）\n")
    if not comparable:
        L.append(
            f"> 本次只处理 **{len(commits)}** 条提交，少于完整版本的 **{FULL_COMMIT_COUNT}** 条"
            "（子集运行）。文档登记的三个外沿数字是在完整版本上算的，**此处不可比**，"
            "下表只出示本脚本的复算值。全量运行时才要求逐项相等。\n"
        )
    L.append("| 判据 | 本脚本复算 | 文档登记 | 一致 |\n|---|---|---|---|")
    for key, name in (
        ("has_id", "只要求含 `AMQ-<数字>` 编号"),
        ("id_and_fix_word", "编号 **且** 含 `fix`/`bug`/`patch`（词首边界）"),
        ("id_and_fix_form", "编号 **且** 含 `fix` 词形（词首边界）"),
    ):
        if comparable:
            mark = "✅" if got[key] == EXPECTED_OUTER[key] else "❌"
            expected = str(EXPECTED_OUTER[key])
        else:
            mark = "—（子集，不可比）"
            expected = f"{EXPECTED_OUTER[key]}（全量）"
        L.append(f"| {name} | {got[key]} | {expected} | {mark} |")
    if comparable:
        L.append(f"\n自检结论：**{'全部一致，判据实现与文档口径相符' if ok else '存在不一致，需核对判据实现或更新文档登记'}**\n")
    else:
        L.append("\n自检结论：**子集运行，仅登记复算值；判据实现与文档是否一致需在全量运行后确认**\n")

    L.append("## 各方法结果\n")
    L.append("| 指标 | " + " | ".join(r["method"] for r in results) + " |\n|---|" + "---|" * len(results))
    def row(name: str, fn) -> str:
        return f"| {name} | " + " | ".join(str(fn(r)) for r in results) + " |"
    L.append(row("打标成功数（进样本集）", lambda r: len(r["sample"])))
    L.append(row("**正样本数**（引入缺陷）", lambda r: r["pos"]))
    L.append(row("负样本数", lambda r: r["neg"]))
    L.append(row("**正样本比例**", lambda r: f"**{r['ratio']:.2%}**"))
    L.append(row("打标方法 `label_method`", lambda r: f"`{r['method']}`"))
    L.append(row("回溯未命中的修复提交（不入样本，D5）", lambda r: r["unresolved"]))
    L.append(row("　其中：引入方落在窗口/版本之外", lambda r: r["out_of_window"]))
    L.append(row("　其中：根提交无父提交", lambda r: r["no_parent"]))
    L.append(row("　其中：diff 取数失败", lambda r: r["diff_failed"]))
    L.append(row("blame/日志调用次数", lambda r: r["blame_calls"]))
    L.append(row("耗时（秒）", lambda r: f"{r['elapsed']:.1f}"))

    L.append("\n### 正样本比例是否落在合理区间（规格 szz-labeling）\n")
    for r in results:
        if ABNORMAL_LOW <= r["ratio"] <= ABNORMAL_HIGH:
            L.append(f"- ❌ **`{r['method']}` 正样本比例 {r['ratio']:.2%} 落在 {ABNORMAL_LOW:.0%}–{ABNORMAL_HIGH:.0%} 异常区间**，先复核打标逻辑，不要进入下游")
        else:
            L.append(f"- ✅ `{r['method']}` 正样本比例 {r['ratio']:.2%} 不在异常区间（经验值：个位数到十几百分点）")

    if len(results) == 2:
        a, b = results
        sa, sb = a["labels"], b["labels"]
        only_a = sorted(set(sa) - set(sb))
        only_b = sorted(set(sb) - set(sa))
        both = sorted(set(sa) & set(sb))
        L.append("\n## 两套方法对照（规格要求：差异必须可量化，不静默取其一）\n")
        L.append("| 项 | 值 |\n|---|---|")
        L.append(f"| 两套都判为正样本 | {len(both)} |")
        L.append(f"| 仅 `{a['method']}` 判为正样本 | {len(only_a)} |")
        L.append(f"| 仅 `{b['method']}` 判为正样本 | {len(only_b)} |")
        diff = len(only_a) + len(only_b)
        base = len(set(sa) | set(sb))
        L.append(f"| 标签不一致总数 | {diff} |")
        L.append(f"| 正样本分歧率 | {diff / base:.2%}（不一致数 ÷ 两法正样本并集） |")
        if only_b:
            L.append(f"\n`{b['method']}` 多认出的前 10 条（粒度粗 ⇒ 容易把「只是同一个文件被改过」也算成引入方）：\n")
            L.append("| commit_hash |\n|---|")
            for h in only_b[:10]:
                L.append(f"| `{h}` |")

    L.append("\n## 说明\n")
    L.append("- 本产物是**带标签样本集，不含特征列**；特征见下一步 `03_*.py` 产出的 `commit_feature`")
    L.append("- `szz` 为自研标准行级 SZZ 实现：契约表二把该方法标注为「PySZZ」，但 PySZZ 不在 PyPI（404），按兜底策略自研替代，**需走契约变更更新该括注**")
    L.append("- `szz_lite` 为文件级回溯简化版：粒度粗、快一个量级，差异见上方对照表")
    L.append("- 回溯未命中的修复提交按 D5 排除出样本集，不当负样本；三个数字（总数 / 打标成功数 / 未判定数）在此表同时出示")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ══ 主流程 ════════════════════════════════════════════════════════════════


def main() -> int:
    args = parse_args()

    if not _GIT:
        print("[失败] 找不到 git 可执行文件（blame/log 回溯需要它）", file=sys.stderr)
        return 2
    if not (args.repo / ".git").exists():
        print(f"[失败] 找不到仓库：{args.repo}（先按 docs/data-pipeline.md 第 2 节克隆并固定版本）", file=sys.stderr)
        return 2

    commits = load_commits(args.commits)
    if not commits:
        print("[失败] 提交清单为空", file=sys.stderr)
        return 3

    fix_rows = [r for r in commits if is_fix_commit(r["message"])]
    print(f"[进行] 样本提交 {len(commits)} 条，识别修复提交 {len(fix_rows)} 条（判据 D4）")

    selfcheck = judge_selfcheck(commits)
    got, ok, comparable = selfcheck
    verdict = ("与文档登记一致" if ok else "与文档登记不一致，请核对") if comparable else "子集运行，外沿不可比"
    print(
        f"[自检] 判据外沿：含编号 {got['has_id']} / 编号+fix词 {got['id_and_fix_word']} / "
        f"编号+fix词形 {got['id_and_fix_form']} —— {verdict}"
    )
    if not fix_rows:
        print("[失败] 没有识别到任何修缺陷提交，判据或输入有问题", file=sys.stderr)
        return 4

    labeled_at = args.labeled_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    methods = METHODS if args.method == "both" else (args.method,)

    results = []
    for m in methods:
        print(f"[进行] 打标方法 {m} —— 处理 {min(args.limit or len(fix_rows), len(fix_rows))} 条修复提交")
        res = run_method(m, args.repo, commits, fix_rows, args.limit)
        results.append(res)
        stem = f"commit_labels_{args.tag}_{m}" if args.tag else f"commit_labels_{m}"
        out = DATA_DIR / f"{stem}.csv"
        write_labels(out, m, res, labeled_at)
        print(
            f"[完成] {m}：正样本 {res['pos']} / 负样本 {res['neg']} / "
            f"比例 {res['ratio']:.2%} / 未命中 {res['unresolved']} / 耗时 {res['elapsed']:.1f}s"
        )
        print(f"       标签：{out}")

    report = REPORTS_DIR / "szz_labeling_stats.md"
    write_report(report, commits, fix_rows, results, selfcheck, args.limit, args.tag)
    print(f"       统计表：{report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
