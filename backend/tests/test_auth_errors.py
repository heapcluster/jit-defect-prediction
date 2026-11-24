# === AI 辅助说明 ===
# 本文件共 7 条测试用例
# [AI生成]：0 条
# [AI生成-人工修改]：0 条
# [手写]：7 条（核心业务断言由人工编写）
# 使用工具：原始生成记录未归档（标注依据代码特征判断，作者于 2026-11-17 确认）
# 提示词见：docs/想到什么取什么/unit_test/prompts/README.md

import pytest
from app import config
from app.auth import MISSING_OR_INVALID_TOKEN, require_api_key
from app.errors import AppError


def test_missing_token(client):
    resp = client.get("/api/commits")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 40100
    assert body["message"] == MISSING_OR_INVALID_TOKEN


def test_invalid_token(client):
    resp = client.get("/api/commits", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_envelope_on_success(client):
    resp = client.get("/api/commits", headers={"X-API-Key": "test-token"}, params={"model_name": "fixture_v2"})
    body = resp.json()
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert "items" in body["data"]


def test_require_api_key_accepts_matching_token():
    """正常：与配置一致的令牌直接放行，不抛异常。"""
    require_api_key(config.API_TOKEN)  # 不抛即通过


def test_require_api_key_rejects_missing_token():
    """异常：未传令牌 → 40100。"""
    with pytest.raises(AppError) as exc:
        require_api_key(None)
    assert exc.value.code == 40100
    assert exc.value.message == MISSING_OR_INVALID_TOKEN


def test_require_api_key_rejects_wrong_token():
    """异常：令牌不匹配 → 40100。"""
    with pytest.raises(AppError) as exc:
        require_api_key("wrong-token")
    assert exc.value.code == 40100


def test_require_api_key_fails_closed_when_token_not_configured(monkeypatch):
    """异常：服务端未配置 API_TOKEN 时，即使请求方传空串也拒绝（fail closed）。"""
    monkeypatch.setattr(config, "API_TOKEN", "")
    with pytest.raises(AppError) as exc:
        require_api_key("")
    assert exc.value.code == 40100
