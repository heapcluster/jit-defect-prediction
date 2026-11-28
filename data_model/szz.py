"""标准 SZZ 打标：由修复提交回溯引入提交。"""

from __future__ import annotations

import re

from git import Repo
from git.exc import GitCommandError

_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


def _removed_ranges(patch: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for raw in patch.splitlines():
        match = _HUNK.match(raw)
        if match:
            start = int(match.group(1))
            count = int(match.group(2) or 1)
            if count > 0:
                ranges.append((start, start + count - 1))
    return ranges


def introducing_commits(repo: Repo, fix_hash: str) -> set[str]:
    try:
        commit = repo.commit(fix_hash)
    except (GitCommandError, ValueError):
        return set()
    if not commit.parents:
        return set()
    parent = commit.parents[0]
    found: set[str] = set()
    try:
        diff = parent.diff(commit, create_patch=True)
    except GitCommandError:
        return found
    for item in diff:
        path = item.a_path or item.b_path
        if not path:
            continue
        patch = item.diff.decode("utf-8", errors="replace") if isinstance(item.diff, bytes) else (item.diff or "")
        for start, end in _removed_ranges(patch):
            try:
                output = repo.git.blame("-l", "-s", f"-L{start},{end}", parent.hexsha, "--", path)
            except GitCommandError:
                continue
            for line in output.splitlines():
                token = line.split(" ", 1)[0]
                if re.fullmatch(r"[0-9a-f]{40}", token):
                    found.add(token)
    return found


def label_commits(repo: Repo, commit_hashes: list[str], fix_hashes: list[str]) -> dict[str, dict]:
    """返回 {commit_hash: {"is_bug_inducing": 0/1, "fix_commit_hash": str|None}}。"""
    sample = set(commit_hashes)
    labels = {h: {"is_bug_inducing": 0, "fix_commit_hash": None} for h in commit_hashes}
    for fix in fix_hashes:
        for introduced in introducing_commits(repo, fix):
            if introduced in sample and labels[introduced]["is_bug_inducing"] == 0:
                labels[introduced] = {"is_bug_inducing": 1, "fix_commit_hash": fix}
    return labels
