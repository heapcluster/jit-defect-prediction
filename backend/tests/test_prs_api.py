"""PR 实时预测与查询端点测试（change realtime-pr-prediction）。

覆盖三条边界（与 realtime-commit-sync 同纪律）：
1. 只读查询（GET /api/prs、/api/prs/{number}）不依赖 SOURCE_REPO 历史索引 ——
   未配历史索引时这两个端点照样能返回库内已预测的数据，不该 40400；
2. 逐 PR 隔离：单个 PR 的提交清单拉取失败只跳过该 PR，不让整端 50000；
3. 同步端点（POST /api/sync-prs）limit 边界走契约内 40001，逐 PR 失败进 skipped 不中断。
"""

from __future__ import annotations

from datetime import datetime

from app import config
from app.api import prs as prs_module
from app.db import SessionLocal
from app.errors import AppError
from app.github import PullRequest
from app.models import Commit, Prediction
from tests.conftest import HEADERS


def _pr(number: int, title: str = "fix: camel") -> PullRequest:
    return PullRequest(
        number=number, title=title, author="octocat", state="open",
        head_sha="f" * 40, html_url=f"https://github.com/apache/camel/pull/{number}",
        updated_at="2026-10-25T12:00:00Z",
    )


def _seed_predictions(scores: dict[str, float], model: str = "fixture_v2") -> None:
    """按 {commit_hash: risk_score} 灌 commit + prediction（详情页要读 commit 元信息）。

    先查自然键再插：两张表的 PK 都是自增 id，`merge` 只按 id 去重，
    直接 merge 新对象会撞 commit_hash / (hash, model) 唯一索引。
    """
    with SessionLocal() as session:
        for commit_hash, score in scores.items():
            if session.query(Commit).filter_by(commit_hash=commit_hash).first() is None:
                session.add(Commit(commit_hash=commit_hash, repo_name="camel",
                                   author_name="dev",
                                   committed_at=datetime(2026, 10, 20, 9, 0, 0),
                                   message="CAMEL-1 fix"))
            if (session.query(Prediction)
                    .filter_by(commit_hash=commit_hash, model_name=model).first() is None):
                session.add(Prediction(commit_hash=commit_hash, model_name=model,
                                       risk_score=score,
                                       predicted_at=datetime(2026, 10, 25, 10, 0, 0),
                                       feature_version="v1"))
        session.commit()


def _wire_github(monkeypatch, prs, shas_by_pr, get_pr=None, fail_shas_for=()):
    """把 app.github 的三个只读调用换成可控假实现。"""
    monkeypatch.setattr(prs_module.github, "list_open_prs", lambda limit=20, repo=None: prs)
    monkeypatch.setattr(prs_module.github, "get_pr",
                        lambda number, repo=None: get_pr or _pr(number))

    def fake_shas(number, repo=None):
        if number in fail_shas_for:
            raise RuntimeError("github api 403: rate limited")
        return shas_by_pr.get(number, [])

    monkeypatch.setattr(prs_module.github, "list_pr_commit_shas", fake_shas)


def test_list_prs_aggregates_max_risk_and_counts(client, monkeypatch):
    _seed_predictions({"a" * 40: 0.2, "b" * 40: 0.9, "c" * 40: 0.1})
    _wire_github(monkeypatch, [_pr(7, "CAMEL-7 fix")],
                 {7: ["a" * 40, "b" * 40, "c" * 40]})
    resp = client.get("/api/prs", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    item = body["data"]["items"][0]
    assert item["number"] == 7 and item["title"] == "CAMEL-7 fix"
    assert item["risk_score"] == 0.9, "取该 PR 各提交的最高风险分"
    assert item["commit_count"] == 3 and item["predicted_count"] == 3
    assert item["predicted_at"] == "2026-10-25T10:00:00Z", "ISO 8601 必须带时区后缀 Z"
    assert body["data"]["skipped"] == 0


def test_list_prs_does_not_need_source_repo(client, monkeypatch):
    """回归：只读查询端点不得因未配 SOURCE_REPO 而 40400（曾多余调用 _repo_path）。"""
    monkeypatch.setattr(config, "SOURCE_REPO", None)
    _wire_github(monkeypatch, [_pr(8)], {8: ["a" * 40]})
    resp = client.get("/api/prs", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["data"]["items"][0]["number"] == 8
    detail = client.get("/api/prs/8", headers=HEADERS)
    assert detail.status_code == 200
    assert detail.json()["data"]["commits"][0]["sha"] == "a" * 40


def test_list_prs_isolates_single_pr_failure(client, monkeypatch):
    """一个 PR 的提交清单拉取失败 → 该 PR 进 skipped，其余 PR 照常返回。"""
    _seed_predictions({"a" * 40: 0.5})
    _wire_github(monkeypatch, [_pr(9), _pr(10)], {10: ["a" * 40]}, fail_shas_for=(9,))
    resp = client.get("/api/prs", headers=HEADERS)
    assert resp.status_code == 200, "单个 PR 失败不许把整端打成 50000"
    data = resp.json()["data"]
    assert [item["number"] for item in data["items"]] == [10]
    assert data["skipped"] == 1


def test_pr_detail_returns_commit_rows_with_prediction(client, monkeypatch):
    _seed_predictions({"a" * 40: 0.42})
    _wire_github(monkeypatch, [_pr(11)], {11: ["a" * 40, "d" * 40]})
    resp = client.get("/api/prs/11", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["number"] == 11 and data["model_name"] == "fixture_v2"
    by_sha = {row["sha"]: row for row in data["commits"]}
    assert by_sha["a" * 40]["risk_score"] == 0.42
    assert by_sha["a" * 40]["predicted_at"] == "2026-10-25T10:00:00Z"
    # 未预测的提交：risk_score 是 None（不得用 0.0 冒充）
    assert by_sha["d" * 40]["risk_score"] is None
    assert by_sha["d" * 40]["predicted_at"] is None


def test_pr_endpoints_reject_unknown_model(client, monkeypatch):
    _wire_github(monkeypatch, [_pr(12)], {12: []})
    for path in ("/api/prs", "/api/prs/12"):
        resp = client.get(path, params={"model_name": "nope_v9"}, headers=HEADERS)
        assert resp.status_code == 400 and resp.json()["code"] == 40001, path


def test_sync_prs_validates_limit(client, monkeypatch):
    monkeypatch.setattr(prs_module, "_repo_path", lambda: None)
    for bad in (0, 51):
        resp = client.post("/api/sync-prs", params={"limit": bad}, headers=HEADERS)
        assert resp.status_code == 400 and resp.json()["code"] == 40001, bad


def test_sync_prs_predicts_each_pr_and_reports_skipped(client, monkeypatch, tmp_path):
    """逐 PR 拉 head → 逐提交现算预测入库；fetch 失败进 skipped 不中断整批。"""
    monkeypatch.setattr(prs_module, "_repo_path", lambda: tmp_path)
    _wire_github(monkeypatch, [_pr(13), _pr(14)], {13: ["a" * 40, "b" * 40], 14: []})

    def fake_fetch(repo, number):
        if number == 14:
            raise AppError(50000, "boom")
        return "0" * 40

    monkeypatch.setattr(prs_module, "fetch_pr_ref", fake_fetch)
    predicted: list[str] = []

    def fake_predict(sha, repo=None):
        predicted.append(sha)
        return []

    monkeypatch.setattr(prs_module, "predict_commit_all_models", fake_predict)
    resp = client.post("/api/sync-prs", params={"limit": 10}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["prs_scanned"] == 2
    assert data["commits_predicted"] == 2 and predicted == ["a" * 40, "b" * 40]
    assert data["prs"][0] == {"pr": 13, "title": "fix: camel", "commits_predicted": 2}
    # 响应经 schemas.SyncPrsSkippedItem 序列化：两种失败形态共用字段并集，缺的字段为 null
    assert data["skipped"] == [{"pr": 14, "reason": "fetch failed: boom",
                                "commit": None, "code": None, "message": None}]


def test_sync_prs_single_commit_failure_does_not_stop_the_pr(client, monkeypatch, tmp_path):
    """单个提交预测失败只进 skipped，同 PR 其余提交继续（与 sync 纪律一致）。"""
    monkeypatch.setattr(prs_module, "_repo_path", lambda: tmp_path)
    _wire_github(monkeypatch, [_pr(15)], {15: ["a" * 40, "b" * 40]})
    monkeypatch.setattr(prs_module, "fetch_pr_ref", lambda repo, number: "0" * 40)

    def fake_predict(sha, repo=None):
        if sha == "a" * 40:
            raise AppError(40400, "commit not found")
        return []

    monkeypatch.setattr(prs_module, "predict_commit_all_models", fake_predict)
    resp = client.post("/api/sync-prs", params={"limit": 10}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["commits_predicted"] == 1
    assert data["prs"][0]["commits_predicted"] == 1
    assert data["skipped"] == [{"pr": 15, "commit": "a" * 40, "code": 40400,
                                "message": "commit not found", "reason": None}]
