"""Swagger 实现镜像（tasks 5.1）：openapi 路径与参数名逐字对齐契约三 v1.2。"""

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
