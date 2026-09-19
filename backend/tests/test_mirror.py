"""Swagger 实现镜像（tasks 5.1）：openapi 路径与参数名逐字对齐契约三 1.4。"""

from tests.conftest import HEADERS


def _schema(client):
    return client.get("/openapi.json", headers=HEADERS).json()


def test_paths_match_contract(client):
    paths = set(_schema(client)["paths"])
    assert paths == {"/api/commits", "/api/commits/{commit_hash}", "/api/trends", "/api/predict"}


def test_commits_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/commits"]["get"]["parameters"]}
    assert {"page", "size", "min_risk", "model_name", "start_time", "end_time"} <= params


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
    return set(node["properties"])


def test_commits_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/commits")
    assert _keys(doc, data) == {"total", "page", "size", "items"}
    assert _keys(doc, data["properties"]["items"]["items"]) == {
        "commit_hash", "author_name", "committed_at", "message", "risk_score", "model_name",
    }


def test_detail_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/commits/{commit_hash}")
    assert _keys(doc, data) == {
        "commit_hash", "author_name", "committed_at", "message",
        "risk_score", "model_name", "features", "explanation",
    }


def test_trends_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/trends")
    assert _keys(doc, data) == {"granularity", "model_name", "series"}
    assert _keys(doc, data["properties"]["series"]["items"]) == {
        "period", "commit_count", "avg_risk", "high_risk_count",
    }


def test_predict_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/predict", "post")
    assert _keys(doc, data) == {
        "commit_hash", "model_name", "risk_score", "predicted_at", "features", "explanation",
    }
