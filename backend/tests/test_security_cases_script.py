"""`scripts/security_cases.py` 的回归测试（#113 复审要求：不依赖外部服务）。

用假的 httpx.Client 驱动 `main()`，钉住四件事：
传 `--mask-url` 且掩码服务回 500/50000 → 证据表出 PASS 行且 rc=0；
回 404（哈希不存在）或库空 → FAIL 行且 rc=1（掩码失败必须进 rc，不许静默通过）；
不传 `--mask-url` → 「未测」行且 rc=0。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "security_cases.py"
BASE = "http://base"
MASK = "http://mask"
HASH40 = "a" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location("security_cases_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeResp:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict:
        return self._payload


class FakeClient:
    def __init__(self, routes, *args, **kwargs):
        self._routes = routes

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, headers=None):
        return self._routes("GET", url, params)

    def post(self, url, json=None, headers=None):
        return self._routes("POST", url, json)


def _make_routes(mask_list_items, mask_post):
    def routes(method, url, arg):
        if url.startswith(MASK):
            if method == "GET":
                return FakeResp(
                    200,
                    {
                        "code": 0,
                        "message": "ok",
                        "data": {"items": mask_list_items, "total": len(mask_list_items)},
                    },
                )
            return mask_post()
        if method == "POST":
            return FakeResp(200, {"code": 0, "message": "ok", "data": {}})
        if "size=101" in url or (arg or {}).get("size") == 101:
            return FakeResp(
                400, {"code": 40001, "message": "参数非法：size 超过上限 100", "data": None}
            )
        if "/api/trends" in url:
            return FakeResp(
                400,
                {
                    "code": 40001,
                    "message": "参数非法：granularity 取值需为 week 或 month",
                    "data": None,
                },
            )
        if url.rstrip("/").endswith("/api/commits"):
            return FakeResp(
                401, {"code": 40100, "message": "missing or invalid token", "data": None}
            )
        return FakeResp(
            400,
            {"code": 40001, "message": "参数非法：commit_hash 需为 40 位十六进制", "data": None},
        )

    return routes


def _run(monkeypatch, tmp_path, argv_extra):
    mod = _load_module()
    monkeypatch.setenv("API_TOKEN", "dev-token")
    monkeypatch.setattr(
        sys,
        "argv",
        ["security_cases.py", "--base-url", BASE, *argv_extra, "--out", str(tmp_path / "out.md")],
    )
    return mod, tmp_path


@pytest.fixture()
def base_items():
    return [{"commit_hash": HASH40}]


def test_mask_50000_passes_row_and_rc(monkeypatch, tmp_path, base_items):
    mod, tmp = _run(monkeypatch, tmp_path, ["--mask-url", MASK])
    monkeypatch.setattr(
        mod.httpx,
        "Client",
        lambda **kw: FakeClient(
            _make_routes(
                base_items,
                lambda: FakeResp(500, {"code": 50000, "message": "internal error", "data": None}),
            )
        ),
    )
    rc = mod.main()
    text = (tmp / "out.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "| 50000 掩码（注册表为空，--mask-url 实测） | PASS |" in text
    assert "HTTP 500 code=50000 message=internal error" in text


def test_mask_404_fails_row_and_rc(monkeypatch, tmp_path, base_items):
    mod, tmp = _run(monkeypatch, tmp_path, ["--mask-url", MASK])
    monkeypatch.setattr(
        mod.httpx,
        "Client",
        lambda **kw: FakeClient(
            _make_routes(
                base_items,
                lambda: FakeResp(404, {"code": 40400, "message": "commit not found", "data": None}),
            )
        ),
    )
    rc = mod.main()
    text = (tmp / "out.md").read_text(encoding="utf-8")
    assert rc == 1, "掩码 FAIL 必须进 rc，禁止静默通过"
    assert "| 50000 掩码（注册表为空，--mask-url 实测） | FAIL |" in text
    assert "存在 FAIL" in text


def test_mask_empty_db_fails_row_and_rc(monkeypatch, tmp_path):
    mod, tmp = _run(monkeypatch, tmp_path, ["--mask-url", MASK])
    monkeypatch.setattr(
        mod.httpx,
        "Client",
        lambda **kw: FakeClient(
            _make_routes(
                [],
                lambda: FakeResp(500, {"code": 50000, "message": "internal error", "data": None}),
            )
        ),
    )
    rc = mod.main()
    text = (tmp / "out.md").read_text(encoding="utf-8")
    assert rc == 1
    assert "| FAIL |" in text and "库中无提交" in text


def test_without_mask_url_row_is_untested_and_rc0(monkeypatch, tmp_path):
    mod, tmp = _run(monkeypatch, tmp_path, [])
    monkeypatch.setattr(
        mod.httpx,
        "Client",
        lambda **kw: FakeClient(
            _make_routes(
                [],
                lambda: FakeResp(500, {"code": 50000, "message": "internal error", "data": None}),
            )
        ),
    )
    rc = mod.main()
    text = (tmp / "out.md").read_text(encoding="utf-8")
    assert rc == 0
    assert "| 50000 掩码（注册表为空） | 未测 |" in text
    assert "evidence-5.3-mysql" not in text, "悬空引用不得回潮"
