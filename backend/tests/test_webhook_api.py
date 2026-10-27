"""GitHub webhook（change ops-hardening）：HMAC 验签与事件派发。

webhook 不走 X-API-Key（GitHub 发不出），改由签名鉴权；这里覆盖
未配置密钥、签名错误、ping、push、pull_request 五条分支。
"""

from __future__ import annotations

import hashlib
import hmac

from app import config
from tests.conftest import HEADERS

URL = "/api/webhook/github"
SECRET = "s3cr3t"


def _sign(raw: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _post(client, raw: bytes, event: str, signature: str | None = None):
    headers = {"X-GitHub-Event": event, "Content-Type": "application/json"}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    return client.post(URL, content=raw, headers=headers)


def test_webhook_rejected_when_secret_not_configured(client, monkeypatch):
    """未配置 WEBHOOK_SECRET 时 fail closed，避免误开无验签入口。"""
    monkeypatch.setattr(config, "WEBHOOK_SECRET", "")
    resp = _post(client, b'{"zen": "hi"}', "ping")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_webhook_rejects_bad_signature(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    raw = b'{"zen": "hi"}'
    resp = _post(client, raw, "ping", _sign(b"tampered"))
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_webhook_rejects_missing_signature(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    resp = _post(client, b"{}", "ping")
    assert resp.status_code == 401
    assert resp.json()["code"] == 40100


def test_webhook_ping_is_accepted_but_not_triggered(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    raw = b'{"zen": "Keep it logically awesome."}'
    resp = _post(client, raw, "ping", _sign(raw))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["accepted"] is True
    assert data["event"] == "ping"
    assert data["triggered"] is False


def test_webhook_push_triggers_sync(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    called: dict = {}
    monkeypatch.setattr(
        "app.api.webhook.sync_api.sync_recent",
        lambda limit, mode=None, scope=None: called.update(limit=limit, mode=mode),
    )
    # 后台线程换成同步执行，测试才能断言
    monkeypatch.setattr("app.api.webhook._spawn", lambda target, **kw: target(**kw))

    raw = b'{"ref": "refs/heads/main"}'
    data = _post(client, raw, "push", _sign(raw)).json()["data"]
    assert data["triggered"] is True
    assert called["limit"] == config.WEBHOOK_SYNC_LIMIT
    assert called["mode"] == "webhook"


def test_webhook_pull_request_opened_triggers_pr_sync(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    called: dict = {}
    monkeypatch.setattr(
        "app.api.webhook.prs_api.sync_prs", lambda limit=1: called.update(limit=limit)
    )
    monkeypatch.setattr("app.api.webhook._spawn", lambda target, **kw: target(**kw))

    raw = b'{"action": "opened", "number": 42}'
    data = _post(client, raw, "pull_request", _sign(raw)).json()["data"]
    assert data["triggered"] is True
    assert data["action"] == "opened"
    assert called["limit"] == 1


def test_webhook_ignores_unrelated_pull_request_action(client, monkeypatch):
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    raw = b'{"action": "labeled", "number": 42}'
    data = _post(client, raw, "pull_request", _sign(raw)).json()["data"]
    assert data["triggered"] is False


def test_webhook_does_not_require_api_key(client, monkeypatch):
    """签名是唯一凭据：带签名时不要求 X-API-Key。"""
    monkeypatch.setattr(config, "WEBHOOK_SECRET", SECRET)
    raw = b'{"zen": "hi"}'
    resp = client.post(
        URL,
        content=raw,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": _sign(raw),
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert "X-API-Key" not in resp.request.headers or resp.request.headers.get(
        "X-API-Key"
    ) is None
    assert HEADERS["X-API-Key"]  # 仅说明普通端点仍需令牌
