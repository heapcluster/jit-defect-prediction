# 来源：[AI生成]；尚未人工审核，不作为课程审核完成证据。

import json
from pathlib import Path

import pytest
from app.db import SessionLocal
from app.models import User, UserConfig
from app.timeutil import now_naive_utc
from sqlalchemy import select

from tests.conftest import HEADERS


@pytest.fixture
def config_client(client):
    with SessionLocal() as session:
        session.query(UserConfig).delete()
        session.query(User).delete()
        session.add(User(user_id="global", display_name="全局默认", role="system",
                         status="active", created_at=now_naive_utc()))
        session.commit()
    yield client
    with SessionLocal() as session:
        session.query(UserConfig).delete()
        session.query(User).delete()
        session.commit()


def test_read_factory_config_is_sorted_and_excludes_secrets(config_client):
    response = config_client.get("/api/config", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()["data"]
    items = data["items"]
    keys = [item["config_key"] for item in items]
    assert keys == sorted(keys)
    assert len(keys) == 23
    assert all(item["source"] == "factory" for item in items)
    assert {item["config_key"]: item["value"] for item in items}["decision_threshold"] == 0.5
    assert not any(key in keys for key in ("API_TOKEN", "DB_PASSWORD", "LLM_API_KEY"))


def test_batch_write_is_persisted_and_read_by_new_session(config_client):
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "risk_high_threshold", "value": 0.8},
        {"config_key": "risk_mid_threshold", "value": 0.6},
        {"config_key": "predict.batch_size", "value": 42},
    ]})
    assert response.status_code == 200
    assert [item["config_key"] for item in response.json()["data"]["items"]] == [
        "risk_high_threshold", "risk_mid_threshold", "predict.batch_size"]
    with SessionLocal() as session:
        rows = session.scalars(select(UserConfig)).all()
        assert {row.config_key: json.loads(row.value_json) for row in rows} == {
            "risk_high_threshold": 0.8, "risk_mid_threshold": 0.6, "predict.batch_size": 42}
    fresh = config_client.get("/api/config?keys=predict.batch_size", headers=HEADERS)
    assert fresh.json()["data"]["items"][0]["value"] == 42
    assert fresh.json()["data"]["items"][0]["source"] == "global"


@pytest.mark.parametrize("key,value", [
    ("decision_threshold", 0), ("decision_threshold", 1),
    ("decision_threshold", True), ("decision_threshold", "0.4"),
    ("predict.batch_size", 0), ("predict.batch_size", 1.5),
    ("predict.cache_ttl", -1), ("effort_enabled", "true"),
    ("selected_model", 123), ("default_dataset", "missing_dataset"),
    ("default_xai", "unregistered"), ("metrics_selected", ["auc", "auc"]),
    ("metrics_selected", ["unknown_metric"]), ("page_prefs", {"API_TOKEN": "secret"}),
    ("localization.top_n", {"files": 0, "lines": 30}),
    ("collect.protocol_whitelist", ["file", "ssh"]),
    ("train.templates", {"unknown": {"algos": ["unknown"]}}),
    ("clean.chain_templates", {"bad": {"steps": [{"op": "unknown"}]}}),
    ("DB_PASSWORD", "secret"), ("unknown", 1),
])
def test_invalid_batch_does_not_write_any_rows(config_client, key, value):
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "explain.cache_ttl", "value": 30},
        {"config_key": key, "value": value},
    ]})
    assert response.status_code in (400, 404)
    assert response.json()["code"] in (40001, 40400)
    with SessionLocal() as session:
        assert session.scalars(select(UserConfig)).all() == []


def test_cross_key_constraint_rejects_batch(config_client):
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "risk_mid_threshold", "value": 0.7},
    ]})
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_primary_metric_must_be_selected(config_client):
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "metrics_selected", "value": ["recall"]},
    ]})
    assert response.status_code == 400
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "metrics_selected", "value": ["recall"]},
        {"config_key": "primary_metric", "value": "recall"},
    ]})
    assert response.status_code == 200


def test_single_key_write_and_delete_falls_back_to_factory(config_client):
    response = config_client.put("/api/config/decision_threshold", headers=HEADERS,
                                 json={"value": 0.3})
    assert response.status_code == 200
    response = config_client.delete("/api/config/decision_threshold", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["data"] == {"config_key": "decision_threshold", "deleted": True,
                                       "fallback_source": "factory", "value": 0.5}
    assert config_client.delete("/api/config/decision_threshold", headers=HEADERS).status_code == 404


def test_delete_cannot_break_cross_key_constraints(config_client):
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": "risk_high_threshold", "value": 0.8},
        {"config_key": "risk_mid_threshold", "value": 0.6},
    ]})
    assert response.status_code == 200
    response = config_client.delete("/api/config/risk_high_threshold", headers=HEADERS)
    assert response.status_code == 400
    assert config_client.get("/api/config?keys=risk_high_threshold", headers=HEADERS).json()["data"]["items"][0]["value"] == 0.8


def test_all_config_methods_require_auth(config_client):
    for method, url, payload in [
        ("get", "/api/config", None),
        ("put", "/api/config", {"items": []}),
        ("put", "/api/config/decision_threshold", {"value": 0.3}),
        ("delete", "/api/config/decision_threshold", None),
    ]:
        response = config_client.request(method, url, json=payload)
        assert response.status_code == 401
        assert response.json()["code"] == 40100


def test_namespace_values_keep_native_types(config_client):
    values = {
        "collect.allow_roots": [str(Path.home())],
        "collect.protocol_whitelist": ["https"],
        "clean.chain_templates": {}, "train.templates": {},
        "predict.batch_size": 100, "predict.cache_ttl": 0, "predict.retry_max": 0,
        "explain.cache_ttl": 0, "explain.compare_enabled": False,
        "localization.weights": {"mix": {"base": 0.5, "file": 0.3, "hunk": 0.2}},
        "localization.top_n": {"files": 5, "lines": 30},
        "localization.file_size_max": 1000000,
        "localization.suggestion_sources": ["template"],
        "page_prefs": {"page_size": 20, "remember_drawer": True, "explain_top_n": 8},
    }
    response = config_client.put("/api/config", headers=HEADERS, json={"items": [
        {"config_key": key, "value": value} for key, value in values.items()]})
    assert response.status_code == 200
    assert {item["config_key"]: item["value"] for item in response.json()["data"]["items"]} == values


def test_collect_page_preferences_persist_and_reset(config_client):
    value = {'page_size': 20, 'collect_branch': 'main', 'collect_mode': 'full'}
    response = config_client.put('/api/config/page_prefs', headers=HEADERS, json={'value': value})
    assert response.status_code == 200
    with SessionLocal() as session:
        from app.services.config_store import get_value
        assert get_value('page_prefs', session) == value
    response = config_client.delete('/api/config/page_prefs', headers=HEADERS)
    assert response.status_code == 200
    assert response.json()['data']['value'] == {}


@pytest.mark.parametrize('value', [{'collect_branch': False}, {'collect_branch': 'x' * 256},
                                    {'collect_mode': 'random'}, {'collect_branch': 'main\\n--all'}])
def test_invalid_collect_page_preferences_are_rejected(config_client, value):
    response = config_client.put('/api/config/page_prefs', headers=HEADERS, json={'value': value})
    assert response.status_code == 400


def test_user_layer_resolves_and_deletes_to_global(config_client):
    from app.services.config_store import delete_config, read_config, write_config
    with SessionLocal() as session:
        session.add(User(user_id="operator", display_name="操作者", role="member",
                         status="active", created_at=now_naive_utc()))
        session.commit()
        write_config(session, [{"config_key": "decision_threshold", "value": 0.4}])
        write_config(session, [{"config_key": "decision_threshold", "value": 0.3}], user_id="operator")
        assert read_config(session, ["decision_threshold"], user_id="operator")[0]["source"] == "user"
        result = delete_config(session, "decision_threshold", user_id="operator")
        assert result["fallback_source"] == "global"
        assert result["value"] == 0.4


def test_commits_requires_explicit_model(config_client):
    response = config_client.get("/api/commits", headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == 40001


def test_single_prediction_requires_explicit_model(config_client):
    prediction = config_client.post("/api/predict", headers=HEADERS, json={"commit_hash": "a" * 40})
    assert prediction.status_code == 400
    assert prediction.json()["code"] == 40001


def test_risk_threshold_change_updates_trend_but_not_stored_risk_score(config_client):
    """阈值只改变风险判定展示；docs/api/commits.md 详情无 summary 字段，且阈值不改变库中 risk_score。"""
    first = config_client.get("/api/commits/" + "a" * 40, params={"model_name": "fixture_v2"}, headers=HEADERS).json()["data"]
    assert first["prediction"] is not None
    original_score = first["prediction"]["risk_score"]
    # 详情按 docs 字段编排，不含解释/定位/修复参考
    for forbidden in ("explanation", "localization", "fix_references"):
        assert forbidden not in first
    saved = config_client.put("/api/config/risk_high_threshold", headers=HEADERS, json={"value": 0.9})
    assert saved.status_code == 200
    response = config_client.get("/api/trends", params={"model_name": "fixture_v2"}, headers=HEADERS)
    assert response.status_code == 200
    assert sum(item["high_risk_count"] for item in response.json()["data"]["series"]) == 0
    second = config_client.get("/api/commits/" + "a" * 40, params={"model_name": "fixture_v2"}, headers=HEADERS).json()["data"]
    assert second["prediction"]["risk_score"] == original_score


@pytest.mark.parametrize("name,status", [("normal", 200), ("boundary", 200), ("invalid", 400)])
def test_config_files_are_independent_inputs(config_client, name, status):
    from pathlib import Path
    fixture = Path(__file__).parent / "fixtures" / "files" / "config" / (name + ".json")
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    response = config_client.put("/api/config", headers=HEADERS, json=payload)
    assert response.status_code == status
    with SessionLocal() as session:
        saved = session.scalars(select(UserConfig)).all()
        assert len(saved) == (len(payload["items"]) if status == 200 else 0)


def test_huge_integer_threshold_returns_400(config_client):
    response = config_client.put("/api/config/decision_threshold", headers=HEADERS, json={"value": 10 ** 400})
    assert response.status_code == 400
    assert response.json()["code"] == 40001


@pytest.mark.parametrize("operation", ["write", "delete"])
def test_global_default_change_cannot_invalidate_user_override(config_client, operation):
    from app.errors import AppError
    from app.services.config_store import delete_config, write_config
    with SessionLocal() as session:
        session.add(User(user_id="operator", display_name="操作者", role="member", status="active", created_at=now_naive_utc()))
        session.commit()
        write_config(session, [{"config_key": "risk_high_threshold", "value": 0.8}])
        write_config(session, [{"config_key": "risk_mid_threshold", "value": 0.6}], user_id="operator")
        with pytest.raises(AppError) as rejected:
            if operation == "write":
                write_config(session, [{"config_key": "risk_high_threshold", "value": 0.5}])
            else:
                delete_config(session, "risk_high_threshold")
        assert rejected.value.code == 40001
        assert json.loads(session.get(UserConfig, ("global", "risk_high_threshold")).value_json) == 0.8


def test_missing_model_rejected_without_database(config_client, monkeypatch):
    from app.errors import AppError
    from app.services import predict
    def no_database(*args, **kwargs):
        pytest.fail("Missing model must be rejected without opening a database")
    monkeypatch.setattr("app.services.config_store.get_value", no_database)
    with pytest.raises(AppError) as error:
        predict.resolve_model_name(None)
    assert error.value.code == 40001


def test_reused_session_validates_latest_concurrent_value(config_client):
    from app.errors import AppError
    from app.services.config_store import write_config
    with SessionLocal() as first:
        write_config(first, [{"config_key": "risk_high_threshold", "value": 0.8}, {"config_key": "risk_mid_threshold", "value": 0.4}])
        with SessionLocal() as second:
            write_config(second, [{"config_key": "risk_mid_threshold", "value": 0.6}])
        with pytest.raises(AppError) as rejected:
            write_config(first, [{"config_key": "risk_high_threshold", "value": 0.5}])
        assert rejected.value.code == 40001
    with SessionLocal() as session:
        assert json.loads(session.get(UserConfig, ("global", "risk_high_threshold")).value_json) == 0.8
        assert json.loads(session.get(UserConfig, ("global", "risk_mid_threshold")).value_json) == 0.6


def test_multibyte_config_size_is_checked_in_utf8_bytes(config_client):
    from app.errors import AppError
    from app.services.config_store import write_config
    with SessionLocal() as session:
        with pytest.raises(AppError) as rejected:
            write_config(session, [{"config_key": "collect.allow_roots", "value": ["/" + "中" * 22000]}])
        assert rejected.value.code == 40001
        assert session.scalars(select(UserConfig)).all() == []


def test_read_unknown_key_is_rejected(config_client):
    response = config_client.get("/api/config?keys=DB_PASSWORD", headers=HEADERS)
    assert response.status_code == 400
    assert response.json()["code"] == 40001
