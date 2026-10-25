"""POST /api/sync 批量同步测试：挑新逻辑、幂等、错误码边界（change realtime-commit-sync）。"""

from __future__ import annotations

import subprocess

import pytest

from app.api import sync as sync_module
from app.errors import AppError
from tests.conftest import C1, C2, C3, HEADERS, UNKNOWN


def test_pick_new_hashes_keeps_order_and_skips_existing():
    hashes = [C3, C1, UNKNOWN, C2]
    existing = {C1, C2}
    assert sync_module.pick_new_hashes(hashes, existing) == [C3, UNKNOWN]
    assert sync_module.pick_new_hashes([], set()) == []


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


def _stub_extract(monkeypatch):
    monkeypatch.setattr(
        sync_module.feature_source, "extract",
        lambda h: {
            "repo_name": "camel",
            "author_name": "tester",
            "author_email": "t@example.com",
            "committed_at": "2026-10-25T10:00:00",
            "message": "sync test commit",
            "parent_hash": None,
            "feature_version": "test-v1",
            "features": {
                "ns": 1.0, "nd": 1.0, "nf": 1.0, "entropy": 1.0,
                "la": 1.0, "ld": 1.0, "lt": 1.0, "fix": 0,
                "ndev": 1.0, "age": 1.0, "nuc": 1.0,
                "exp": 1.0, "rexp": 1.0, "sexp": 1.0,
            },
        },
    )


def test_sync_endpoint_end_to_end_idempotent(client, monkeypatch, tmp_path):
    """git fetch/extract 全部打桩：新提交被预测入库，二次调用幂等返回 0 新。"""
    repo = tmp_path / "camel"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)

    hashes = [UNKNOWN, "e" * 40]
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: hashes[0])
    monkeypatch.setattr(sync_module, "ensure_reachable", lambda repo_dir, tip: None)
    monkeypatch.setattr(sync_module, "list_recent_hashes", lambda repo_dir, limit: hashes[:limit])
    _stub_extract(monkeypatch)

    first = client.post("/api/sync?limit=2", headers=HEADERS)
    assert first.status_code == 200
    body = first.json()
    assert body["code"] == 0
    assert body["data"]["scanned"] == 2
    assert body["data"]["new"] == 2
    assert len(body["data"]["predicted"]) == 2
    assert body["data"]["predicted"][0]["model_name"] == "fixture_v2"
    assert 0.0 <= body["data"]["predicted"][0]["risk_score"] <= 1.0

    # 二次调用：全部已存在 → new=0（幂等，不重复入库）
    second = client.post("/api/sync?limit=2", headers=HEADERS)
    assert second.status_code == 200
    assert second.json()["data"]["new"] == 0
    assert second.json()["data"]["predicted"] == []


def test_sync_endpoint_unreachable_commit_counts_as_skipped(client, monkeypatch, tmp_path):
    """提取器抛 ValueError（提交不可达）→ 单条计入 skipped（40400），整批不 500。"""
    repo = tmp_path / "camel2"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.setattr(sync_module.config, "SOURCE_REPO", repo)

    hashes = [UNKNOWN]
    monkeypatch.setattr(sync_module, "fetch_latest_tip", lambda repo_dir: hashes[0])
    monkeypatch.setattr(sync_module, "ensure_reachable", lambda repo_dir, tip: None)
    monkeypatch.setattr(sync_module, "list_recent_hashes", lambda repo_dir, limit: hashes)

    def _boom(_hash: str):
        raise ValueError("目标不是当前 HEAD 可达的非合并提交")

    monkeypatch.setattr(sync_module.feature_source, "extract", _boom)
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
