"""POST /api/sync 批量同步测试（change realtime-commit-sync）。

覆盖审阅固化的三条边界：
1. 只读 SOURCE_REPO：tip 非 HEAD 祖先时走专用临时工作树，用户检出状态不变；
2. 「待预测」按默认模型是否已有 prediction 行判断（commit 已存在 ≠ 已预测）；
3. git 失败映射契约内 50000、无新提交幂等、并发互斥。
"""

from __future__ import annotations

import subprocess

import pytest
from app import feature_source
from app.api import sync as sync_module
from app.db import SessionLocal
from app.errors import AppError
from app.models import Prediction

from tests.conftest import C3, HEADERS, UNKNOWN


def test_pick_hashes_to_predict_skips_already_predicted():
    hashes = [UNKNOWN, C3, "e" * 40]
    predicted = {C3}
    assert sync_module.pick_hashes_to_predict(hashes, predicted) == [UNKNOWN, "e" * 40]
    assert sync_module.pick_hashes_to_predict([], set()) == []
    # 全部已预测 → 空（幂等）
    assert sync_module.pick_hashes_to_predict(hashes, set(hashes)) == []


def test_build_fetch_args_disables_proxy():
    assert sync_module.build_fetch_args() == ["fetch", "origin", "HEAD"]


def test_git_failure_maps_to_50000(monkeypatch, tmp_path):
    """git 子进程失败/超时映射为契约内 50000，不裸抛 RuntimeError。"""
    calls = {"n": 0}

    def _fail(*_a, **_k):
        calls["n"] += 1
        raise subprocess.TimeoutExpired(cmd="git", timeout=180)

    monkeypatch.setattr(sync_module.subprocess, "run", _fail)
    with pytest.raises(AppError) as exc:
        sync_module.fetch_latest_tip(str(tmp_path), retries=2)
    assert exc.value.code == 50000
    assert calls["n"] == 2  # 重试次数生效


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@e.com", "-c", "user.name=t", *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def _init_repo_with_two_commits(tmp_path):
    repo = tmp_path / "src"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "a.txt").write_text("a", encoding="utf-8")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "first")
    first = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    (repo / "b.txt").write_text("b", encoding="utf-8")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-qm", "second")
    second = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return repo, first, second


def test_ensure_extractable_uses_repo_when_tip_is_head_reachable(tmp_path):
    repo, _first, second = _init_repo_with_two_commits(tmp_path)
    extract_repo, release = sync_module.ensure_extractable(str(repo), second)
    # 返回值收窄为 Path（feature_source 统一吃 Path，str 会在路径拼接处炸 str/str）
    assert str(extract_repo) == str(repo)
    release()  # 空操作，不报错
    # HEAD 未被改动
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head == second


def test_ensure_extractable_uses_temp_worktree_without_touching_checkout(tmp_path):
    """tip 不是 HEAD 祖先：建专用工作树；HEAD 与工作区不变，用后即焚。"""
    repo, first, second = _init_repo_with_two_commits(tmp_path)
    _git(repo, "checkout", "-q", "--detach", first)  # HEAD 退到 first
    head_before = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head_before == first

    extract_repo, release = sync_module.ensure_extractable(str(repo), second)
    try:
        assert extract_repo != str(repo)
        # 工作树的 HEAD 就是 tip
        wt_head = subprocess.run(
            ["git", "-C", extract_repo, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert wt_head == second
    finally:
        release()

    # 释放后：工作树目录没了、git worktree 列表回到 1 个、原仓库 HEAD 未动
    import os

    assert not os.path.exists(extract_repo)
    listed = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list"], capture_output=True, text=True, check=True
    ).stdout
    assert listed.count("\n") == 1
    head_after = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert head_after == first


def _stub_extract(monkeypatch):
    monkeypatch.setattr(
        feature_source,
        "extract",
        lambda h, repo=None: {
            "repo_name": "camel",
            "author_name": "tester",
            "author_email": "t@example.com",
            "committed_at": "2026-10-25T10:00:00",
            "message": "sync test commit",
            "parent_hash": None,
            "feature_version": "test-v1",
            "features": {
                "ns": 1.0,
                "nd": 1.0,
                "nf": 1.0,
                "entropy": 1.0,
                "la": 1.0,
                "ld": 1.0,
                "lt": 1.0,
                "fix": 0,
                "ndev": 1.0,
                "age": 1.0,
                "nuc": 1.0,
                "exp": 1.0,
                "rexp": 1.0,
                "sexp": 1.0,
            },
        },
    )


def test_sync_predicts_existing_commit_without_prediction(client, monkeypatch, tmp_path):
    """C3 在 commit 表已有行但无 prediction：sync 必须补预测，且统一落全部模型（startup-baseline-sync）。"""
    repo = tmp_path / "camel3"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)

    hashes = [UNKNOWN, C3, "e" * 40]
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: hashes[0])
    monkeypatch.setattr(sync_module, "list_recent_hashes", lambda repo_dir, limit: hashes[:limit])
    monkeypatch.setattr(
        sync_module, "ensure_extractable", lambda repo_dir, tip: (repo_dir, lambda: None)
    )
    _stub_extract(monkeypatch)

    resp = client.post("/api/sync?limit=3", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["new"] == 3  # 三条 commit 都无 prediction 行
    assert {r["commit_hash"] for r in body["data"]["predicted"]} == set(hashes)
    # 全模型落库：每个 commit 在 prediction 表各注册模型各一行
    with SessionLocal() as session:
        rows = session.query(Prediction).filter(Prediction.commit_hash == C3).all()
        assert {r.model_name for r in rows} == {"fixture_v1", "fixture_v2"}

    # 二次调用：三条都已有 prediction → new=0（幂等）
    second = client.post("/api/sync?limit=3", headers=HEADERS)
    assert second.status_code == 200
    assert second.json()["data"]["new"] == 0
    assert second.json()["data"]["predicted"] == []


def test_sync_requires_source_repo(monkeypatch):
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", None)
    with pytest.raises(AppError) as exc:
        sync_module.sync_recent(limit=5)
    assert exc.value.code == 40400


def test_sync_limit_out_of_range():
    with pytest.raises(AppError) as exc:
        sync_module.sync_recent(limit=0)
    assert exc.value.code == 40001
    with pytest.raises(AppError) as exc2:
        sync_module.sync_recent(limit=sync_module.MAX_LIMIT + 1)
    assert exc2.value.code == 40001


def test_sync_endpoint_unreachable_commit_counts_as_skipped(client, monkeypatch, tmp_path):
    """提取器抛 ValueError（提交不可达）→ 单条计入 skipped（40400），整批不 500。"""
    repo = tmp_path / "camel2"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)

    hashes = [UNKNOWN]
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: hashes[0])
    monkeypatch.setattr(sync_module, "list_recent_hashes", lambda repo_dir, limit: hashes)
    monkeypatch.setattr(
        sync_module, "ensure_extractable", lambda repo_dir, tip: (repo_dir, lambda: None)
    )

    def _boom(_hash: str, repo=None):
        raise ValueError("目标不是当前 HEAD 可达的非合并提交")

    monkeypatch.setattr(feature_source, "extract", _boom)
    resp = client.post("/api/sync?limit=1", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["predicted"] == []
    assert len(body["data"]["skipped"]) == 1
    assert body["data"]["skipped"][0]["code"] == 40400


def test_sync_concurrent_calls_rejected(monkeypatch):
    """持锁期间再次进入 → 50000（不排队、不并发操作同一仓库）。"""
    assert sync_module._sync_lock.acquire(blocking=False)
    try:
        with pytest.raises(AppError) as exc:
            sync_module.sync_recent(limit=1)
        assert exc.value.code == 50000
    finally:
        sync_module._sync_lock.release()


def test_catchup_predicts_uncovered_commits(client, monkeypatch, tmp_path):
    """catchup 补齐 DB 有而 git 无 prediction 的 commit，且统一落全部模型（startup-baseline-sync）。"""
    repo = tmp_path / "camel4"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)

    hashes = [UNKNOWN, C3, "e" * 40]
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: hashes[0])
    monkeypatch.setattr(sync_module, "list_all_hashes", lambda repo_dir, ref="FETCH_HEAD": hashes)
    monkeypatch.setattr(
        sync_module, "ensure_extractable", lambda repo_dir, tip: (repo_dir, lambda: None)
    )
    _stub_extract(monkeypatch)

    resp = client.post("/api/sync/catchup", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["new"] == 3  # 三条 commit 在 DB 均无 prediction 行
    with SessionLocal() as session:
        rows = session.query(Prediction).filter(Prediction.commit_hash == C3).all()
        assert {r.model_name for r in rows} == {"fixture_v1", "fixture_v2"}


def test_sync_status_reports_idle_and_after_catchup(client, monkeypatch, tmp_path):
    """status 快照：空闲 running=false；catchup 结束后状态复原且 mode=catchup。"""
    idle = client.get("/api/sync/status", headers=HEADERS)
    assert idle.status_code == 200
    assert idle.json()["data"]["running"] is False

    repo = tmp_path / "camel5"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: UNKNOWN)
    monkeypatch.setattr(
        sync_module, "list_all_hashes", lambda repo_dir, ref="FETCH_HEAD": [UNKNOWN]
    )
    monkeypatch.setattr(
        sync_module, "ensure_extractable", lambda repo_dir, tip: (repo_dir, lambda: None)
    )
    _stub_extract(monkeypatch)
    resp = client.post("/api/sync/catchup", headers=HEADERS)
    assert resp.status_code == 200
    after = client.get("/api/sync/status", headers=HEADERS).json()["data"]
    assert after["running"] is False
    assert after["mode"] == "catchup"
