"""01 抽取提交清单。

对应 OpenSpec change: data-collection-and-szz-labeling
规格: openspec/changes/data-collection-and-szz-labeling/specs/commit-collection/spec.md

只做三件事：读提交记录、过滤合并提交、按契约落字段。
字段口径以 docs/database/commit.md 为准，不在此处发明列名。

为什么要 --since：全量提交做回溯的开销尚未实测（见 docs/common/data-pipeline.md
第 1 节）。首次跑通先用窗口子集验证链路，跑通后再扩大到全量。
窗口只决定「哪些提交进样本」，不影响特征计算 —— 特征用的是窗口之前的历史。
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path

from git import Repo

BASE = Path(__file__).resolve().parent
DEFAULT_OUT = BASE.parent / "data" / "commits.csv"
REPORTS_DIR = BASE / "reports"

# 与 docs/database/commit.md 的提交字段对齐（id 由数据库自增，CSV 不落）
FIELDS = [
    "repo_name",
    "commit_hash",
    "author_name",
    "author_email",
    "committed_at",
    "message",
    "parent_hash",
]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="从指定 Git 仓库抽取提交清单")
    p.add_argument("--repo", type=Path, required=True, help="仓库副本路径")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"输出 CSV（默认 {DEFAULT_OUT}）")
    p.add_argument("--since", default=None, help="只取此日期之后的提交，如 2018-01-01；不传=全量")
    return p.parse_args()


def to_utc(ts: int) -> str:
    """统一 UTC，格式与契约的 DATETIME 对齐（时间字段一律 UTC，见命名约定）。"""
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")


def extract_commits(repo_dir: Path, *, ref: str = "HEAD", repo_name: str | None = None,
                    runner=None, progress=None) -> list[dict[str, str]]:
    """Reusable read-only metadata extraction; legacy CLI remains unchanged.

    The injected runner owns security, cancellation and resource limits. No
    output range is applied here: SZZ and features need the complete ancestry.
    """
    if runner is None:
        from importlib import import_module
        runner = import_module("preparation.03_extract_features").run_git
    text = runner(repo_dir, "log", "--no-merges", "-z",
                  "--format=%H%x00%an%x00%ae%x00%ct%x00%B%x00%P", ref, "--")
    fields = text.removesuffix("\x00").split("\x00") if text else []
    if len(fields) % 6:
        raise RuntimeError("无法解析提交元信息")
    rows = []
    for i in range(0, len(fields), 6):
        if progress:
            progress()
        commit_hash, name, email, ts, message, parents = fields[i:i + 6]
        rows.append({"repo_name": repo_name or repo_dir.name, "commit_hash": commit_hash,
                     "author_name": name.strip(), "author_email": email.strip(),
                     "committed_at": to_utc(int(ts)), "message": message.strip(),
                     "parent_hash": parents.split(" ")[0] if parents else ""})
    return sorted(rows, key=lambda row: (row["committed_at"], row["commit_hash"]))


def main() -> int:
    args = parse_args()

    if not (args.repo / ".git").exists():
        print(f"[失败] 找不到仓库：{args.repo}", file=sys.stderr)
        return 2

    repo = Repo(str(args.repo))
    head = repo.head.commit.hexsha

    rows: list[dict[str, str]] = []
    for c in repo.iter_commits(rev=head, since=args.since):
        # 合并提交不引入新的代码改动，其内容已被其父提交覆盖 —— 计入会重复计数
        if len(c.parents) > 1:
            continue
        rows.append(
            {
                "repo_name": args.repo.name,
                "commit_hash": c.hexsha,
                # author 是「谁写的」，committer 是「谁合进去的」；本项目要的是写提交的人
                "author_name": (c.author.name or "").strip(),
                "author_email": (c.author.email or "").strip(),
                # 用 committer 时间：SZZ 的时间序与修复顺序依赖代码真正进入仓库的时刻
                "committed_at": to_utc(c.committed_date),
                "message": c.message.strip(),
                "parent_hash": c.parents[0].hexsha if c.parents else "",
            }
        )

    if not rows:
        print("[失败] 抽取结果为 0 条提交，终止（继续跑打标只会产出空样本集）", file=sys.stderr)
        return 4

    # 契约把 commit_hash 定为唯一键；这里先自查，避免把脏数据带进下游
    hashes = [r["commit_hash"] for r in rows]
    if len(hashes) != len(set(hashes)):
        print("[失败] 提交哈希出现重复，抽取逻辑有问题", file=sys.stderr)
        return 5

    rows.sort(key=lambda r: (r["committed_at"], r["commit_hash"]))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)

    earliest, latest = rows[0]["committed_at"], rows[-1]["committed_at"]
    print(f"[完成] 仓库：{args.repo}")
    print(f"       固定版本 HEAD：{head}")
    print(f"       时间窗口：{args.since}")
    print(f"       提交总数：{len(rows)}")
    print(f"       时间跨度：{earliest} ~ {latest}")
    print(f"       输出：{args.out}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stat = REPORTS_DIR / "commit_extract_stats.md"
    stat.write_text(
        "# 提交抽取统计（01_extract_commits.py 产出）\n\n"
        "> 本文件可入库，是链路可复现的证据之一（见 `docs/common/data-pipeline.md` 第 3 节）\n\n"
        "| 指标 | 值 |\n|---|---|\n"
        f"| 仓库副本 | `{args.repo.name}` |\n"
        f"| 固定版本 HEAD | `{head}` |\n"
        f"| 时间窗口 | `{args.since}` |\n"
        f"| 提交总数（已过滤合并提交） | {len(rows)} |\n"
        f"| 最早提交时间（UTC） | {earliest} |\n"
        f"| 最晚提交时间（UTC） | {latest} |\n",
        encoding="utf-8",
    )
    print(f"       统计表：{stat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
