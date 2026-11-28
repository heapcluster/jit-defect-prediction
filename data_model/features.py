"""Kamei 14 维专家特征：严格只使用当前提交之前、同一分支内的历史。"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta

from git import Repo
from git.exc import GitCommandError

from data_model import gitops

FIX_KEYWORDS = ("fix", "fixes", "fixed", "bug", "bugs", "repair", "resolve", "close")


def _is_fix(message: str) -> int:
    lowered = (message or "").lower()
    return 1 if any(word in lowered for word in FIX_KEYWORDS) else 0


def _subsystem(path: str) -> str:
    parts = path.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else "(root)"


def _entropy(weights: list[int]) -> float:
    total = sum(weights)
    if total <= 0:
        return 0.0
    value = 0.0
    for weight in weights:
        if weight > 0:
            p = weight / total
            value -= p * math.log2(p)
    return value


class _History:
    def __init__(self) -> None:
        self.author_counts: dict[str, int] = defaultdict(int)
        self.author_recent: list[tuple[datetime, str]] = []
        self.file_authors: dict[str, set[str]] = defaultdict(set)
        self.file_count: dict[str, int] = defaultdict(int)
        self.file_last: dict[str, datetime] = {}
        self.subsystem_author: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def recent_count(self, author: str, when: datetime, days: int = 90) -> int:
        since = when - timedelta(days=days)
        return sum(1 for ts, name in self.author_recent if name == author and ts >= since)

    def update(self, commit, files: list[str], subsystems: set[str]) -> None:
        when = gitops.local_datetime(commit.committed_datetime)
        author = commit.author.email or commit.author.name or ""
        self.author_counts[author] += 1
        self.author_recent.append((when, author))
        for path in files:
            self.file_authors[path].add(author)
            self.file_count[path] += 1
            self.file_last[path] = when
        for subsystem in subsystems:
            self.subsystem_author[subsystem][author] += 1


def _features_from_state(commit, history: _History) -> dict:
    stats = gitops.file_diff_stats(commit)
    files = list(stats.keys())
    subsystems = {_subsystem(path) for path in files}
    dirs = {str(("/".join(path.replace("\\", "/").split("/")[:-1]))) for path in files}
    when = gitops.local_datetime(commit.committed_datetime)
    author = commit.author.email or commit.author.name or ""

    la = sum(v[0] for v in stats.values())
    ld = sum(v[1] for v in stats.values())
    lt = sum(v[2] for v in stats.values())
    entropy = _entropy([v[0] + v[1] for v in stats.values()])

    ndev_values, age_values, nuc_values = [], [], []
    for path in files:
        ndev_values.append(len(history.file_authors.get(path, set())))
        last = history.file_last.get(path)
        age_values.append(max((when - last).total_seconds() / 86400.0, 0.0) if last else 0.0)
        nuc_values.append(history.file_count.get(path, 0))

    def avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    return {
        "ns": float(len(subsystems)),
        "nd": float(len(dirs)),
        "nf": float(len(files)),
        "entropy": round(entropy, 4),
        "la": float(la),
        "ld": float(ld),
        "lt": float(lt),
        "fix": _is_fix(commit.message),
        "ndev": avg(ndev_values),
        "age": round(avg(age_values), 4),
        "nuc": avg(nuc_values),
        "exp": float(history.author_counts.get(author, 0)),
        "rexp": float(history.recent_count(author, when)),
        "sexp": float(sum(history.subsystem_author[s].get(author, 0) for s in subsystems)),
    }


def compute_features_batch(repo: Repo, commits: list) -> dict[str, dict]:
    """按时间升序批量计算；返回 commit_hash → 14 维特征。"""
    history = _History()
    result: dict[str, dict] = {}
    for commit in commits:
        stats = gitops.file_diff_stats(commit)
        files = list(stats.keys())
        subsystems = {_subsystem(path) for path in files}
        result[commit.hexsha] = _features_from_state(commit, history)
        history.update(commit, files, subsystems)
    return result


def compute_features(repo: Repo, commit_hash: str) -> dict:
    commit = repo.commit(commit_hash)
    ancestors = list(reversed(list(repo.iter_commits(rev=commit_hash, no_merges=True))))
    history = _History()
    for item in ancestors:
        stats = gitops.file_diff_stats(item)
        files = list(stats.keys())
        subsystems = {_subsystem(path) for path in files}
        if item.hexsha == commit.hexsha:
            break
        history.update(item, files, subsystems)
    return _features_from_state(commit, history)


def feature_vector(features: dict) -> list[float]:
    from backend.app.constants import EXPERT_FEATURES

    return [float(features.get(name, 0.0) or 0.0) for name in EXPERT_FEATURES]
