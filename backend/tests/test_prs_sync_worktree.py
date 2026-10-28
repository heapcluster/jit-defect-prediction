"""PR 历史可达性与临时 worktree 释放的单元和本地 Git 集成测试。"""

from __future__ import annotations

import subprocess

import pytest
from app import config, feature_source, model_registry
from app.api import prs
from app.db import SessionLocal
from app.errors import AppError
from app.models import Commit, CommitFeature, Prediction


class Pr:
    def __init__(self, number: int, title: str = "t"):
        self.number = number
        self.title = title


@pytest.fixture
def harness(monkeypatch, tmp_path):
    """把 sync_prs 的四个外部依赖换成探针。"""
    repo = tmp_path / "camel"
    (repo / ".git").mkdir(parents=True)
    calls: dict[str, list] = {"predict": [], "fetch": [], "worktree": [], "release": []}

    monkeypatch.setattr(prs, "_repo_path", lambda: repo)
    monkeypatch.setattr(prs.github, "list_open_prs", lambda limit=10: [Pr(101), Pr(202)])
    monkeypatch.setattr(prs.github, "list_pr_commit_shas", lambda n: [f"{n}-sha1", f"{n}-sha2"])

    def fake_fetch(_repo, number):
        calls["fetch"].append(number)
        if number == 202:
            raise AppError(50000, "internal error")
        return f"head-{number}"

    def fake_ensure(_repo, tip):
        calls["worktree"].append(tip)
        wt = f"/tmp/wt-{tip}"

        def _release():
            calls["release"].append(tip)

        return wt, _release

    def fake_predict(sha, repo=None):
        calls["predict"].append((sha, repo))

    monkeypatch.setattr(prs, "fetch_pr_ref", fake_fetch)
    monkeypatch.setattr(prs, "ensure_extractable", fake_ensure)
    monkeypatch.setattr(prs, "predict_commit_all_models", fake_predict)
    return calls, str(repo)


def test_pr_commits_are_extracted_from_a_temporary_worktree(harness):
    calls, repo_path = harness
    out = prs.sync_prs(limit=2)

    assert calls["worktree"] == ["head-101"], "只为真正要处理的 PR 建 worktree"
    assert [c[1] for c in calls["predict"]] == ["/tmp/wt-head-101"] * 2, (
        "抽取用的仓库必须是该 PR 历史可达的 worktree；传 SOURCE_REPO 会让 PR 提交全部算不出来"
    )
    assert all(repo != repo_path for _s, repo in calls["predict"]), "不得退回 SOURCE_REPO 本体"
    assert out["prs"][0]["commits_predicted"] == 2
    assert out["commits_predicted"] == 2


def test_worktree_is_released_even_when_prediction_fails(harness, monkeypatch):
    calls, _repo_path = harness

    def boom(_sha, repo=None):
        calls["predict"].append((_sha, repo))
        raise AppError(40400, "commit not found")

    monkeypatch.setattr(prs, "predict_commit_all_models", boom)
    out = prs.sync_prs(limit=2)

    assert calls["release"] == ["head-101"], "临时 worktree 必须用后即焚（失败路径也要释放）"
    assert out["commits_predicted"] == 0
    assert [s["code"] for s in out["skipped"] if "commit" in s] == [40400, 40400]


def test_one_failing_pr_does_not_abort_the_batch(harness):
    """PR 202 fetch 失败 → 记 skipped，PR 101 照常处理完。"""
    calls, _repo_path = harness
    out = prs.sync_prs(limit=2)

    assert out["prs_scanned"] == 2
    assert [p["pr"] for p in out["prs"]] == [101], "失败的 PR 不进结果列表"
    assert any("fetch failed" in str(s.get("reason")) for s in out["skipped"])
    assert calls["release"] == ["head-101"]


def test_worktree_creation_failure_is_skipped_without_release(harness, monkeypatch):
    calls, _repo_path = harness

    def fail(_repo, tip):
        raise AppError(50000, "internal error")

    monkeypatch.setattr(prs, "ensure_extractable", fail)
    out = prs.sync_prs(limit=2)

    assert calls["release"] == [], "没建成就不该释放"
    assert calls["predict"] == []
    assert any("worktree failed" in str(s.get("reason")) for s in out["skipped"])


def test_limit_still_validated_before_touching_git(harness):
    calls, _repo_path = harness
    with pytest.raises(AppError) as exc:
        prs.sync_prs(limit=0)
    assert exc.value.code == 40001
    assert calls["fetch"] == []


def test_pr_branch_extracts_and_persists_without_changing_source(client, monkeypatch, tmp_path):
    repo = tmp_path / "source"
    repo.mkdir()
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "Test Author")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.com")

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        ).stdout.strip()

    git("init", "-b", "main")
    source = repo / "example.txt"
    source.write_text("base\n", encoding="utf-8")
    git("add", "example.txt")
    git("commit", "-m", "base")
    git("switch", "-c", "pr")
    source.write_text("base\nnew line\n", encoding="utf-8")
    git("add", "example.txt")
    git("commit", "-m", "change")
    head = git("rev-parse", "HEAD")
    git("switch", "main")
    source.write_text("uncommitted local work\n", encoding="utf-8")
    before = (
        git("rev-parse", "HEAD"),
        git("status", "--porcelain"),
        git("worktree", "list", "--porcelain"),
    )

    with pytest.raises(ValueError, match="HEAD"):
        feature_source.extract(head, repo=repo)
    monkeypatch.setattr(config, "SOURCE_REPO", repo)
    monkeypatch.setattr(prs.github, "list_open_prs", lambda limit: [Pr(101)])
    monkeypatch.setattr(prs.github, "list_pr_commit_shas", lambda number: [head])
    monkeypatch.setattr(prs, "fetch_pr_ref", lambda repo, number: head)

    out = prs.sync_prs(limit=1)

    assert out["commits_predicted"] == 1 and out["skipped"] == []
    with SessionLocal() as session:
        assert session.query(Commit).filter_by(commit_hash=head).count() == 1
        assert session.query(CommitFeature).filter_by(commit_hash=head).count() == 1
        rows = session.query(Prediction).filter_by(commit_hash=head).all()
        assert {row.model_name for row in rows} == {
            entry.name for entry in model_registry.all_models()
        }
    assert (
        git("rev-parse", "HEAD"),
        git("status", "--porcelain"),
        git("worktree", "list", "--porcelain"),
    ) == before
    assert source.read_text(encoding="utf-8") == "uncommitted local work\n"
