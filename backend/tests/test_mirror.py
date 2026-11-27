# === AI 辅助说明 ===
# 本文件共 15 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：15 条（AI 生成骨架，人工补充核心断言）
# [手写]：0 条
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/test/unit_test/prompts/README.md

"""Swagger 实现镜像：openapi 路径与参数名逐字对齐 docs/api/*。

路径集是「一条不多一条不少」的精确断言 —— 新增端点必须同步改这里，
不允许静默多出路径（PR / 质量 / 反馈 / webhook / 运行时配置已下线）。
"""

from tests.conftest import HEADERS

CONTRACT_PATHS = {
    "/api/algorithms",
    "/api/clean/operations",
    "/api/clean/outputs/{job_id}/{name}",
    "/api/clean/preview/{job_id}",
    "/api/clean/run",
    "/api/collect/branches",
    "/api/collect/outputs/{job_id}/{name}",
    "/api/collect/preview/{job_id}",
    "/api/collect/resave/{job_id}",
    "/api/collect/run",
    "/api/collect/source-columns",
    "/api/commits",
    "/api/commits/{commit_hash}",
    "/api/config",
    "/api/config/{key}",
    "/api/datasets",
    "/api/datasets/outputs/{job_id}/{name}",
    "/api/datasets/{dataset_id}",
    "/api/datasets/{dataset_id}/commits",
    "/api/datasets/{dataset_id}/export",
    "/api/evaluate/metrics",
    "/api/evaluate/outputs/{job_id}/{name}",
    "/api/evaluate/run",
    "/api/explain",
    "/api/explain/outputs/{job_id}/{name}",
    "/api/explain/run",
    "/api/explain/techniques",
    "/api/figures",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/jobs",
    "/api/jobs/{job_id}",
    "/api/jobs/{job_id}/cancel",
    "/api/jobs/{job_id}/retry",
    "/api/localize/outputs/{job_id}/{name}",
    "/api/localize/run",
    "/api/models",
    "/api/models/default",
    "/api/models/selection",
    "/api/models/status",
    "/api/models/{name}/load",
    "/api/models/{name}/reload",
    "/api/models/{name}/unload",
    "/api/predict",
    "/api/predict/outputs/{job_id}/{name}",
    "/api/predict/preview/{job_id}",
    "/api/predict/run",
    "/api/source/file",
    "/api/source/tree",
    "/api/storage/chains/{chain_id}",
    "/api/storage/export",
    "/api/storage/import",
    "/api/storage/lineage",
    "/api/storage/outputs/{job_id}/{name}",
    "/api/storage/tables",
    "/api/sync",
    "/api/sync/status",
    "/api/train/outputs/{job_id}/{name}",
    "/api/train/run",
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
    assert "with_features" in params
    assert "is_test" not in params
    assert "min_risk" not in params and "has_label" not in params


def test_models_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/models"]["get"]["parameters"]}
    assert "line" in params


def test_figures_params_match_contract(client):
    params = {p["name"] for p in _schema(client)["paths"]["/api/figures"]["get"]["parameters"]}
    assert {"model_name", "figure_type", "job_id"} <= params


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
        "repo_name",
        "author_name",
        "committed_at",
        "message",
        "risk_score",
        "model_name",
        "predicted_at",
        "predicted_label",
        "features",
        "is_bug_inducing",
        "label_method",
        "labeled_at",
    }


def test_detail_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/commits/{commit_hash}")
    assert _keys(doc, data) == {
        "commit_hash",
        "repo_name",
        "author_name",
        "committed_at",
        "message",
        "risk_score",
        "model_name",
        "predicted_at",
        "features",
        "summary",
        "is_bug_inducing",
        "label_method",
        "labeled_at",
        "prediction",
    }


def test_predict_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/predict", "post")
    assert _keys(doc, data) == {
        "commit_hash",
        "model_name",
        "risk_score",
        "predicted_at",
        "features",
        "summary",
        "predicted_label",
        "decision_threshold",
        "risk_level",
        "model_version",
        "feature_version",
        "result_source",
        "stale",
    }


def test_models_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/models")
    assert _keys(doc, data) == {"lines"}
    assert _keys(doc, data["properties"]["lines"]["items"]) == {"line", "label", "models"}


def test_figures_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/figures")
    assert _keys(doc, data) == {
        "model_name",
        "line",
        "source_job_id",
        "batches",
        "metrics",
        "metrics_unavailable",
        "figures",
        "missing",
    }
    assert _keys(doc, data["properties"]["batches"]["items"]) == {
        "job_id", "created_at", "testset_ref", "figures_count",
    }
    assert _keys(doc, data["properties"]["figures"]["items"]) == {
        "figure_type",
        "effort_kind",
        "title",
        "figure_name",
        "file_path",
        "checksum_sha256",
        "source_job_id",
    }
    # §3.6 指标长表：逐模型逐指标一行，不是旧的 8 字段宽表对象。
    assert _keys(doc, data["properties"]["metrics"]["items"]) == {
        "model_name",
        "line",
        "metric",
        "value",
        "threshold",
        "n",
        "pos_rate",
        "dataset_version",
        "model_version",
        "computed_at",
    }
    # 缺图/校验失败改为对象数组，逐项给出 figure_type/file_path/reason。
    assert _keys(doc, data["properties"]["missing"]["items"]) == {
        "figure_type",
        "file_path",
        "reason",
    }


def test_health_response_fields_match_contract(client):
    doc, data = _data_props(client, "/api/health")
    assert _keys(doc, data) == {
        "status",
        "db",
        "models_loaded",
        "model_names",
        "catalog_count",
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
