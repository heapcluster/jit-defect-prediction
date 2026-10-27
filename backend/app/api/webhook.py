"""GitHub webhook 接入（change ops-hardening）：事件驱动，替代手动点同步。

鉴权说明：GitHub 发不出 `X-API-Key`，故本路由**不走 API key 鉴权**，改由
`X-Hub-Signature-256`（HMAC-SHA256 + `WEBHOOK_SECRET`）保证来源可信 —— 契约 §四
「所有接口均需鉴权」依然成立，只是机制从令牌换成签名。`WEBHOOK_SECRET` 未配置时
一律拒绝（fail closed），避免误开无验签入口。

触发语义：同步是分钟级操作，webhook 必须**立即返回 202/200**，实际同步丢后台线程；
并发由 `sync._sync_lock` 兜底（重复事件会被拒，只记日志）。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading

from fastapi import APIRouter, Header, Request

from app import config, schemas
from app.api import prs as prs_api
from app.api import sync as sync_api
from app.errors import AppError, ok

# 注意：无 Depends(require_api_key) —— 由 HMAC 验签替代令牌
router = APIRouter()
logger = logging.getLogger("backend.webhook")

# 只在 PR 内容真正变化时重算，避免 labeled/edited 等事件造成无谓同步
PR_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}


def verify_signature(raw: bytes, signature: str | None, secret: str) -> bool:
    """常数时间比对 HMAC-SHA256 签名。"""
    if not secret or not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _spawn(target, **kwargs) -> None:
    """后台派发（单独抽出来是为了测试能替换成同步执行）。"""
    threading.Thread(target=target, kwargs=kwargs, daemon=True, name="webhook-dispatch").start()


def _run_sync() -> None:
    try:
        sync_api.sync_recent(config.WEBHOOK_SYNC_LIMIT, mode="webhook", scope="latest")
    except Exception:  # noqa: BLE001 —— 后台线程不能把异常抛给请求
        logger.exception("webhook push 同步失败")


def _run_sync_prs() -> None:
    try:
        prs_api.sync_prs(1)
    except Exception:  # noqa: BLE001
        logger.exception("webhook pull_request 同步失败")


@router.post("/api/webhook/github", response_model=schemas.WebhookResponse)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
) -> dict:
    if not config.WEBHOOK_SECRET:
        raise AppError(40100, "webhook secret not configured")
    raw = await request.body()
    if not verify_signature(raw, x_hub_signature_256, config.WEBHOOK_SECRET):
        raise AppError(40100, "invalid webhook signature")
    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise AppError(40001, "参数非法：请求体需为 JSON") from None
    if not isinstance(payload, dict):
        raise AppError(40001, "参数非法：请求体需为 JSON 对象")

    event = x_github_event or ""
    action = payload.get("action")
    triggered = False
    if event == "push":
        _spawn(_run_sync)
        triggered = True
    elif event == "pull_request" and action in PR_TRIGGER_ACTIONS:
        _spawn(_run_sync_prs)
        triggered = True
    return ok(
        {
            "accepted": True,
            "event": event or None,
            "action": action,
            "triggered": triggered,
        }
    )
