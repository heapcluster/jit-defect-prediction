from tests.conftest import HEADERS


def test_week_aggregation(client):
    body = client.get("/api/trends", headers=HEADERS).json()
    series = body["data"]["series"]
    assert body["data"]["granularity"] == "week"
    assert len(series) == 2
    first = series[0]
    assert set(first) == {"period", "commit_count", "avg_risk", "high_risk_count"}
    assert first["high_risk_count"] == 1
    assert first["period"].startswith("2026-W")


def test_invalid_granularity(client):
    resp = client.get("/api/trends", params={"granularity": "day"}, headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "granularity" in body["message"]


def test_month_aggregation_buckets_by_calendar_month(client):
    """月粒度走 `_period()` 的 YYYY-MM 分支（Issue #73 缺口一：此前零覆盖）。"""
    body = client.get("/api/trends", params={"granularity": "month"}, headers=HEADERS).json()
    assert body["code"] == 0
    assert body["data"]["granularity"] == "month"
    series = body["data"]["series"]
    # 种子 C1=2026-07-20、C2=2026-08-03 各一条预测 → 两个自然月桶，升序
    assert [s["period"] for s in series] == ["2026-07", "2026-08"]
    assert series[0]["commit_count"] == 1
    assert series[0]["high_risk_count"] == 1
    assert abs(series[0]["avg_risk"] - 0.8732) < 1e-9
    assert series[1]["commit_count"] == 1
    assert series[1]["high_risk_count"] == 0


def test_month_granularity_pure_date_end_includes_whole_end_day(client):
    """月粒度同样适用契约 1.5 区间语义：end 纯日期串含结束日全天。"""
    body = client.get(
        "/api/trends",
        params={"granularity": "month", "start_time": "2026-08-01", "end_time": "2026-08-03"},
        headers=HEADERS,
    ).json()
    series = body["data"]["series"]
    assert [s["period"] for s in series] == ["2026-08"]
    # C2 committed_at=2026-08-03 09:00 —— 语义回退时会丢成 0 条
    assert series[0]["commit_count"] == 1


def test_month_granularity_empty_range_is_not_error(client):
    body = client.get(
        "/api/trends",
        params={"granularity": "month", "start_time": "2030-01-01", "end_time": "2030-12-31"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["series"] == []


def test_empty_range_is_not_error(client):
    body = client.get(
        "/api/trends",
        params={
            "start_time": "2030-01-01T00:00:00Z",
            "end_time": "2030-12-31T00:00:00Z",
        },
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["series"] == []


def test_end_pure_date_includes_whole_end_day(client):
    """趋势接口同口径：end 纯日期串含结束日全天（#61）。"""
    body = client.get(
        "/api/trends",
        params={"start_time": "2026-08-03", "end_time": "2026-08-03"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    series = body["data"]["series"]
    assert len(series) == 1
    assert series[0]["period"] == "2026-W32"
    assert series[0]["commit_count"] == 1


def test_compact_basic_format_rejected(client):
    for value in ("20260803", "20260803T090000Z", "20260803T090000+08:00"):
        resp = client.get("/api/trends", params={"end_time": value}, headers=HEADERS)
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001


def test_week_drilldown_monday_to_sunday_keeps_sunday(client):
    """周下钻（周一→周日纯日期串）不丢周日当天 —— Issue #61 原现象的永久防回归判据。

    蒋励在 #75 的建议：集成证据里的 D 断言（真服务 curl）是一次性的，
    这里用夹具把它固化成用例。种子没有周日提交，故临时插一条 2026-08-02（周日）。
    """
    from datetime import datetime

    from tests.conftest import FEATURE_VALUES

    from app.db import SessionLocal
    from app.models import Commit, CommitFeature, Prediction

    sunday = "e" * 40
    with SessionLocal() as session:
        session.add(Commit(commit_hash=sunday, repo_name="camel", author_name="jdoe",
                           committed_at=datetime(2026, 8, 2, 9, 0, 0), message="Sunday commit", parent_hash=None))
        session.add(CommitFeature(commit_hash=sunday, committed_at=datetime(2026, 8, 2, 9, 0, 0),
                                  feature_version="v1", **FEATURE_VALUES))
        session.add(Prediction(commit_hash=sunday, model_name="xgb_v1", risk_score=0.50000,
                               predicted_at=datetime(2026, 9, 1, 8, 0, 0), feature_version="v1"))
        session.commit()
    body = client.get(
        "/api/trends",
        params={"granularity": "week", "start_time": "2026-07-27", "end_time": "2026-08-02"},
        headers=HEADERS,
    ).json()
    series = body["data"]["series"]
    assert [s["period"] for s in series] == ["2026-W31"]
    # 语义回退（end 停当天 00:00）时周日这条会丢，桶计数变 0 / 桶消失
    assert series[0]["commit_count"] == 1
