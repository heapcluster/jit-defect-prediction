"""运维加固（change ops-hardening）：运行时配置热更新、探针拆分、PR 风险门禁。"""

from __future__ import annotations

from app.db import SessionLocal
from app.models import Prediction
from app.services import settings as runtime_settings

from tests.conftest import C1, C2, HEADERS


def test_get_config_returns_defaults(client):
    body = client.get("/api/config", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["high_risk_threshold"] == 0.5
    assert data["mid_risk_threshold"] == 0.2
    assert data["sync_initial_limit"] > 0
    assert data["sync_catchup_limit"] > 0


def test_put_config_updates_and_takes_effect(client):
    """阈值热更新：PUT 之后 PR 等级判定立刻按新阈值走，无需重启。"""
    body = client.put(
        "/api/config",
        json={"high_risk_threshold": 0.3, "mid_risk_threshold": 0.1},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["high_risk_threshold"] == 0.3
    assert body["data"]["mid_risk_threshold"] == 0.1
    assert body["data"]["updated_at"] is not None

    from app.api.prs import get_pr_risk_level

    assert get_pr_risk_level(0.35) == "高"
    assert get_pr_risk_level(0.15) == "中"


def test_put_config_rejects_inverted_thresholds(client):
    body = client.put(
        "/api/config",
        json={"high_risk_threshold": 0.1, "mid_risk_threshold": 0.4},
        headers=HEADERS,
    ).json()
    assert body["code"] == 40001
    # 非法请求不得写入
    assert runtime_settings.high_threshold() == 0.5


def test_health_live_is_independent_of_db(client):
    """liveness 不查 DB，只说明进程活着。"""
    body = client.get("/api/health/live", headers=HEADERS).json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["data"]["server_time"].endswith("Z")


def test_health_ready_reports_db_and_models(client):
    body = client.get("/api/health/ready", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["db"] == "up"
    assert data["models_loaded"] >= 1
    assert data["status"] == "ok"


def test_pr_gate_blocks_high_risk(client, monkeypatch):
    """高风险 PR 被门禁拦截；数据只从本地 prediction 读，不依赖网络。"""
    with SessionLocal() as session:
        row = session.query(Prediction).filter_by(commit_hash=C1, model_name="fixture_v2").one()
        row.risk_score = 0.91
        session.commit()
    monkeypatch.setattr("app.api.prs.github.list_pr_commit_shas", lambda number: [C1, C2])

    body = client.get("/api/prs/7/gate", headers=HEADERS).json()
    assert body["code"] == 0
    data = body["data"]
    assert data["number"] == 7
    assert data["risk_score"] == 0.91
    assert data["risk_level"] == "高"
    assert data["threshold"] == 0.5
    assert data["blocked"] is True


def test_pr_gate_allows_low_risk(client, monkeypatch):
    with SessionLocal() as session:
        row = session.query(Prediction).filter_by(commit_hash=C2, model_name="fixture_v2").one()
        row.risk_score = 0.12
        session.commit()
    monkeypatch.setattr("app.api.prs.github.list_pr_commit_shas", lambda number: [C2])

    data = client.get("/api/prs/8/gate", headers=HEADERS).json()["data"]
    assert data["blocked"] is False
    assert data["risk_level"] == "低"


def test_ops_endpoints_require_api_key(client):
    for path in ("/api/config", "/api/health/live", "/api/health/ready"):
        resp = client.get(path)
        assert resp.status_code == 401, path
        assert resp.json()["code"] == 40100, path
