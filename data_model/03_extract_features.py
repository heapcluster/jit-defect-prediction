"""03 抽取 Kamei 14 项特征。

对应 OpenSpec change: data-collection-and-szz-labeling（第 4 组任务的第 ④ 步）
字段与取值口径: docs/contracts/feature-columns.md（已冻结，feature_version = v1）
                docs/contracts/data-fields.md 表四 `commit_feature`

── 纪律 ───────────────────────────────────────────────────────────────────
列名逐字取自契约第三节，**不在此处发明列名**。归一化与对数变换逐条取自契约第四节：

  la / lt、ld / lt、lt / nf、nuc / nf   —— 第四节「本组定稿口径」
  其余各项                            —— 原值
  最后全部 14 项取对数                  —— 第四节「对数变换的三条补充」
    · `fix` 不取对数（0/1 布尔值，取对数无意义）
    · 用自然对数 ln
    · 值为 0 时用 ln(1+x)

── 特征的时间方向（这一条错了整份数据就废了）─────────────────────────────
所有「历史类」特征（`ndev`/`age`/`nuc`/`exp`/`rexp`/`sexp`）只使用**严格早于本次提交**
的提交来算，绝不允许看到本次提交之后发生的事。`lt` 取的是**父提交时刻**的文件行数。
这与 AGENTS.md 里「禁止随机切分、按时间序切分」是同一条纪律的两面。

── 计算成本 ───────────────────────────────────────────────────────────────
历史明细用**一次** `git log --numstat` 拿全（约 9.5 万行），不按提交逐个问 git；
`lt` 需要的「父提交时刻各文件行数」用一个常驻 `git cat-file --batch` 进程批量取，
避免为每个文件起一个新进程。全量 11,050 条提交在本机是分钟级，不是小时级。

── 契约里没写清、本脚本必须作主的三处（跑通后要回契约确认）─────────────────
1. **`rexp` 的衰减函数契约未定义**，只写了中文「按时间衰减加权」。本脚本按 Kamei
   原文口径取 `Σ count(n) / (n + 1)`，`n` = 该次历史提交距本次提交的整年数
   （文献转述：「5 次改动发生在 3 年前 ⇒ 记为 5/3，REXP 为这些加权值的求和」）。
   **这是本脚本的取值来源，契约第四节需补一行把它写成字面口径。**
2. **契约第三节把 `ns/nd/nf/la/ld/lt` 定为 INT，第四节又要求全部取对数** ——
   取完对数必为小数，两者不能同时成立。本脚本按第四节执行（落盘值是小数），
   **契约第三节这六行的类型需要改成 DECIMAL/DOUBLE。**
3. **`ln(x)` 与 `ln(1+x)` 之间不连续**：归一化后的比率落在 [0,1]，`ln` 在 0 附近趋于
   负无穷，而 0 值被规定记作 0。于是 x=0.001 记 -6.9、x=0 记 0，同量级的两条提交
   数值相差极大。本脚本按契约字面实现，**不擅自改成 `ln(1+x)` 通算** —— 但这条要
   在对外报告里注明，并建议 v2 统一为 `ln(1+x)`。
   实测证据（窗口子集 275 条）：`la` 有 7 条记 0，其余最小值为 **-7.43**；`ld` 有 33 条
   记 0，最小值为 **-8.62**。即「新增行数占比极小」与「新增行数为 0」在数值上分居两端。

4. **`nuc` 的聚合方式契约有歧义**，只写「这些文件此前被改动过的独立次数」。两种读法：
   ①按文件分别数「该文件此前被改过几次」再**求和**；②把这些文件的既往改动提交**取并集**。
   本脚本取 **①求和**，依据两条：契约第四节把 `nuc` 除以 `nf`（若为并集，则不会像原文
   所说那样与 `nf` 高度相关，除以 `nf` 也就不成立）；Kamei 原文表述为
   「counting the number of commits that caused changes to specific files」——主语是
   逐个文件。**这一条与 `ndev` 故意不对称**：`ndev` 数的是「人」，必须去重取并集。
   契约第四节需补一行把它写明。
"""

from __future__ import annotations

import argparse
import bisect
import csv
import importlib.util
import math
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DEFAULT_REPO = BASE / "data" / "activemq"
DEFAULT_COMMITS = BASE / "data" / "commits.csv"
DEFAULT_OUT = BASE / "data" / "commit_features.csv"
DEFAULT_RAW = BASE / "data" / "commit_features_raw.csv"
REPORTS_DIR = BASE / "reports"

SZZ_SCRIPT = BASE / "02_szz_labeling.py"

# docs/contracts/feature-columns.md 第二节：标识列
ID_FIELDS = ["commit_hash", "committed_at", "feature_version"]

# docs/contracts/feature-columns.md 第三节：14 项特征列，顺序即契约中的出现顺序
FEATURE_FIELDS = [
    "ns", "nd", "nf", "entropy",          # 代码分布 Diffusion
    "la", "ld", "lt",                     # 规模 Size
    "fix",                                # 目的 Purpose
    "ndev", "age", "nuc",                 # 历史 History
    "exp", "rexp", "sexp",                # 开发者经验 Experience
]

FEATURE_VERSION = "v1"
REPO_NAME = "activemq"

# 契约第四节：entropy 采用两周（14 天）滚动窗口（Kamei 引用 Hassan 的定义）
ENTROPY_WINDOW_SECONDS = 14 * 24 * 3600
DAYS_PER_YEAR = 365.25


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="按 docs/contracts/feature-columns.md 抽取 Kamei 14 项特征",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--repo", type=Path, default=DEFAULT_REPO, help=f"仓库副本路径（默认 {DEFAULT_REPO}）")
    p.add_argument("--commits", type=Path, default=DEFAULT_COMMITS, help=f"01 产出的提交清单（默认 {DEFAULT_COMMITS}）")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"契约口径的特征表（默认 {DEFAULT_OUT}）")
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW, help=f"未变换的原值中间产物（默认 {DEFAULT_RAW}）")
    p.add_argument("--since", default=None, help="只算此日期之后的提交，如 2023-01-01；不传=全量。历史特征仍用完整历史")
    p.add_argument("--limit", type=int, default=0, help="只算前 N 条（烟雾测试用，0=不限）")
    return p.parse_args()


# ══ git 调用 ══════════════════════════════════════════════════════════════


def run_git(repo_dir: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} 失败（exit {proc.returncode}）："
            f"{proc.stderr.decode('utf-8', 'replace').strip()[:300]}"
        )
    return proc.stdout.decode("utf-8", "replace")


def blob_line_counts(repo_dir: Path, specs: list[str]) -> dict[str, int]:
    """批量取 `<父提交>:<路径>` 的行数，返回 {spec: 行数}。

    用常驻 `git cat-file --batch`：入参写一条、结果读一条。写与读必须并行，
    否则 6 万多条 spec 会把管道缓冲区写满而死锁，故写线程单独跑。
    路径在父提交不存在（新增文件）时 git 回 `missing`，记 0 行。
    """
    if not specs:
        return {}
    proc = subprocess.Popen(
        ["git", "-C", str(repo_dir), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def _writer() -> None:
        assert proc.stdin is not None
        try:
            for s in specs:
                proc.stdin.write((s + "\n").encode("utf-8", "replace"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    threading.Thread(target=_writer, daemon=True).start()
    assert proc.stdout is not None
    out: dict[str, int] = {}
    for s in specs:
        header = proc.stdout.readline()
        if not header:
            break
        parts = header.decode("utf-8", "replace").rstrip("\n").split(" ")
        if len(parts) < 3 or parts[-1] == "missing":
            out[s] = 0
            continue
        size = int(parts[-1])
        body = proc.stdout.read(size)
        proc.stdout.read(1)  # 对象内容后的换行
        n = body.count(b"\n")
        if body and not body.endswith(b"\n"):
            n += 1  # 末行没有换行符也算一行
        out[s] = n
    proc.wait()
    return out


# ══ 历史明细 ══════════════════════════════════════════════════════════════


def subsystem_of(path: str) -> str:
    """Kamei 的 subsystem = 路径的根目录名。根目录下的文件单列一组。"""
    parts = path.split("/")
    return parts[0] if len(parts) > 1 else "(root)"


def directory_of(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:-1]) if len(parts) > 1 else "(root)"


def scan_history(repo_dir: Path) -> dict[str, dict]:
    """一次 `git log --numstat` 取回全部非合并提交的文件级增删行明细。

    `--no-renames`：关掉重命名检测，改名会拆成「删旧 + 增新」，不必再解析 `old => new`。
    二进制文件的增删列是 `-`，按 0 计。
    """
    text = run_git(
        repo_dir,
        "log",
        "--no-merges",
        "--no-renames",
        "--numstat",
        "--format=@@%H|%at|%ae|%an",
        "HEAD",
    )
    commits: dict[str, dict] = {}
    cur: dict | None = None
    for line in text.split("\n"):
        if line.startswith("@@"):
            h, ts, email, name = line[2:].split("|", 3)
            cur = commits.setdefault(
                h, {"ts": int(ts), "email": email.strip().lower(), "name": name.strip(), "files": []}
            )
            continue
        if not line.strip() or cur is None:
            continue
        cols = line.split("\t")
        if len(cols) != 3:
            continue
        added, deleted, path = cols
        if not path or "=>" in path:
            continue
        cur["files"].append(
            (
                0 if added == "-" else int(added),
                0 if deleted == "-" else int(deleted),
                path.strip('"'),
            )
        )
    return commits


class HistoryIndex:
    """按文件 / 作者 / 子系统建索引，支持「严格早于某时刻」的前缀查询。

    索引里存的是全部提交（含窗口之前的），这正是契约要的：特征用的是历史。
    """

    def __init__(self, commits: dict[str, dict]) -> None:
        self._by_time = sorted(
            ((c["ts"], h) for h, c in commits.items()),
            key=lambda t: (t[0], t[1]),
        )
        self._times = [t for t, _ in self._by_time]

        file_events: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        author_events: dict[str, list[int]] = defaultdict(list)
        author_sub_events: dict[tuple[str, str], list[int]] = defaultdict(list)

        for h, c in commits.items():
            author_events[c["email"]].append(c["ts"])
            subs = {subsystem_of(p) for _, _, p in c["files"]}
            for s in subs:
                author_sub_events[(c["email"], s)].append(c["ts"])
            for _, _, p in c["files"]:
                file_events[p].append((c["ts"], h, c["email"]))

        for lst in author_events.values():
            lst.sort()
        for lst in author_sub_events.values():
            lst.sort()
        for lst in file_events.values():
            lst.sort(key=lambda t: (t[0], t[1]))

        self.file_events = dict(file_events)
        self.author_events = dict(author_events)
        self.author_sub_events = dict(author_sub_events)
        self.commits = commits

    @staticmethod
    def _prefix_lt(lst: list, ts: int) -> int:
        """严格早于 ts 的元素个数（bisect_left 天然排除相等的时间戳）。"""
        return bisect.bisect_left(lst, ts)

    def prior_file_events(self, path: str, ts: int) -> list[tuple[int, str, str]]:
        ev = self.file_events.get(path)
        if not ev:
            return []
        times = [e[0] for e in ev]
        return ev[: bisect.bisect_left(times, ts)]

    def prior_author_count(self, email: str, ts: int) -> int:
        return self._prefix_lt(self.author_events.get(email, []), ts)

    def prior_author_subsystem_count(self, email: str, subsystems: set[str], ts: int) -> int:
        hits = set()
        for s in subsystems:
            lst = self.author_sub_events.get((email, s))
            if not lst:
                continue
            for t in lst[: self._prefix_lt(lst, ts)]:
                hits.add(t)
        return len(hits)

    def rexp(self, email: str, ts: int) -> float:
        """Σ 1/(n+1)，n = 该次历史提交距本次的整年数（Kamei 原文口径，见模块 docstring 第 1 条）。"""
        lst = self.author_events.get(email, [])
        total = 0.0
        for t in lst[: self._prefix_lt(lst, ts)]:
            n = int((ts - t) / (DAYS_PER_YEAR * 86400))
            total += 1.0 / (n + 1)
        return total


def entropy_series(commits: dict[str, dict], target_ts: list[int]) -> list[float]:
    """对每条目标提交算两周窗口内的改动信息熵（契约第四节：Kamei 引用 Hassan）。

    窗口 `(t - 14 天, t]`；`p_k` = 文件 k 在窗口内的被改次数 ÷ 窗口内全部文件的被改总次数；
    `H = -Σ p_k·log₂p_k`；窗口内无改动时记 0。
    用滑动窗口（双指针 + 计数器）实现：目标提交已按时间升序，所以窗口只向前走，
    不重复扫历史。逐个提交重扫窗口在 11,050 条上会退化。
    """
    ordered = sorted(((c["ts"], h) for h, c in commits.items()))
    out: list[float] = []
    counts: Counter[str] = Counter()
    total = 0
    left = right = 0
    for ts in target_ts:
        while right < len(ordered) and ordered[right][0] <= ts:
            for _, _, p in commits[ordered[right][1]]["files"]:
                counts[p] += 1
                total += 1
            right += 1
        while left < right and ordered[left][0] <= ts - ENTROPY_WINDOW_SECONDS:
            for _, _, p in commits[ordered[left][1]]["files"]:
                counts[p] -= 1
                total -= 1
                if counts[p] == 0:
                    del counts[p]
            left += 1
        if total == 0:
            out.append(0.0)
            continue
        h = 0.0
        for c in counts.values():
            p = c / total
            h -= p * math.log2(p)
        out.append(h)
    return out


# ══ 特征计算 ══════════════════════════════════════════════════════════════


def load_is_fix_commit():
    """复用 02 脚本的判据实现，避免两处各写一份正则而慢慢走偏。

    文件名以数字开头，无法用 import 语句导入，故按路径加载。
    """
    spec = importlib.util.spec_from_file_location("szz_labeling", SZZ_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载判据模块：{SZZ_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_fix_commit


def to_epoch(committed_at: str) -> int:
    return int(datetime.strptime(committed_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def compute_raw(
    targets: list[dict],
    commits: dict[str, dict],
    index: HistoryIndex,
    is_fix_commit,
    repo_dir: Path,
    progress_every: int = 500,
) -> list[dict]:
    """对每条目标提交算出 14 项的**原值**（尚未归一化与取对数）。"""
    # 先把所有「父提交:路径」的 spec 收集齐，一次 batch 取完行数
    specs: list[str] = []
    seen: set[str] = set()
    plan: list[tuple[dict, int, list[tuple[int, int, str]]]] = []
    for row in targets:
        h = row["commit_hash"]
        ts = to_epoch(row["committed_at"])
        files = commits.get(h, {}).get("files", [])
        plan.append((row, ts, files))
        parent = row.get("parent_hash") or ""
        if not parent:
            continue
        for _, _, p in files:
            spec = f"{parent}:{p}"
            if spec not in seen:
                seen.add(spec)
                specs.append(spec)

    print(f"[进行] 取 {len(specs)} 个父提交时刻的文件行数（lt 用）……", flush=True)
    line_counts = blob_line_counts(repo_dir, specs)

    entropies = entropy_series(commits, [ts for _, ts, _ in plan])

    rows: list[dict] = []
    t0 = time.time()
    for i, ((row, ts, files), ent) in enumerate(zip(plan, entropies), 1):
        h = row["commit_hash"]
        email = commits.get(h, {}).get("email", "")
        parent = row.get("parent_hash") or ""

        paths = [p for _, _, p in files]
        subsystems = {subsystem_of(p) for p in paths}
        directories = {directory_of(p) for p in paths}

        la = sum(a for a, _, _ in files)
        ld = sum(d for _, d, _ in files)
        # lt：改动前这些文件的总行数（父提交时刻）
        lt = sum(line_counts.get(f"{parent}:{p}", 0) for p in paths) if parent else 0

        # 历史类特征只认「严格早于本次提交」的记录
        prior_emails: set[str] = set()
        ages: list[float] = []
        nuc = 0
        for p in set(paths):
            ev = index.prior_file_events(p, ts)
            if not ev:
                continue
            # nuc：逐个文件数「此前被改过几次」再求和（见模块 docstring 第 4 条）
            nuc += len({e_hash for _, e_hash, _ in ev})
            for _, _, e_email in ev:
                prior_emails.add(e_email)
            ages.append((ts - ev[-1][0]) / 86400.0)

        rows.append(
            {
                "commit_hash": h,
                "committed_at": row["committed_at"],
                "feature_version": FEATURE_VERSION,
                "ns": len(subsystems),
                "nd": len(directories),
                "nf": len(set(paths)),
                "entropy": ent,
                "la": la,
                "ld": ld,
                "lt": lt,
                "fix": 1 if is_fix_commit(row["message"]) else 0,
                "ndev": len(prior_emails),
                "age": statistics.fmean(ages) if ages else 0.0,
                "nuc": nuc,
                "exp": index.prior_author_count(email, ts) if email else 0,
                "rexp": index.rexp(email, ts) if email else 0.0,
                "sexp": index.prior_author_subsystem_count(email, subsystems, ts) if email else 0,
            }
        )
        if progress_every and i % progress_every == 0:
            print(f"    {i}/{len(plan)} 条，已用 {time.time() - t0:.0f}s", flush=True)
    return rows


# ══ 契约口径变换 ══════════════════════════════════════════════════════════


def log_v1(x: float) -> float:
    """契约第四节「对数变换的三条补充」的字面实现。

    `x > 0` 用 `ln(x)`；`x == 0` 用 `ln(1+0) = 0`。
    这条在 0 附近不连续，是契约本身的缺陷（见模块 docstring 第 3 条），本脚本不擅自修正。
    """
    return math.log(x) if x > 0 else 0.0


def apply_contract(rows: list[dict]) -> list[dict]:
    """把原值变换成契约第四节规定的落库口径。"""
    out: list[dict] = []
    for r in rows:
        lt = r["lt"]
        nf = r["nf"]
        la_n = (r["la"] / lt) if lt else 0.0
        ld_n = (r["ld"] / lt) if lt else 0.0
        lt_n = (lt / nf) if nf else 0.0
        nuc_n = (r["nuc"] / nf) if nf else 0.0
        out.append(
            {
                "commit_hash": r["commit_hash"],
                "committed_at": r["committed_at"],
                "feature_version": r["feature_version"],
                "ns": log_v1(r["ns"]),
                "nd": log_v1(r["nd"]),
                "nf": log_v1(r["nf"]),
                "entropy": log_v1(r["entropy"]),
                "la": log_v1(la_n),
                "ld": log_v1(ld_n),
                "lt": log_v1(lt_n),
                "fix": r["fix"],  # 契约明确：布尔值不取对数
                "ndev": log_v1(r["ndev"]),
                "age": log_v1(r["age"]),
                "nuc": log_v1(nuc_n),
                "exp": log_v1(r["exp"]),
                "rexp": log_v1(r["rexp"]),
                "sexp": log_v1(r["sexp"]),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ID_FIELDS + FEATURE_FIELDS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)


# ══ 报告 ══════════════════════════════════════════════════════════════════


def write_report(
    path: Path,
    rows_raw: list[dict],
    rows_v1: list[dict],
    targets: list[dict],
    since: str | None,
    limit: int,
) -> None:
    L: list[str] = []
    L.append("# 特征抽取统计（03_extract_features.py 产出）\n")
    L.append("> 本文件可入库，是特征口径落地的证据（见 `docs/data-pipeline.md` 第 4 节第 ④ 步）\n")
    L.append("## 输入\n")
    L.append("| 项 | 值 |\n|---|---|")
    L.append(f"| 特征表口径版本 | `{FEATURE_VERSION}`（`docs/contracts/feature-columns.md` 已冻结） |")
    L.append(f"| 提交清单 | `{len(targets)}` 条 |")
    L.append(f"| 时间窗口 | `{since or '(全量)'}` |")
    if limit:
        L.append(f"| **本次仅算前 N 条（烟雾测试）** | **{limit}** |")
    L.append(f"| 时间跨度 | {targets[0]['committed_at']} ~ {targets[-1]['committed_at']} |")
    L.append(f"| 输出列 | {len(ID_FIELDS)} 个标识列 + {len(FEATURE_FIELDS)} 项特征列 |")
    L.append("\n> `entropy` 的窗口为两周（14 天）滚动窗口，其余历史类特征一律只使用**严格早于本次提交**的记录。\n")

    L.append("## 落库口径（契约第四节变换后的分布）\n")
    L.append("| 特征 | 最小 | 中位 | 平均 | 最大 | 取值为 0 的条数 |\n|---|---|---|---|---|---|")
    for col in FEATURE_FIELDS:
        vals = [r[col] for r in rows_v1]
        zeros = sum(1 for v in vals if v == 0)
        L.append(
            f"| `{col}` | {min(vals):.4f} | {statistics.median(vals):.4f} | "
            f"{statistics.fmean(vals):.4f} | {max(vals):.4f} | {zeros} |"
        )

    L.append("\n## 原值分布（未归一化、未取对数，仅供核对量级）\n")
    L.append("| 特征 | 最小 | 中位 | 平均 | 最大 |\n|---|---|---|---|---|")
    for col in FEATURE_FIELDS:
        vals = [r[col] for r in rows_raw]
        L.append(
            f"| `{col}` | {min(vals):.4f} | {statistics.median(vals):.4f} | "
            f"{statistics.fmean(vals):.4f} | {max(vals):.4f} |"
        )

    L.append("\n## 契约里没写清、由本脚本作主的四处（需回契约确认）\n")
    L.append(
        "| # | 问题 | 本脚本的处置 | 建议 |\n|---|---|---|---|\n"
        "| 1 | `rexp` 的衰减函数契约只写「按时间衰减加权」，未给公式 | 按 Kamei 原文口径 `Σ count(n)/(n+1)`，`n` = 距本次提交的整年数 | 契约第四节补一行写成字面口径 |\n"
        "| 2 | 契约第三节把 `ns/nd/nf/la/ld/lt` 定为 INT，第四节又要求全部取对数 | 按第四节执行，落盘值为小数 | 第三节这六行的类型改为 DECIMAL/DOUBLE |\n"
        "| 3 | `ln(x)` 与「0 值用 `ln(1+x)`」之间不连续，0 附近的数值会被拉出巨大落差 | 按契约字面实现，不擅自统一 | 建议 v2 统一为 `ln(1+x)` 通算，并升 `feature_version` |\n"
        "| 4 | `nuc` 的聚合方式有歧义：按文件计数求和，还是对既往提交取并集 | 取**按文件计数求和**（依据：契约第四节把它除以 `nf`；原文表述为「count of commits that caused changes to specific files」）。`ndev` 数的是人，仍取并集，两者故意不对称 | 契约第四节补一行写明聚合方式 |\n"
    )
    L.append("## 说明\n")
    L.append("- 本产物是**特征表**（`commit_feature`），不含标签列；标签在 `commit_label` / 02 的产出里，两者在 04 步按 `commit_hash` 汇总")
    L.append("- `fix` 列是「本次提交的目的是不是修缺陷」（判据与 02 脚本同一份实现），**不是**预测目标 `is_bug_inducing`")
    L.append("- 原值中间产物落在 `data_model/data/`，不入库；入库的只有本统计表")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ══ 主流程 ════════════════════════════════════════════════════════════════


def main() -> int:
    args = parse_args()

    if not (args.repo / ".git").exists():
        print(f"[失败] 找不到仓库：{args.repo}（先按 docs/data-pipeline.md 第 2 节克隆并固定版本）", file=sys.stderr)
        return 2
    if not args.commits.exists():
        print(f"[失败] 找不到提交清单：{args.commits}（先跑 01_extract_commits.py）", file=sys.stderr)
        return 2
    if not SZZ_SCRIPT.exists():
        print(f"[失败] 找不到判据来源：{SZZ_SCRIPT}", file=sys.stderr)
        return 2

    with args.commits.open(encoding="utf-8", newline="") as f:
        all_rows = list(csv.DictReader(f))
    all_rows.sort(key=lambda r: (r["committed_at"], r["commit_hash"]))

    targets = [r for r in all_rows if (not args.since or r["committed_at"][:10] >= args.since)]
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        print("[失败] 窗口过滤后没有提交可算，检查 --since 是否晚于仓库存在时间", file=sys.stderr)
        return 3

    print(f"[进行] 扫描仓库完整历史明细（一次 git log --numstat）……", flush=True)
    commits = scan_history(args.repo)
    print(f"        历史索引：{len(commits)} 条非合并提交")

    missing = [r["commit_hash"] for r in targets if r["commit_hash"] not in commits]
    if missing:
        print(f"[失败] {len(missing)} 条目标提交在历史明细里找不到，如 {missing[0]}；01 与 03 的过滤口径可能不一致", file=sys.stderr)
        return 4

    index = HistoryIndex(commits)
    is_fix_commit = load_is_fix_commit()

    print(f"[进行] 计算 {len(targets)} 条提交的 14 项特征……", flush=True)
    rows_raw = compute_raw(targets, commits, index, is_fix_commit, args.repo)
    rows_v1 = apply_contract(rows_raw)

    write_csv(args.out, rows_v1)
    write_csv(args.raw, rows_raw)
    report = REPORTS_DIR / "feature_stats.md"
    write_report(report, rows_raw, rows_v1, targets, args.since, args.limit)

    print(f"[完成] 特征表：{args.out}（{len(rows_v1)} 行 × {len(FEATURE_FIELDS)} 项特征）")
    print(f"       原值中间产物：{args.raw}")
    print(f"       统计表：{report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
