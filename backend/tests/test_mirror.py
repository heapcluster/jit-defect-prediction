"""Swagger 实现镜像（tasks 5.1）：openapi 路径与参数名逐字对齐契约三。

契约三原有五条路径；realtime-pr-prediction（PR 实时预测）又登记了三条：
`POST /api/sync-prs`、`GET /api/prs`、`GET /api/prs/{number}`
（api-spec.md §5 同步登记，版本见该文件头）。
路径集仍是「一条不多一条不少」的精确断言 —— 新增端点必须同步改这里与契约，
不允许静默多出路径。
"""

from tests.conftest import HEADERS

CONTRACT_PATHS = {
    "/api/commits",
    "/api/commits/{commit_hash}",
    "/api/commits/coverage",
    "/api/commits/{commit_hash}/label",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/quality",
    "/api/quality/dataset",
    "/api/quality/calibrate",
    "/api/config",
    "/api/webhook/github",
    "/api/trends",
    "/api/predict",
    "/api/sync",
    "/api/sync/catchup",
    "/api/sync/status",
    "/api/sync/stream",
}
PR_PATHS = {"/api/sync-prs", "/api/prs", "/api/prs/{number}", "/api/prs/{number}/gate"}


def _schema(client):
    return client.get("/openapi.json", headers=HEADERS).json()


def test_paths_match_contract(client):
    paths = set(_schema(client)["paths"])
    assert paths == CONTRACT_PATHS | PR_PATHS


def test_sync_is_post_with_limit(client):
    doc = _schema(client)
    assert "post" in doc["paths"]["/api/sync"]
    params = {p["name"] for p in doc["paths"]["/api/sync"]["post"]["parameters"]}
    assert "limit" in params


def test_commits_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/commits"]["get"]["parameters"]}
    assert {"page", "size", "min_risk", "model_name", "start_time", "end_time"} <= params


def test_trends_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/trends"]["get"]["parameters"]}
    assert {"granularity", "start_time", "end_time", "model_name"} <= params


def test_predict_is_post(client):
    assert "post" in _schema(client)["paths"]["/api/predict"]


def test_pr_endpoints_methods_and_params_match_contract(client):
    """PR 三条端点的方法与查询参数逐字对齐（api-spec §5）。

    `x-api-key` 是鉴权头（契约三 §1），经 router 级 dependencies 声明进 OpenAPI，故在参数列表里。
    """
    doc = _schema(client)
    assert set(doc["paths"]["/api/sync-prs"]) == {"post"}
    assert {p["name"] for p in doc["paths"]["/api/sync-prs"]["post"]["parameters"]} == {
        "limit",
        "x-api-key",
    }
    for path in ("/api/prs", "/api/prs/{number}", "/api/prs/{number}/gate"):
        assert set(doc["paths"][path]) == {"get"}, path
        params = {p["name"] for p in doc["paths"][path]["get"]["parameters"]}
        assert "model_name" in params and "x-api-key" in params, path
        if path == "/api/prs":
            assert "limit" in params, path


def test_prs_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/prs")
    assert _keys(doc, data) == {"items", "model_name", "skipped"}
    assert _keys(doc, data["properties"]["items"]["items"]) == {
        "number",
        "title",
        "author",
        "state",
        "html_url",
        "updated_at",
        "risk_score",
        "risk_level",
        "reason",
        "commit_count",
        "predicted_count",
        "predicted_at",
    }


def test_pr_detail_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/prs/{number}")
    assert _keys(doc, data) == {
        "number",
        "title",
        "author",
        "state",
        "html_url",
        "updated_at",
        "model_name",
        "commits",
    }
    assert _keys(doc, data["properties"]["commits"]["items"]) == {
        "sha",
        "message",
        "author",
        "risk_score",
        "risk_level",
        "predicted_at",
    }


def test_sync_prs_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/sync-prs", "post")
    assert _keys(doc, data) == {"prs_scanned", "commits_predicted", "prs", "skipped"}


def _data_props(client, path, method="get"):
    doc = _schema(client)
    schema = doc["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
    resp = doc["components"]["schemas"][schema["$ref"].split("/")[-1]]
    data = resp["properties"]["data"]
    if "$ref" in data:
        data = doc["components"]["schemas"][data["$ref"].split("/")[-1]]
    return doc, data


def _keys(doc, node):
    if "$ref" in node:
        node = doc["components"]["schemas"][node["$ref"].split("/")[-1]]
    return set(node["properties"])


def test_commits_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/commits")
    assert _keys(doc, data) == {"total", "page", "size", "items"}
    assert _keys(doc, data["properties"]["items"]["items"]) == {
        "commit_hash",
        "author_name",
        "committed_at",
        "message",
        "risk_score",
        "model_name",
    }


def test_detail_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/commits/{commit_hash}")
    assert _keys(doc, data) == {
        "commit_hash",
        "author_name",
        "committed_at",
        "message",
        "risk_score",
        "model_name",
        "features",
        "explanation",
        "label",
    }


def test_trends_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/trends")
    assert _keys(doc, data) == {"granularity", "model_name", "series"}
    assert _keys(doc, data["properties"]["series"]["items"]) == {
        "period",
        "commit_count",
        "avg_risk",
        "high_risk_count",
    }


def test_predict_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/predict", "post")
    assert _keys(doc, data) == {
        "commit_hash",
        "model_name",
        "risk_score",
        "predicted_at",
        "features",
        "explanation",
    }


def test_quality_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/quality")
    assert _keys(doc, data) == {
        "model_name",
        "threshold",
        "labeled_total",
        "evaluated",
        "tp",
        "fp",
        "tn",
        "fn",
        "precision",
        "recall",
        "f1",
        "accuracy",
        "avg_risk_defect",
        "avg_risk_clean",
        "recommended_threshold",
        "evaluated_at",
    }


def test_quality_dataset_fields_match_contract(client):
    doc, data = _data_props(client, "/api/quality/dataset")
    assert _keys(doc, data) == {"count", "items"}
    assert _keys(doc, data["properties"]["items"]["items"]) == {
        "commit_hash",
        "is_defect",
        "labeled_at",
        "committed_at",
        "features",
    }


def test_calibrate_fields_match_contract(client):
    doc, data = _data_props(client, "/api/quality/calibrate", "post")
    assert _keys(doc, data) == {
        "model_name",
        "labeled_total",
        "evaluated",
        "applied",
        "reason",
        "before",
        "after",
    }
    for key in ("before", "after"):
        assert _keys(doc, data["properties"][key]) == {"threshold", "precision", "recall", "f1"}


def test_config_supports_get_and_put(client):
    """阈值既读也写：GET 查看、PUT 热更新（change ops-hardening）。"""
    assert set(_schema(client)["paths"]["/api/config"]) == {"get", "put"}


def test_config_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/config")
    assert _keys(doc, data) == {
        "high_risk_threshold",
        "mid_risk_threshold",
        "sync_initial_limit",
        "sync_catchup_limit",
        "updated_at",
    }


def test_live_and_ready_fields_match_contract(client):
    doc, live = _data_props(client, "/api/health/live")
    assert _keys(doc, live) == {"status", "server_time"}
    doc, ready = _data_props(client, "/api/health/ready")
    assert _keys(doc, ready) == {"status", "db", "models_loaded", "server_time"}


def test_pr_gate_fields_match_contract(client):
    doc, data = _data_props(client, "/api/prs/{number}/gate")
    assert _keys(doc, data) == {
        "number",
        "model_name",
        "risk_score",
        "risk_level",
        "threshold",
        "blocked",
        "reason",
    }


def test_webhook_fields_match_contract(client):
    doc, data = _data_props(client, "/api/webhook/github", "post")
    assert _keys(doc, data) == {"accepted", "event", "action", "triggered"}
