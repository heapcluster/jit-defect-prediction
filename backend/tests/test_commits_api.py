from app.db import SessionLocal
from app.models import Prediction

from tests.conftest import C1, C2, C3, FEATURE_VALUES, HEADERS, UNKNOWN


def test_list_sorted_and_paged(client):
    body = client.get("/api/commits", headers=HEADERS).json()
    items = body["data"]["items"]
    assert [item["risk_score"] for item in items] == sorted(
        (item["risk_score"] for item in items), reverse=True
    )
    assert body["data"]["total"] == 2
    assert body["data"]["page"] == 1 and body["data"]["size"] == 20


def test_size_over_limit(client):
    resp = client.get("/api/commits", params={"size": 101}, headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "size" in body["message"]


def test_size_at_limit(client):
    resp = client.get("/api/commits", params={"size": 100}, headers=HEADERS)
    assert resp.status_code == 200


def test_min_risk_filter_empty_is_not_error(client):
    body = client.get("/api/commits", params={"min_risk": 0.99}, headers=HEADERS).json()
    assert body["code"] == 0
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


def test_detail_features_and_explanation(client):
    body = client.get(f"/api/commits/{C1}", headers=HEADERS).json()
    data = body["data"]
    assert set(data["features"]) == set(FEATURE_VALUES)
    assert data["risk_score"] == 0.8732
    assert isinstance(data["explanation"], list)


def test_detail_without_prediction_returns_nulls(client):
    body = client.get(f"/api/commits/{C3}", headers=HEADERS).json()
    data = body["data"]
    assert body["code"] == 0
    assert data["risk_score"] is None
    assert data["model_name"] is None
    assert data["explanation"] == []
    assert data["features"] is None


def test_detail_unknown_hash(client):
    resp = client.get(f"/api/commits/{UNKNOWN}", headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["message"] == "commit not found"


def test_detail_bad_hash_format(client):
    resp = client.get(f"/api/commits/{'a' * 39}", headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_default_model_is_version_order_not_recency(client):
    from datetime import datetime

    from app.db import SessionLocal
    from app.models import Prediction

    with SessionLocal() as session:
        session.add(
            Prediction(
                commit_hash=C1,
                model_name="xgb_v9",
                risk_score=0.55,
                predicted_at=datetime(2020, 1, 1),
                feature_version="v1",
            )
        )
        session.commit()
    body = client.get("/api/commits", headers=HEADERS).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["model_name"] == "xgb_v9"
    detail = client.get(f"/api/commits/{C1}", headers=HEADERS).json()
    assert detail["data"]["model_name"] == "xgb_v9"
    assert detail["data"]["risk_score"] == 0.55


def test_end_pure_date_includes_whole_end_day(client):
    """契约三 1.5：end 纯日期串含结束日全天（#61：此前丢当天数据）。"""
    body = client.get(
        "/api/commits",
        params={"start_time": "2026-08-03", "end_time": "2026-08-03"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["commit_hash"] == C2


def test_end_with_time_component_unchanged(client):
    """带时间分量按原样解析：08-03T08:59:59 不含 C2，09:00:00 含。"""
    early = client.get(
        "/api/commits", params={"end_time": "2026-08-03T08:59:59"}, headers=HEADERS
    ).json()
    late = client.get(
        "/api/commits", params={"end_time": "2026-08-03T09:00:00"}, headers=HEADERS
    ).json()
    assert early["data"]["total"] == 1
    assert late["data"]["total"] == 2


def test_start_pure_date_still_midnight(client):
    """start 纯日期串仍是当天 00:00:00，不随 end 规则变（#61 评审：不能一刀切）。"""
    body = client.get("/api/commits", params={"start_time": "2026-08-03"}, headers=HEADERS).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["commit_hash"] == C2


def test_compact_basic_format_rejected(client):
    """紧凑基本格式（20260803）拒收 40001，不与带分隔符写法产生两种结果（#62 复审 1）。"""
    for param, value in (
        ("start_time", "20260803"),
        ("end_time", "20260803"),
        ("end_time", "20260803T090000Z"),
        ("end_time", "20260803T090000+08:00"),
    ):
        resp = client.get("/api/commits", params={param: value}, headers=HEADERS)
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40001
        assert param in body["message"]


def test_commits_coverage_reports_time_ranges(client):
    """GET /api/commits/coverage 返回各模型已预测的时间覆盖区间（start 含结束日全天口径）。"""
    body = client.get("/api/commits/coverage", headers=HEADERS).json()
    assert body["code"] == 0
    items = body["data"]["items"]
    # conftest 已为 C1(07-20)/C2(08-03) 以 xgb_v1 灌 prediction
    by_model = {it["model_name"]: it for it in items}
    assert "xgb_v1" in by_model
    cov = by_model["xgb_v1"]
    assert cov["start"] is not None and cov["end"] is not None
    assert cov["start"] <= cov["end"]


def test_commits_view_filter_does_not_trigger_prediction(client):
    """日期（since/until）仅过滤已预测结果，不触发新预测（startup-baseline-sync）。

    用「prediction 行数不变」直接证明没有发生任何现算预测，比断言未触碰 git 更硬。
    """
    with SessionLocal() as session:
        before = session.query(Prediction).count()
    body = client.get(
        "/api/commits",
        params={"since": "2026-07-01", "until": "2026-07-31"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    # C1 在 07-20，落在区间内；C2 在 08-03 不在
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["commit_hash"] == C1
    with SessionLocal() as session:
        assert session.query(Prediction).count() == before, "查看过滤 MUST NOT 触发新预测"


def test_search_by_message_and_by_hash_prefix(client):
    """q 支持提交信息片段与哈希前缀，且只做查看过滤。"""
    by_message = client.get("/api/commits", params={"q": "CAMEL-2"}, headers=HEADERS).json()["data"]
    assert [item["commit_hash"] for item in by_message["items"]] == [C2]

    by_hash = client.get("/api/commits", params={"q": C1[:8]}, headers=HEADERS).json()["data"]
    assert [item["commit_hash"] for item in by_hash["items"]] == [C1]


def test_search_treats_like_wildcards_literally(client):
    """`_` / `%` 必须按字面匹配（LIKE 需显式 escape），不能退化成通配符扫全表。"""
    for keyword in ("jd_e", "jd%", "_", "%"):
        data = client.get("/api/commits", params={"q": keyword}, headers=HEADERS).json()["data"]
        assert data["items"] == [], f"{keyword!r} 被当成了通配符"
    # 作者 jdoe 字面命中不受影响（C3 无 prediction，列表只展示已预测的 C1/C2）
    hit = client.get("/api/commits", params={"q": "jdoe"}, headers=HEADERS).json()["data"]
    assert hit["total"] == 2
