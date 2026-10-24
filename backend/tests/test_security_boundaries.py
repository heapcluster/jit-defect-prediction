"""安全与边界输入用例（T-NF-02 扩展；原安全仅两组：缺令牌 / 畸形参数）。

课程测试要求「对每个核心功能给出正向验收和至少一个异常/无效输入验证」，
且 50000 的 message 不得回显堆栈 / SQL / 文件路径（契约三 §二）。
本文件把安全用例从两组扩到：鉴权边界 + 四类参数边界 + 信息泄露断言。

口径来源：`backend/api-spec.md` §一（鉴权）/ §二（错误码）/ §三（四接口参数）。
跑法：`cd backend && python -m pytest -q`
"""

from __future__ import annotations

import pytest

from app.errors import INTERNAL_ERROR_MESSAGE

HEADERS = {"X-API-Key": "test-token"}
GOOD_HASH = "a" * 40

# 四个接口一律适用鉴权（契约三 §一：「四个接口一律适用，预测接口不例外」）
ALL_ENDPOINTS = [
    ("GET", "/api/commits"),
    ("GET", f"/api/commits/{GOOD_HASH}"),
    ("GET", "/api/trends"),
    ("POST", "/api/predict"),
]


# ────────────────────────── 鉴权边界 ──────────────────────────

@pytest.mark.parametrize("method,path", ALL_ENDPOINTS)
def test_all_four_endpoints_require_token(client, method, path):
    """缺令牌时四个接口都必须 40100，预测接口不例外。"""
    resp = client.request(method, path, json={"commit_hash": GOOD_HASH} if method == "POST" else None)
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


@pytest.mark.parametrize(
    "bad_token",
    [
        "",
        " ",
        " test-token",          # 前导空白不算通过
        "test-token ",          # 尾随空白不算通过
        "TEST-TOKEN",           # 大小写敏感
        "test-token-extra",     # 超长
        "test",                 # 前缀
    ],
)
def test_token_must_match_exactly(client, bad_token):
    """令牌为精确字符串比较（app/auth.py），任何偏差一律 40100。"""
    resp = client.get("/api/commits", headers={"X-API-Key": bad_token})
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100
    assert resp.json()["message"] == "missing or invalid token"


def test_token_error_does_not_reveal_which_char_is_wrong(client):
    """契约三鉴权细则：不提示令牌哪一位错。"""
    resp = client.get("/api/commits", headers={"X-API-Key": "test-tokeX"})
    assert resp.json()["message"] == "missing or invalid token"


# ────────────────────────── 查询参数边界（GET /api/commits） ──────────────────────────

@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=abc",             # 非整数 → RequestValidationError → 40001
        "size=0",
        "size=101",             # 超过上限 100
        "size=-5",
        "min_risk=1.5",         # 超出 0.0~1.0
        "min_risk=-0.1",
        "start_time=not-a-time",
        "end_time=2026-13-45",  # 月/日越界
    ],
)
def test_commits_query_boundaries_return_40001(client, query):
    resp = client.get(f"/api/commits?{query}", headers=HEADERS)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 40001
    assert body["data"] is None


@pytest.mark.parametrize(
    "query",
    [
        "page=1&size=100",      # 上限值本身合法
        "min_risk=0.0",         # 下界值合法
        "min_risk=1.0",         # 上界值合法
        "start_time=2026-09-16T08:30:00Z",  # 合法 ISO 8601 带时区
    ],
)
def test_commits_query_boundary_values_are_accepted(client, query):
    """边界值本身不误判为非法（防止校验写过头）。"""
    resp = client.get(f"/api/commits?{query}", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ────────────────────────── 详情 / 预测 / 趋势 边界 ──────────────────────────

@pytest.mark.parametrize(
    "bad_hash",
    [
        "short",                       # 长度不足
        "a" * 39,                      # 39 位
        "a" * 41,                      # 41 位
        "g" * 40,                      # 非十六进制
        "G" * 40,                      # 非十六进制（大写形式同样拒收，归一化不放宽校验）
        "A" * 40 + "!",                # 含符号
    ],
)
def test_detail_hash_boundaries_return_40001(client, bad_hash):
    resp = client.get(f"/api/commits/{bad_hash}", headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_detail_uppercase_hash_is_normalized_to_the_stored_commit(client):
    """D-09 修复：大写/混合大小写哈希归一化后命中库内同一提交。

    旧行为是「过校验却 40400 commit not found」—— ``_check_hash`` 先 ``lower()``
    放行大写，``commit_detail`` 却用原样字符串匹配库内小写哈希。
    """
    baseline = client.get(f"/api/commits/{GOOD_HASH}", headers=HEADERS)
    assert baseline.status_code == 200
    for variant in (GOOD_HASH.upper(), GOOD_HASH.title()):
        assert variant != GOOD_HASH
        resp = client.get(f"/api/commits/{variant}", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert resp.json()["data"] == baseline.json()["data"]
        assert resp.json()["data"]["commit_hash"] == GOOD_HASH


def test_detail_unknown_hash_stays_40400_after_normalization(client):
    """归一化只改大小写：库内没有的哈希仍是 40400，不得改判 40001、不得误命中。"""
    unknown = "d" * 40
    for variant in (unknown, unknown.upper()):
        resp = client.get(f"/api/commits/{variant}", headers=HEADERS)
        assert resp.status_code == 404
        assert resp.json()["code"] == 40400
        assert resp.json()["message"] == "commit not found"


@pytest.mark.parametrize(
    "payload",
    [
        {},                                  # 缺 commit_hash
        {"commit_hash": ""},                 # 空哈希
        {"commit_hash": "short"},            # 非 40 位
        {"commit_hash": "z" * 40},           # 非十六进制
        {"commit_hash": GOOD_HASH, "model_name": "nope_v1"},  # 模型不在清单
    ],
)
def test_predict_boundaries_return_40001(client, payload):
    resp = client.post("/api/predict", headers=HEADERS, json=payload)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


@pytest.mark.parametrize("granularity", ["day", "year", "WEEK", "", "week "])
def test_trends_granularity_boundary_return_40001(client, granularity):
    resp = client.get(f"/api/trends?granularity={granularity}", headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


def test_trends_time_boundary_return_40001(client):
    resp = client.get("/api/trends?start_time=yesterday", headers=HEADERS)
    assert resp.status_code == 400
    assert resp.json()["code"] == 40001


# ────────────────────────── 信息泄露断言 ──────────────────────────

@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/api/commits?page=0", None),
        ("GET", "/api/commits/short", None),
        ("GET", "/api/trends?granularity=day", None),
        ("POST", "/api/predict", {"commit_hash": "short"}),
    ],
)
def test_error_responses_do_not_leak_internals(client, method, path, payload):
    """契约三 §二：40001/40100 的响应体不得出现堆栈、SQL 片段或文件路径。"""
    resp = client.request(method, path, headers=HEADERS, json=payload)
    text = resp.text
    for leak in ("Traceback", "SELECT ", "sqlalchemy", ".py", "C:\\", "site-packages"):
        assert leak not in text, f"响应体泄露内部信息：{leak}"


def test_internal_error_message_is_generic():
    """50000 的 message 固定为通用文案，细节只进服务端日志（app/errors.py）。"""
    assert INTERNAL_ERROR_MESSAGE == "internal error"
