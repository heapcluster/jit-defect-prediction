"""GitHub webhook 接入（change ops-hardening）：事件驱动，替代手动点同步。

鉴权说明：GitHub 发不出 `X-API-Key`，故本路由**不走 API key 鉴权**，改由
`X-Hub-Signature-256`（HMAC-SHA256 + `WEBHOOK_SECRET`）保证来源可信 —— 契约 §四
「所有接口均需鉴权」依然成立，只是机制从令牌换成签名。`WEBHOOK_SECRET` 未配置时
一律拒绝（fail closed），避免误开无验签入口。

触发语义：同步是分钟级操作，webhook 必须**立即返回 200**，实际同步丢后台线程；
并发由 `services.sync_state._sync_lock` 兜底（已在跑时本次派发直接跳过并记 info）。

去重语义：GitHub 在超时/5xx 时会重投同一 `X-GitHub-Delivery`，故按投递 id 判重。
判定与登记**必须分开**：只有「已成功受理」的投递才登记，否则「处理失败 → 返回 5xx →
GitHub 重投」会被自己的缓存判成重复而静默丢弃（事件永久丢失）。
缓存是进程内的（最近 256 条），多 worker 部署时每个 worker 各持一份，跨进程去重不成立。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
from collections import OrderedDict

from fastapi import APIRouter, Header, Request

from app import config, schemas
from app.api import prs as prs_api
from app.api import sync as sync_api
from app.errors import AppError, ok
from app.services import sync_state

# 注意：无 Depends(require_api_key) —— 由 HMAC 验签替代令牌
router = APIRouter()
logger = logging.getLogger("backend.webhook")

# 只在 PR 内容真正变化时重算，避免 labeled/edited 等事件造成无谓同步
PR_TRIGGER_ACTIONS = {"opened", "synchronize", "reopened"}

# 投递去重：GitHub 在超时/5xx 时会重投同一 X-GitHub-Delivery。
# 进程内保留最近 256 个投递 id（重启丢失可接受：重投窗口远短于进程生命周期）。
# 多 worker 部署时各自独立，去重只在单进程内有效 —— 需要跨进程去重时改落 DB/Redis。
_DELIVERY_CACHE: OrderedDict[str, None] = OrderedDict()
_DELIVERY_CACHE_MAX = 256
_DELIVERY_LOCK = threading.Lock()


def _is_duplicate(delivery_id: str | None) -> bool:
    """只读判定：True = 同一次投递已成功受理过。缺 id 时不判重（兼容手工 curl）。"""
    if not delivery_id:
        return False
    with _DELIVERY_LOCK:
        return delivery_id in _DELIVERY_CACHE


def _remember_delivery(delivery_id: str | None) -> None:
    """登记一次「已成功受理」的投递；MUST 在处理成功之后调用（失败不登记，允许重投）。

    与 `_is_duplicate` 拆开是为了避免「先占位后失败」把重投判成重复而丢事件。
    """
    if not delivery_id:
        return
    with _DELIVERY_LOCK:
        _DELIVERY_CACHE[delivery_id] = None
        _DELIVERY_CACHE.move_to_end(delivery_id)
        while len(_DELIVERY_CACHE) > _DELIVERY_CACHE_MAX:
            _DELIVERY_CACHE.popitem(last=False)


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
    if sync_state.get_sync_state()["running"]:
        # 已经在跑（首启基线 / 手动同步 / 上一条 webhook）：本次派发让位，不当失败记录
        logger.info("同步已在运行，跳过本次 webhook push 触发的增量同步")
        return
    try:
        sync_api.sync_recent(config.WEBHOOK_SYNC_LIMIT, mode="webhook", scope="latest")
    except AppError as exc:
        if exc.code == 50000:
            # 互斥锁被抢占（状态快照与抢锁之间的竞态）：同样只是让位
            logger.info("同步互斥锁被占用，跳过本次 webhook push 触发的增量同步")
            return
        logger.exception("webhook push 同步失败")
    except Exception:  # noqa: BLE001 —— 后台线程不能把异常抛给请求
        logger.exception("webhook push 同步失败")


def _run_sync_prs() -> None:
    try:
        # 上限可配（WEBHOOK_PR_LIMIT，默认 1）：一次 PR 事件只刷新最新那批 open PR，
        # 避免为单个事件耗尽 GitHub 配额（每 PR 一次 commit 清单调用）
        prs_api.sync_prs(config.WEBHOOK_PR_LIMIT)
    except AppError as exc:
        if exc.code == 50000:
            logger.info("同步互斥锁被占用，跳过本次 webhook pull_request 同步")
            return
        logger.exception("webhook pull_request 同步失败")
    except Exception:  # noqa: BLE001
        logger.exception("webhook pull_request 同步失败")


@router.post("/api/webhook/github", response_model=schemas.WebhookResponse)
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict:
    if not config.WEBHOOK_SECRET:
        raise AppError(40100, "webhook secret not configured")
    raw = await request.body()
    if not verify_signature(raw, x_hub_signature_256, config.WEBHOOK_SECRET):
        raise AppError(40100, "invalid webhook signature")
    # 验签通过后再判重：伪造请求不该污染去重缓存；此处只读，不登记（见 _remember_delivery）
    if _is_duplicate(x_github_delivery):
        logger.info("duplicate webhook delivery ignored: %s", x_github_delivery)
        return ok(
            {
                "accepted": True,
                "duplicate": True,
                "event": x_github_event or None,
                "action": None,
                "triggered": False,
            }
        )
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
    # 走到这里说明本次投递已受理成功；失败分支（40001/500）提前抛出，不登记，允许重投
    _remember_delivery(x_github_delivery)
    return ok(
        {
            "accepted": True,
            "duplicate": False,
            "event": event or None,
            "action": action,
            "triggered": triggered,
        }
    )
