"""Camel 源切换的本地 Git 集成烟雾测试；不依赖真实全量数据。"""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from git import Actor, Repo


def load_script(name):
    """01/02 moved into the preparation/ package during the four-line split;
    resolve against that directory, not the data_model root."""
    root = Path(__file__).resolve().parents[1]
    path = root / name
    if not path.is_file():
        path = root / "preparation" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collection_and_both_szz_methods_on_local_git(tmp_path, monkeypatch):
    repo_dir = tmp_path / "camel"
    repo = Repo.init(repo_dir)
    actor = Actor("Fixture", "fixture@example.invalid")
    source = repo_dir / "Example.java"
    source.write_text("class Example { int value = 0; }\n", encoding="utf-8")
    repo.index.add(["Example.java"])
    introducing = repo.index.commit(
        "CAMEL-1 add example", author=actor, committer=actor,
        author_date="2026-01-01T00:00:00+0000", commit_date="2026-01-01T00:00:00+0000",
    )
    source.write_text("class Example { int value = 1; }\n", encoding="utf-8")
    repo.index.add(["Example.java"])
    fixing = repo.index.commit(
        "CAMEL-2 fix incorrect value", author=actor, committer=actor,
        author_date="2026-01-02T00:00:00+0000", commit_date="2026-01-02T00:00:00+0000",
    )
    extract = load_script("01_extract_commits.py")
    out = tmp_path / "commits.csv"
    monkeypatch.setattr(extract, "parse_args", lambda: SimpleNamespace(
        repo=repo_dir, out=out, since=None, allow_head_mismatch=False,
    ))
    monkeypatch.setattr(extract, "REPORTS_DIR", tmp_path / "reports")

    # 生产固定提交不匹配：必须在写 CSV 前拦截。
    assert extract.main() == 3
    assert not out.exists()

    # 仅在本测试中把基准设为合成仓库，实测采集 → 两套 git 回溯。
    monkeypatch.setattr(extract, "EXPECTED_HEAD", fixing.hexsha)
    assert extract.main() == 0
    with out.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["repo_name"] for r in rows] == ["camel", "camel"]
    assert [r["commit_hash"] for r in rows] == [introducing.hexsha, fixing.hexsha]
    assert rows[0]["parent_hash"] == ""
    assert rows[1]["parent_hash"] == introducing.hexsha

    szz = load_script("02_szz_labeling.py")
    fixes = [r for r in rows if szz.is_fix_commit(r["message"])]
    assert [r["commit_hash"] for r in fixes] == [fixing.hexsha]
    for method in szz.METHODS:
        result = szz.run_method(method, repo_dir, rows, fixes, 0)
        assert introducing.hexsha in result["labels"]
        assert result["pos"] == 1
    repo.close()
