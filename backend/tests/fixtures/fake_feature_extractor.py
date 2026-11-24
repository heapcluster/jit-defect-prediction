"""CLI 子进程可加载的确定性特征抽取器。

与 conftest 的内存 mock 共用 `_fake_features`，保证 API（进程内 mock）与 CLI
（子进程外挂抽取器）对同一假提交得到逐位相同的 14 维向量，用于 parity 验收。
真实抽取器见 data_model/preparation/03_extract_features.py。
"""

from __future__ import annotations

import numpy as np

FEATURE_COLUMNS = (
    "ns",
    "nd",
    "nf",
    "entropy",
    "la",
    "ld",
    "lt",
    "fix",
    "ndev",
    "age",
    "nuc",
    "exp",
    "rexp",
    "sexp",
)
FEATURE_VALUES = {name: 0.0 for name in FEATURE_COLUMNS}


def _fake_features(commit_hash: str) -> dict[str, float]:
    seed = int(commit_hash[:8], 16) if all(c in "0123456789abcdef" for c in commit_hash[:8]) else 7
    rng = np.random.RandomState(seed)
    values = {name: float(rng.rand()) for name in FEATURE_COLUMNS}
    values["fix"] = float(seed % 2)
    return values


def extract_single_commit(repo_dir, commit_hash: str) -> dict:
    values = _fake_features(commit_hash)
    return {
        "commit_hash": commit_hash,
        "repo_name": "fixture",
        "author_name": "jdoe",
        "author_email": "",
        "committed_at": "2026-01-01T00:00:00Z",
        "message": "fixture",
        "parent_hash": None,
        "feature_version": "v1",
        "features": values,
        "vector": [values[name] for name in FEATURE_COLUMNS],
    }


def extract_commits(repo_dir, commit_hashes, skip_missing=False) -> list[dict]:
    return [{"commit_hash": h, **_fake_features(h)} for h in commit_hashes]
