"""Git 仓库操作：克隆缓存、分支、提交遍历、diff、blame。"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOS_DIR = REPO_ROOT / "temp" / "repos"

_GITHUB = re.compile(r"github\.com/([^/]+)/([^/.]+)")
_GITEE = re.compile(r"gitee\.com/([^/]+)/([^/.]+)")


def parse_repo_url(url: str) -> dict:
    raw = (url or "").strip()
    if not raw:
        raise ValueError("仓库地址为空")
    if raw.endswith(".git"):
        raw = raw[:-4]
    raw = raw.rstrip("/")
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").lower()
    if host not in ("github.com", "gitee.com"):
        raise ValueError("仅支持 github.com / gitee.com 的公开仓库")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("仓库地址格式无法归一化")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    platform = "github" if host == "github.com" else "gitee"
    return {
        "platform": platform,
        "owner": owner,
        "repo": repo,
        "repo_name": f"{owner}/{repo}",
        "repo_url": f"https://{host}/{owner}/{repo}",
        "clone_url": f"https://{host}/{owner}/{repo}.git",
    }


def cache_dir(info: dict) -> Path:
    name = f"{info['platform']}-{info['owner']}-{info['repo']}".lower()
    return REPOS_DIR / name


def ensure_repo(info: dict, update: bool = True) -> Repo:
    path = cache_dir(info)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        Repo.clone_from(info["clone_url"], path, no_single_branch=True)
        return Repo(path)
    try:
        repo = Repo(path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        shutil.rmtree(path, ignore_errors=True)
        Repo.clone_from(info["clone_url"], path, no_single_branch=True)
        return Repo(path)
    if update:
        try:
            repo.git.fetch("--all", "--tags", "--prune")
        except GitCommandError:
            pass
    return repo


def list_branches(repo: Repo) -> tuple[str, list[str]]:
    remote = repo.remotes.origin if repo.remotes else None
    branches = []
    if remote:
        for ref in remote.refs:
            name = ref.remote_head
            if name and name != "HEAD":
                branches.append(name)
    if not branches:
        branches = [head.name for head in repo.heads]
    branches = sorted(set(branches))
    try:
        default = repo.git.symbolic_ref("refs/remotes/origin/HEAD").split("/")[-1]
    except GitCommandError:
        default = branches[0] if branches else "main"
    return default, branches


def local_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


def iter_commits(repo: Repo, branch: str, limit: int | None = None) -> list:
    rev = branch if branch in [h.name for h in repo.heads] else f"origin/{branch}"
    try:
        commits = list(repo.iter_commits(rev=rev, max_count=limit, no_merges=True))
    except GitCommandError:
        commits = list(repo.iter_commits(max_count=limit, no_merges=True))
    if commits:
        commits = commits[:-1]  # 排除分支根提交
    return list(reversed(commits))  # 时间升序


def commit_meta(commit) -> dict:
    return {
        "commit_hash": commit.hexsha,
        "parent_hash": commit.parents[0].hexsha if commit.parents else None,
        "author_name": commit.author.name or "",
        "author_email": commit.author.email or "",
        "committed_at": local_datetime(commit.committed_datetime),
        "message": commit.message.strip(),
    }


def changed_files(commit) -> list[str]:
    if not commit.parents:
        return []
    try:
        diff = commit.parents[0].diff(commit, create_patch=False)
    except GitCommandError:
        return []
    return [item.b_path or item.a_path for item in diff if (item.b_path or item.a_path)]


def file_diff_stats(commit) -> dict[str, tuple[int, int, int]]:
    """每个文件 (新增行, 删除行, 修改前行数)。"""
    if not commit.parents:
        return {}
    stats: dict[str, tuple[int, int, int]] = {}
    try:
        diff = commit.parents[0].diff(commit, create_patch=True)
    except GitCommandError:
        return stats
    for item in diff:
        path = item.b_path or item.a_path
        if not path:
            continue
        patch = item.diff.decode("utf-8", errors="replace") if isinstance(item.diff, bytes) else (item.diff or "")
        added = sum(1 for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
        deleted = sum(1 for line in patch.splitlines() if line.startswith("-") and not line.startswith("---"))
        old_total = 0
        if commit.parents and path:
            try:
                blob = commit.parents[0].tree / path
                content = blob.data_stream.read().decode("utf-8", errors="replace")
                old_total = content.count("\n") + (0 if content.endswith("\n") else 1)
            except (KeyError, AttributeError):
                old_total = 0
        stats[path] = (added, deleted, old_total)
    return stats


def history_for_path(repo: Repo, rev: str, path: str) -> list:
    try:
        return list(repo.iter_commits(rev=rev, paths=path))
    except GitCommandError:
        return []


def blame_lines(repo: Repo, rev: str, path: str, line_ranges: list[tuple[int, int]]) -> set[str]:
    hashes: set[str] = set()
    for start, end in line_ranges:
        try:
            output = repo.git.blame("-l", "-s", f"-L{start},{end}", rev, "--", path)
        except GitCommandError:
            continue
        for line in output.splitlines():
            token = line.split(" ", 1)[0]
            if re.fullmatch(r"[0-9a-f]{40}", token):
                hashes.add(token)
    return hashes


def diff_hunks(commit) -> dict[str, list[dict]]:
    """解析提交 diff 为按文件分组的行记录。"""
    if not commit.parents:
        return {}
    result: dict[str, list[dict]] = {}
    try:
        diff = commit.parents[0].diff(commit, create_patch=True)
    except GitCommandError:
        return result
    for item in diff:
        path = item.b_path or item.a_path
        if not path:
            continue
        patch = item.diff.decode("utf-8", errors="replace") if isinstance(item.diff, bytes) else (item.diff or "")
        old_no = new_no = 0
        lines: list[dict] = []
        for raw in patch.splitlines():
            header = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if header:
                old_no, new_no = int(header.group(1)), int(header.group(2))
                continue
            if raw.startswith("+++") or raw.startswith("---"):
                continue
            if raw.startswith("+"):
                lines.append({"no": new_no, "type": "added", "content": raw[1:]})
                new_no += 1
            elif raw.startswith("-"):
                lines.append({"no": old_no, "type": "removed", "content": raw[1:]})
                old_no += 1
            else:
                lines.append({"no": new_no, "type": "context", "content": raw[1:] if raw.startswith(" ") else raw})
                old_no += 1
                new_no += 1
        result[path] = lines
    return result


def recent_commit_count(commits: list, since: datetime, until: datetime) -> int:
    return sum(1 for c in commits if since <= local_datetime(c.committed_datetime) <= until)
