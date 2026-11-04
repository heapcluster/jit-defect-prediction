"""Swagger 实现镜像：openapi 路径与参数名逐字对齐 docs/api/*。

路径集是「一条不多一条不少」的精确断言 —— 新增端点必须同步改这里，
不允许静默多出路径（PR / 质量 / 反馈 / webhook / 运行时配置已下线）。
"""

from tests.conftest import HEADERS

CONTRACT_PATHS = {
    "/api/commits",
    "/api/commits/{commit_hash}",
    "/api/models",
    "/api/trends",
    "/api/predict",
    "/api/sync",
    "/api/sync/status",
    "/api/figures",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
}


def _schema(client):
    return client.get("/openapi.json", headers=HEADERS).json()


def test_paths_match_contract(client):
    paths = set(_schema(client)["paths"])
    assert paths == CONTRACT_PATHS


def test_sync_params_match_contract(client):
    doc = _schema(client)
    assert "post" in doc["paths"]["/api/sync"]
    params = {p["name"] for p in doc["paths"]["/api/sync"]["post"]["parameters"]}
    assert {"line", "model_name", "start_time", "end_time"} <= params
    assert "limit" not in params


def test_commits_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/commits"]["get"]["parameters"]}
    assert {"page", "size", "model_name", "start_time", "end_time", "q"} <= params
    assert {"with_features", "is_test"} <= params
    assert "min_risk" not in params and "has_label" not in params


def test_models_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/models"]["get"]["parameters"]}
    assert "line" in params


def test_figures_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/figures"]["get"]["parameters"]}
    assert "model_name" in params


def test_trends_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/trends"]["get"]["parameters"]}
    assert {"granularity", "start_time", "end_time", "model_name"} <= params


def test_predict_is_post(client):
    assert "post" in _schema(client)["paths"]["/api/predict"]


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
    elif "anyOf" in node:
        # 可空字段（如 figures.metrics: MetricsData | None）以 anyOf[$ref, null] 表达
        refs = [o for o in node["anyOf"] if "$ref" in o]
        if refs:
            node = doc["components"]["schemas"][refs[0]["$ref"].split("/")[-1]]
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
        "features",
        "is_bug_inducing",
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
        "predicted_at",
        "features",
        "explanation",
        "is_bug_inducing",
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


def test_models_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/models")
    assert _keys(doc, data) == {"lines"}
    assert _keys(doc, data["properties"]["lines"]["items"]) == {"line", "label", "models"}


def test_figures_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/figures")
    assert _keys(doc, data) == {"model_name", "line", "metrics", "figures"}
    assert _keys(doc, data["properties"]["figures"]["items"]) == {
        "figure_type",
        "title",
        "file_path",
    }
    assert _keys(doc, data["properties"]["metrics"]) == {
        "auc",
        "ap",
        "f1",
        "precision",
        "recall",
        "accuracy",
        "n",
        "pos_rate",
    }


def test_health_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/health")
    assert _keys(doc, data) == {
        "status",
        "db",
        "models_loaded",
        "model_names",
        "commit_count",
        "prediction_count",
        "last_sync_at",
        "server_time",
    }


def test_live_and_ready_fields_match_contract(client):
    doc, live = _data_props(client, "/api/health/live")
    assert _keys(doc, live) == {"status", "server_time"}
    doc, ready = _data_props(client, "/api/health/ready")
    assert _keys(doc, ready) == {"status", "db", "models_loaded", "server_time"}
