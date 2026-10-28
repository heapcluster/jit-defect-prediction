"""PR 同步必须让该 PR 的历史对抽取器可达（改动前：拿 SOURCE_REPO 直接算，必算不出来）。

回归点：`sync_prs` 原先把 `repo=str(SOURCE_REPO)` 交给 `predict_commit_all_models`，而特征
抽取器的历史扫描是 `git log … HEAD`（`data_model/preparation/03_extract_features.py`）；
PR 的提交只被 `git fetch origin pull/<n>/head` 取进对象库、**不在默认分支 HEAD 的历史上**，
于是每条 sha 都算不出来 —— 表现为接口返回 200、`commits_predicted=0`、
`GET /api/prs` 整表 `risk_score=null`（本机实测：该端点 67s、全表 null）。

本文件是纯单元测试，不连数据库也不起服务（因此不依赖 MySQL 测试库 jit_test）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.api import prs
from app.errors import AppError


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


def test_repo_path_is_a_path_object_for_production_callers():
    """_repo_path 的返回类型是 Path；ensure_extractable 收的是 str，别把 Path 直接喂进去。"""
    src = Path(prs.__file__).read_text(encoding="utf-8")
    assert "ensure_extractable(str(repo)" in src, "worktree 入口仍按 str 传仓库路径"
