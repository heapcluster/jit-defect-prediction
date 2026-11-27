# === AI 辅助说明 ===
# 本文件共 1 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：1 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/README.md

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
        "CAMEL-1 add example",
        author=actor,
        committer=actor,
        author_date="2026-01-01T00:00:00+0000",
        commit_date="2026-01-01T00:00:00+0000",
    )
    source.write_text("class Example { int value = 1; }\n", encoding="utf-8")
    repo.index.add(["Example.java"])
    fixing = repo.index.commit(
        "CAMEL-2 fix incorrect value",
        author=actor,
        committer=actor,
        author_date="2026-01-02T00:00:00+0000",
        commit_date="2026-01-02T00:00:00+0000",
    )
    extract = load_script("01_extract_commits.py")
    out = tmp_path / "commits.csv"
    monkeypatch.setattr(
        extract,
        "parse_args",
        lambda: SimpleNamespace(
            repo=repo_dir,
            out=out,
            since=None,
            allow_head_mismatch=False,
        ),
    )
    monkeypatch.setattr(extract, "REPORTS_DIR", tmp_path / "reports")

    # 新契约按 source_url / repo_name 采集，不再校验固定仓库 HEAD；本地合成仓库可直接采集。
    assert extract.main() == 0
    assert out.exists()
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
