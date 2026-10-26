"""建/更新 Camel 的 blobless 历史索引（实时 PR 预测的特征来源）。

只取提交 + 树、不含 blob（`--filter=blob:none`），几十 MB，纯粹是「只读历史索引」，
供后端 feature_source 跑 `git log --numstat` / `git cat-file` 算 14 维特征。
它**不是开发库、不进工作流、不持有预测状态**。

用法：
    python infra/clone_camel_history.py --repo apache/camel --path ../camel-history
    python infra/clone_camel_history.py --path ../camel-history --fetch   # 增量更新
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(args: list[str]) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, check=True)


def clone(repo: str, path: Path) -> None:
    if path.exists():
        print(f"skip: {path} 已存在，改用 --fetch 更新")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            f"https://github.com/{repo}.git",
            str(path),
        ]
    )


def fetch(path: Path) -> None:
    if not (path / ".git").exists():
        print(f"error: {path} 不是 git 仓库，先跑 clone", file=sys.stderr)
        raise SystemExit(2)
    run(["git", "-C", str(path), "fetch", "origin", "--prune"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", default="apache/camel", help="owner/name，默认 apache/camel")
    parser.add_argument("--path", required=True, type=Path, help="本地历史索引目录")
    parser.add_argument("--fetch", action="store_true", help="仅增量更新已存在的索引")
    args = parser.parse_args()

    if args.fetch:
        fetch(args.path)
    else:
        clone(args.repo, args.path)
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
