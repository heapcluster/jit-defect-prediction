# === AI 辅助说明 ===
# 本文件共 24 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：22 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/test/unit_test/prompts/README.md

from app.db import SessionLocal
from app.models import Prediction

from tests.conftest import C1, C2, C3, FEATURE_VALUES, HEADERS, UNKNOWN


def test_list_sorted_and_paged(client):
    body = client.get("/api/commits", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    items = body["data"]["items"]
    assert [item["risk_score"] for item in items] == sorted(
        (item["risk_score"] for item in items), reverse=True
    )
    assert body["data"]["total"] == 2
    assert body["data"]["page"] == 1 and body["data"]["size"] == 20


def test_size_over_limit(client):
    resp = client.get("/api/commits", params={"model_name": "fixture_v2", "size": 101}, headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert "size" in body["message"]


def test_size_at_limit(client):
    resp = client.get("/api/commits", params={"model_name": "fixture_v2", "size": 100}, headers=HEADERS)
    assert resp.status_code == 200


def test_list_returns_contract_fields_and_features_only_on_demand(client):
    """列表项按 docs/api/commits.md：提交元信息 + 预测摘要 + SZZ 标签；features 仅 with_features=1 返回。"""
    body = client.get("/api/commits", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    items = body["data"]["items"]
    assert all(item.get("features") is None for item in items)
    by_hash = {item["commit_hash"]: item for item in items}
    assert by_hash[C1]["is_bug_inducing"] == 1
    assert by_hash[C2]["is_bug_inducing"] == 0
    # 契约字段逐一校验，不把缺字段当成通过
    expected = {
        "commit_hash", "repo_name", "author_name", "committed_at", "message",
        "model_name", "risk_score", "predicted_label", "predicted_at",
        "is_bug_inducing", "labeled_at", "label_method",
    }
    for item in items:
        assert expected <= set(item), f"列表项缺少契约字段：{expected - set(item)}"
        assert item["model_name"] == "fixture_v2"
        assert item["repo_name"] == "camel"
        assert item["message"].startswith("CAMEL-")
        assert item["committed_at"].endswith("Z")
        assert item["predicted_at"].endswith("Z")
        assert item["predicted_label"] in (0, 1)
        assert 0.0 <= item["risk_score"] <= 1.0
    # 列表不返回已废止的 is_test，也不含解释/定位/修复字段
    for item in items:
        assert "is_test" not in item
        assert "explanation" not in item and "localization" not in item and "fix_references" not in item

    with_features = client.get(
        "/api/commits", params={"with_features": "1", "model_name": "fixture_v2"}, headers=HEADERS
    ).json()
    assert set(with_features["data"]["items"][0]["features"]) == set(FEATURE_VALUES)


def test_list_is_test_is_rejected(client):
    """is_test 已废止：docs/api/commits.md §5 明确传入返回 40001，不再作为筛选参数。"""
    for value in ("0", "1"):
        resp = client.get(
            "/api/commits", params={"model_name": "fixture_v2", "is_test": value}, headers=HEADERS
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40001
        assert body["data"] is None


def test_invalid_with_features_rejected(client):
    resp = client.get("/api/commits", params={"model_name": "fixture_v2", "with_features": "2"}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_list_risk_range_filters(client):
    """risk_min/risk_max 按闭区间筛选 [0,1] 的 risk_score（C1=0.8732, C2=0.21）。"""
    base = {"model_name": "fixture_v2"}
    high = client.get("/api/commits", params={**base, "risk_min": 0.5}, headers=HEADERS).json()
    assert high["code"] == 0
    assert [item["commit_hash"] for item in high["data"]["items"]] == [C1]
    low = client.get("/api/commits", params={**base, "risk_max": 0.5}, headers=HEADERS).json()
    assert [item["commit_hash"] for item in low["data"]["items"]] == [C2]
    band = client.get(
        "/api/commits", params={**base, "risk_min": 0.2, "risk_max": 0.3}, headers=HEADERS
    ).json()
    assert [item["commit_hash"] for item in band["data"]["items"]] == [C2]
    for params in (
        {"risk_min": -0.1}, {"risk_max": 1.1}, {"risk_min": 0.8, "risk_max": 0.2},
    ):
        resp = client.get("/api/commits", params={**base, **params}, headers=HEADERS)
        assert resp.status_code == 400 and resp.json()["code"] == 40001


def test_list_dataset_id_filter(client):
    """dataset_id 仅筛选已导入 dataset_commit 成员；未知 dataset 返回 40400。"""
    from datetime import datetime

    from app.db import SessionLocal
    from app.models import Dataset, DatasetCommit

    with SessionLocal() as session:
        session.add(
            Dataset(
                dataset_id="ds-only-c1", name="only-c1", source_type="git_repo",
                status="ready", created_at=datetime(2026, 1, 1),
            )
        )
        session.add(
            DatasetCommit(
                dataset_id="ds-only-c1", commit_hash=C1, repo_name="camel",
                label_source="git_szz", source_type="git_repo", row_no=1,
                committed_at=datetime(2026, 7, 20, 9, 0, 0),
            )
        )
        session.commit()
    scoped = client.get(
        "/api/commits", params={"model_name": "fixture_v2", "dataset_id": "ds-only-c1"},
        headers=HEADERS,
    ).json()
    assert scoped["code"] == 0
    assert [item["commit_hash"] for item in scoped["data"]["items"]] == [C1]
    missing = client.get(
        "/api/commits", params={"model_name": "fixture_v2", "dataset_id": "no-such-dataset"},
        headers=HEADERS,
    )
    assert missing.status_code == 404 and missing.json()["code"] == 40400


def test_detail_features_and_prediction(client):
    """详情按 docs/api/commits.md：features + §3.1 标签 + prediction 对象；无解释/定位字段。"""
    body = client.get(f"/api/commits/{C1}", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    data = body["data"]
    assert set(data["features"]) == set(FEATURE_VALUES)
    assert data["is_bug_inducing"] == 1
    prediction = data["prediction"]
    assert prediction is not None
    assert prediction["model_name"] == "fixture_v2"
    assert prediction["risk_score"] == 0.8732
    assert prediction["predicted_label"] in (0, 1)
    assert prediction["predicted_at"].endswith("Z")
    assert {
        "model_name", "risk_score", "predicted_label", "decision_threshold",
        "model_version", "feature_version", "predicted_at", "stale",
    } <= set(prediction)
    for forbidden in ("explanation", "localization", "fix_references"):
        assert forbidden not in data


def test_detail_does_not_embed_localization(client):
    """docs/api/commits.md §2：详情不含 localization；行级定位由 /api/localize/run 独立编排。"""
    body = client.get(f"/api/commits/{C1}", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    assert "localization" not in body["data"]


def test_detail_model_name_matches_list_selection(client):
    """详情按显式 model_name 查询同一模型的 prediction，不再有默认模型回退。"""
    from datetime import datetime

    from app.models import Prediction

    with SessionLocal() as session:
        session.add(
            Prediction(
                commit_hash=C1,
                model_name="fixture_v1",
                risk_score=0.33,
                predicted_at=datetime(2026, 9, 1),
            )
        )
        session.commit()
    body = client.get(
        f"/api/commits/{C1}", params={"model_name": "fixture_v1"}, headers=HEADERS
    ).json()
    assert body["data"]["prediction"]["model_name"] == "fixture_v1"
    assert body["data"]["prediction"]["risk_score"] == 0.33
    default = client.get(f"/api/commits/{C1}", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    assert default["data"]["prediction"]["model_name"] == "fixture_v2"
    assert default["data"]["prediction"]["risk_score"] == 0.8732


def test_detail_does_not_embed_fix_references(client):
    """docs/api/commits.md §2：详情不含 fix_references；修复建议由独立端点获取。"""
    for hash_ in (C1, C3):
        body = client.get(f"/api/commits/{hash_}", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
        assert body["code"] == 0
        assert "fix_references" not in body["data"]


def test_detail_without_prediction_returns_null_prediction(client):
    """提交存在但所选模型无预测 → HTTP 200 且 prediction=null（docs §2）。"""
    body = client.get(f"/api/commits/{C3}", params={"model_name": "fixture_v2"}, headers=HEADERS).json()
    data = body["data"]
    assert body["code"] == 0
    assert data["prediction"] is None
    assert data["commit_hash"] == C3
    assert data["features"] is None


def test_detail_unknown_hash(client):
    resp = client.get(f"/api/commits/{UNKNOWN}", params={"model_name": "fixture_v2"}, headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["message"] == "commit not found"


def test_detail_bad_hash_format(client):
    resp = client.get(f"/api/commits/{'a' * 39}", params={"model_name": "fixture_v2"}, headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_explicit_model_selection(client, monkeypatch):
    from dataclasses import replace
    from datetime import datetime

    from app import model_registry
    from app.db import SessionLocal
    from app.models import Model, Prediction

    entry = replace(model_registry.get_model("fixture_v2"), name="xgb_v9")
    monkeypatch.setitem(model_registry._REGISTRY, entry.name, entry)
    with SessionLocal() as session:
        session.add(Model(model_name="xgb_v9", line="expert"))
        session.add(
            Prediction(
                commit_hash=C1,
                model_name="xgb_v9",
                risk_score=0.55,
                predicted_at=datetime(2020, 1, 1),
            )
        )
        session.commit()
    body = client.get("/api/commits", params={"model_name": "xgb_v9"}, headers=HEADERS).json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["model_name"] == "xgb_v9"
    detail = client.get(f"/api/commits/{C1}", params={"model_name": "xgb_v9"}, headers=HEADERS).json()
    assert detail["data"]["prediction"]["model_name"] == "xgb_v9"
    assert detail["data"]["prediction"]["risk_score"] == 0.55


def test_end_pure_date_includes_whole_end_day(client):
    """契约三 1.5：end 纯日期串含结束日全天（#61：此前丢当天数据）。"""
    body = client.get(
        "/api/commits",
        params={"start_time": "2026-08-03", "end_time": "2026-08-03", "model_name": "fixture_v2"},
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["commit_hash"] == C2


def test_end_with_time_component_unchanged(client):
    """带时间分量按原样解析：08-03T08:59:59 不含 C2，09:00:00 含。"""
    early = client.get(
        "/api/commits", params={"end_time": "2026-08-03T08:59:59", "model_name": "fixture_v2"}, headers=HEADERS
    ).json()
    late = client.get(
        "/api/commits", params={"end_time": "2026-08-03T09:00:00", "model_name": "fixture_v2"}, headers=HEADERS
    ).json()
    assert early["data"]["total"] == 1
    assert late["data"]["total"] == 2


def test_start_pure_date_still_midnight(client):
    """start 纯日期串仍是当天 00:00:00，不随 end 规则变（#61 评审：不能一刀切）。"""
    body = client.get("/api/commits", params={"model_name": "fixture_v2", "start_time": "2026-08-03"}, headers=HEADERS).json()
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
        resp = client.get("/api/commits", params={"model_name": "fixture_v2", param: value}, headers=HEADERS)
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == 40001
        assert param in body["message"]


def test_commits_time_filter_does_not_trigger_prediction(client):
    """日期过滤仅筛选已预测结果，不触发新预测；用 prediction 行数不变直接证明。"""
    with SessionLocal() as session:
        before = session.query(Prediction).count()
    body = client.get(
        "/api/commits",
        params={
            "start_time": "2026-07-01", "end_time": "2026-07-31",
            "model_name": "fixture_v2",
        },
        headers=HEADERS,
    ).json()
    assert body["code"] == 0
    # C1 在 07-20，落在区间内；C2 在 08-03 不在
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["commit_hash"] == C1
    with SessionLocal() as session:
        assert session.query(Prediction).count() == before, "查看过滤 MUST NOT 触发新预测"


def test_deprecated_since_until_params_rejected(client):
    """since/until 已从 commits 契约下线：未知参数一律 40001，不得静默忽略。"""
    for param in ("since", "until"):
        resp = client.get(
            "/api/commits", params={"model_name": "fixture_v2", param: "2026-07-01"},
            headers=HEADERS,
        )
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001


def test_search_by_message_and_by_hash_prefix(client):
    """q 支持提交信息片段与哈希前缀，且只做查看过滤。"""
    by_message = client.get("/api/commits", params={"model_name": "fixture_v2", "q": "CAMEL-2"}, headers=HEADERS).json()["data"]
    assert [item["commit_hash"] for item in by_message["items"]] == [C2]

    by_hash = client.get("/api/commits", params={"model_name": "fixture_v2", "q": C1[:8]}, headers=HEADERS).json()["data"]
    assert [item["commit_hash"] for item in by_hash["items"]] == [C1]


def test_search_treats_like_wildcards_literally(client):
    """`_` / `%` 必须按字面匹配（LIKE 需显式 escape），不能退化成通配符扫全表。"""
    for keyword in ("jd_e", "jd%", "_", "%"):
        data = client.get("/api/commits", params={"model_name": "fixture_v2", "q": keyword}, headers=HEADERS).json()["data"]
        assert data["items"] == [], f"{keyword!r} 被当成了通配符"
    # 作者 jdoe 字面命中不受影响（C3 无 prediction，列表只展示已预测的 C1/C2）
    hit = client.get("/api/commits", params={"model_name": "fixture_v2", "q": "jdoe"}, headers=HEADERS).json()["data"]
    assert hit["total"] == 2
