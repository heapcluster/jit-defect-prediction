# === AI 辅助说明 ===
# 本文件共 4 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：4 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

"""单条 v1 特征与批量口径一致，且不依赖预生成 CSV。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "preparation" / "03_extract_features.py"
SPEC = importlib.util.spec_from_file_location("extract_features", SCRIPT)
assert SPEC and SPEC.loader
extract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extract)


def _git(repo: Path, *args: str, when: str | None = None) -> str:
    env = os.environ.copy()
    if when:
        env.update(GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    ).stdout.strip()


@pytest.fixture()
def tiny_repo(tmp_path: Path) -> tuple[Path, list[str]]:
    repo = tmp_path / "sample"
    repo.mkdir()
    _git(repo, "init")
    hashes = []
    target = repo / "src" / "a.txt"
    target.parent.mkdir()
    for day, content, message in (
        ("01", "one\n", "initial"),
        ("02", "one\ntwo\n", "CAMEL-123 fix issue"),
        ("03", "one\ntwo\nthree\n", "extend"),
    ):
        target.write_text(content, encoding="utf-8")
        _git(repo, "add", ".")
        _git(
            repo,
            "-c",
            "user.name=Example",
            "-c",
            "user.email=test@example.org",
            "commit",
            "-m",
            message,
            when=f"2026-01-{day}T12:00:00+0000",
        )
        hashes.append(_git(repo, "rev-parse", "HEAD"))
    return repo, hashes


def test_single_matches_batch_v1(tiny_repo):
    repo, hashes = tiny_repo
    history = extract.scan_history(repo)
    targets = []
    for commit_hash in hashes:
        one = extract.extract_single_commit(repo, commit_hash)
        assert one["commit_hash"] == commit_hash
        assert one["feature_version"] == "v1"
        assert list(one["features"]) == extract.FEATURE_FIELDS
        assert one["vector"] == list(one["features"].values())
        targets.append(one)
    rows = extract.apply_contract(
        extract.compute_raw(
            targets,
            history,
            extract.HistoryIndex(history),
            extract.load_is_fix_commit(),
            repo,
            progress_every=0,
            verbose=False,
        )
    )
    for one, batch in zip(targets, rows, strict=True):
        assert one["features"] == {name: batch[name] for name in extract.FEATURE_FIELDS}
    assert targets[1]["features"]["fix"] == 1
    assert targets[0]["features"]["exp"] == 0


def test_cli_emits_json_without_batch_files(tiny_repo):
    repo, hashes = tiny_repo
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--commit", hashes[-1]],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert json.loads(result.stdout)["commit_hash"] == hashes[-1]
    assert not (repo / "commit_features.csv").exists()


def test_rejects_bad_or_unreachable_commit(tiny_repo):
    repo, _ = tiny_repo
    with pytest.raises(ValueError, match="40 位"):
        extract.extract_single_commit(repo, "bad")
    with pytest.raises(ValueError, match="HEAD 可达"):
        extract.extract_single_commit(repo, "f" * 40)


def test_extract_commits_matches_single(tiny_repo):
    """批量抽取与逐条抽取结果必须逐字段一致（同步提速的前提）。"""
    repo, hashes = tiny_repo
    batch = extract.extract_commits(repo, hashes)
    singles = [extract.extract_single_commit(repo, commit_hash) for commit_hash in hashes]
    assert batch == singles
