"""e2e 线 ⑩：构造每条提交的「代码变更文本」数据集。

e2e（CodeBERT 端到端微调）不吃 Kamei 14 特征，直接吃**一次提交改了什么代码**——
也就是该提交引入的 diff 文本。本脚本从克隆仓库里取出每个 commit 的 diff，
与 `dataset_szz.csv` 的标签对齐，落盘成 `commit_text.csv`（commit_hash, text, label, feature_version）。

依赖：GitPython（从克隆仓库取 diff）+ pandas。

── 复用上游产物 ───────────────────────────────────────────────────────────
输入：
  · `data/dataset_szz.csv`（`04` 产出，含 commit_hash / is_bug_inducing / feature_version）
  · 克隆仓库（默认自动探测 `data/camel` 或 `data/activemq`，否则扫 `data/` 下含 `.git` 的目录）
输出：
  · `pipelines/e2e/data/commit_text.csv`

── 文本构造口径（与 semantic 线一致，便于两线对照）──────────────────────────
每个改动文件生成一段：文件头（a/b 路径）+ patch 文本；单文件超过上限按行截断，
总文本超过 `--max-chars` 截断。合并提交（父提交数 != 1）按其第一个父提交取 diff。
取不到 diff（根提交 / 仓库缺失）的提交跳过并登记。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from git import Repo
from git.exc import BadName, BadObject, GitCommandError

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE.parent.parent / "data"          # data_model/data
OUT_CSV = BASE / "data" / "commit_text.csv"
MAX_CHARS = 4000


def detect_repo(base: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    for cand in (base / "data" / "camel", base / "data" / "activemq"):
        if (cand / ".git").exists():
            return cand
    data = base / "data"
    if data.exists():
        for d in sorted(data.iterdir()):
            if d.is_dir() and (d / ".git").exists():
                return d
    return None


def commit_diff_text(repo: Repo, commit_hash: str, max_chars: int) -> str | None:
    """返回该提交引入的 diff 文本；取不到返回 None。"""
    try:
        commit = repo.commit(commit_hash)
    except (BadName, BadObject, GitCommandError, ValueError):
        return None
    try:
        if not commit.parents:
            return None  # 根提交无 diff
        parent = commit.parents[0]
        diffs = commit.diff(parent, create_patch=True, R=True)
    except (GitCommandError, OSError, ValueError):
        return None

    parts: list[str] = []
    total = 0
    for d in diffs:
        a_path = d.a_path or ""
        b_path = d.b_path or a_path
        header = f"diff --git a/{a_path} b/{b_path}\n"
        parts.append(header)
        total += len(header)
        patch = d.diff
        if patch:
            text = patch.decode("utf-8", "replace") if isinstance(patch, bytes) else str(patch)
            # 单文件截断：超过 1500 字符的行级 diff 直接跳过该文件剩余
            if len(text) > 1500:
                text = text[:1500] + "\n... [truncated]\n"
            parts.append(text)
            total += len(text)
        if total >= max_chars:
            break
    text = "".join(parts)[:max_chars]
    return text if text.strip() else None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="构造 e2e 线每段提交的 diff 文本数据集（对齐 SZZ 标签）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", type=Path,
                   default=DATA_DIR / "dataset_szz.csv",
                   help="04 产出的样本集（含标签）")
    p.add_argument("--repo", type=Path, default=None,
                   help="克隆仓库路径；默认自动探测 data/camel 或 data/activemq")
    p.add_argument("--out", type=Path, default=OUT_CSV)
    p.add_argument("--max-chars", type=int, default=MAX_CHARS,
                   help="单条提交文本上限字符数（CodeBERT 512 token ≈ 2000 字符）")
    p.add_argument("--limit", type=int, default=0,
                   help="只处理前 N 条（冒烟测试用；0=全量）")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dataset.is_file():
        print(f"[build_text] 找不到样本集：{args.dataset}（先跑 04_build_dataset.py）", file=sys.stderr)
        return 2
    repo_path = detect_repo(BASE.parent.parent, args.repo)
    if repo_path is None:
        print("[build_text] 找不到克隆仓库：请先按 docs/model/data-pipeline.md 克隆并固定版本，"
              "或传 --repo", file=sys.stderr)
        return 2
    print(f"[build_text] 使用仓库：{repo_path}")

    repo = Repo(str(repo_path))
    df = pd.read_csv(args.dataset)
    need = ["commit_hash", "is_bug_inducing", "feature_version"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        print(f"[build_text] 样本集缺列：{missing}", file=sys.stderr)
        return 2

    rows = df.head(args.limit) if args.limit else df
    out_rows = []
    skipped = 0
    for _, r in rows.iterrows():
        text = commit_diff_text(repo, str(r["commit_hash"]), args.max_chars)
        if text is None:
            skipped += 1
            continue
        out_rows.append({
            "commit_hash": str(r["commit_hash"]),
            "text": text,
            "label": int(r["is_bug_inducing"]),
            "feature_version": str(r["feature_version"]),
        })

    if not out_rows:
        print("[build_text] 0 条有效文本（全部取不到 diff），未产出文件", file=sys.stderr)
        return 1

    out_df = pd.DataFrame(out_rows, columns=["commit_hash", "text", "label", "feature_version"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False, quoting=__import__("csv").QUOTE_ALL)

    pos = int(out_df["label"].sum())
    print(f"[build_text] 已写 {len(out_df)} 条（正样本 {pos} / 负样本 {len(out_df) - pos}；跳过 {skipped} 条取不到 diff）")
    print(f"[build_text] -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
