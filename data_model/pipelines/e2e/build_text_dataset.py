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

── 文本构造口径（与 semantic 线共用 `pipelines/text_source.py`，两线不会分叉）────────
每个改动文件生成一段：文件头（a/b 路径）+ patch 文本；单文件超过上限按行截断，
总文本超过 `--max-chars` 截断。合并提交（父提交数 != 1）按其第一个父提交取 diff。
提交存在但没有可取的文本变更时写占位串并登记来源：有父提交但 diff 为空 →
`no_text_change`（`[no-text-change]`，SVN 属性/ignore 类提交）；根提交 →
`root_commit`（`[root-commit]`）。提交在克隆仓库里**取不到** → 仍然跳过并单独计数，
不用占位串掩盖（那意味着切分文件与克隆版本不一致，是真缺陷）。
产出比原来多一列 `text_source`，只做统计与报告登记，**不进特征、不进模型输入**。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from git import Repo
from git.exc import BadName, BadObject, GitCommandError

try:
    from .. import text_source
except ImportError:  # 直接以脚本方式跑（python build_text_dataset.py）时没有包上下文
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from pipelines import text_source

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


def commit_text(repo: Repo, commit_hash: str, max_chars: int) -> tuple[str, str] | None:
    """返回 `(text, text_source)`；提交在克隆仓库里取不到时返回 None。

    返回 None 只表示「这条提交读不出来」——调用方必须跳过并单独计数，不能落占位串，
    否则会把「切分文件与克隆版本不一致」这种真缺陷伪装成「该提交无文本变更」。
    """
    try:
        commit = repo.commit(commit_hash)
    except (BadName, BadObject, GitCommandError, ValueError):
        return None
    try:
        has_parents = bool(commit.parents)
        diffs = commit.diff(commit.parents[0], create_patch=True, R=True) if has_parents else []
    except (GitCommandError, OSError, ValueError):
        return None
    assembled, has_content = text_source.assemble(diffs, max_chars)
    return text_source.classify(has_parents, assembled, has_content)


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
    unreachable = 0
    for _, r in rows.iterrows():
        got = commit_text(repo, str(r["commit_hash"]), args.max_chars)
        if got is None:
            unreachable += 1
            continue
        text, source = got
        out_rows.append(text_source.make_row(r["commit_hash"], text, source,
                                             int(r["is_bug_inducing"]), r["feature_version"]))

    if not out_rows:
        print("[build_text] 0 条有效文本（全部取不到提交），未产出文件", file=sys.stderr)
        return 1

    out_df = pd.DataFrame(out_rows, columns=text_source.TEXT_COLUMNS)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False, quoting=__import__("csv").QUOTE_ALL)

    stats = text_source.summarize(out_df["text_source"])
    positives = {name: int(((out_df["text_source"] == name) & (out_df["label"] == 1)).sum())
                 for name in text_source.SOURCES}
    pos = int(out_df["label"].sum())
    print(f"[build_text] 已写 {len(out_df)} 条（正样本 {pos} / 负样本 {len(out_df) - pos}）")
    print("[build_text] 文本来源：" + "，".join(f"{k}={v}" for k, v in stats.items()))
    print("[build_text] 占位行中的正样本：" + "，".join(
        f"{k}={positives[k]}" for k in (text_source.SOURCE_NO_TEXT_CHANGE,
                                        text_source.SOURCE_ROOT_COMMIT)))
    if unreachable:
        # 取不到的提交不等于「无文本变更」，必须显式报警：切分文件与克隆版本可能不一致
        print(f"[build_text] ⚠ 跳过 {unreachable} 条在克隆仓库里取不到的提交（未落占位串）",
              file=sys.stderr)
    print(f"[build_text] -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
