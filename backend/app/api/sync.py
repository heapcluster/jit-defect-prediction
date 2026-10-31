"""批量同步最新提交并在线预测（POST /api/sync、/api/sync/catchup；change startup-baseline-sync 加 status/stream）。

分层现状：本模块承担**批量编排**（取锁 / 状态快照 / 逐条调度 / 失败隔离），底层原语已下沉
`services.git`（git 命令与临时 worktree）、`services.predict`（特征与打分）、
`services.sync_state`（状态快照与互斥锁）；status/stream 只做响应包络。

三条边界（2026-10-25 审阅后固化）：
1. 绝不改动 SOURCE_REPO 的检出状态（临时 worktree，用后即焚）。
2. 「待预测」按 commit 是否已有 prediction 行判断（commit 表存在 ≠ 已预测）。
3. 不从请求接收仓库路径；复用冻结错误码集合（0/40001/40400/50000）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess  # noqa: F401  # 供测试按 `app.api.sync.subprocess` 打补丁
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app import config, model_registry
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError, ok
from app.models import Prediction
from app.services import champion, sync_state
from app.services.git import (
    build_fetch_args,
    ensure_extractable,
    fetch_latest_tip,
    list_all_hashes,
    list_recent_hashes,
    pick_hashes_to_predict,
)
from app.services.predict import predict_commit_all_models

router = APIRouter(dependencies=[Depends(require_api_key)])

logger = logging.getLogger("backend.sync")

MAX_LIMIT = 50
# 单次 IN 查询的分批大小：catchup 时若把全表 prediction.commit_hash 拉进内存，
# 内存与首屏时间都会随预测规模线性增长（这是启动路径，代价被放大）
_PREDICTED_CHUNK = 500

# 同步互斥锁与状态快照同源（services.sync_state 为唯一定义点）；
# 本模块级别名保留「按 app.api.sync._sync_lock 持锁」的既有用法。
_sync_lock = sync_state._sync_lock

# plan(repo_dir) → (scanned, pending, truncated)；truncated 为 None 表示该场景不截断


_AUTO = object()  # 哨兵：不传 = 按当前已加载模型集合判断覆盖缺口


def _loaded_model_names() -> set[str]:
    """本批要对齐的在线模型集合。

    注册表为空（全部加载失败）时无从判断“全模型覆盖”，退回有效默认模型单模型判据，
    避免把整批候选当成缺口反复重试；默认模型解析与读路径同源于 `services.champion`。
    """
    names = {entry.name for entry in model_registry.all_models()}
    if names:
        return names
    with SessionLocal() as session:
        default = champion.resolve(session)
    return {default} if default else set()


def _unpredicted(
    hashes: list[str], limit: int | None = None, models: set[str] | str | None | object = _AUTO
) -> tuple[list[str], bool]:
    """按输入顺序挑出「在线模型覆盖不全」的哈希；分批 IN，不整表载入。

    `models` 三种取值：
    - `_AUTO`（默认）：当前**已加载模型集合**，缺任一模型的行即算待预测 —— 这是
      change `realtime-commit-sync`「全模型落库」的判据。只看默认模型不够：某提交
      已有默认模型行、却缺其余在线模型行时会被永久跳过，补齐永远不会发生。
    - `str` / 集合：按指定模型（集合）判断，供定向补齐与测试使用。
    - `None`：旧语义「任意模型有行即算完成」，仅显式传入时生效。

    `limit` 非空时最多返回 limit 条，并在「还有更多」时把第二项置为 True。
    """
    pending: list[str] = []
    wanted: set[str] | None
    if models is _AUTO:
        wanted = _loaded_model_names()
    elif isinstance(models, str):
        wanted = {models}
    else:
        wanted = set(models) if models is not None else None
    with SessionLocal() as session:
        for start in range(0, len(hashes), _PREDICTED_CHUNK):
            chunk = hashes[start : start + _PREDICTED_CHUNK]
            if wanted is None:
                rows = session.execute(
                    select(Prediction.commit_hash)
                    .where(Prediction.commit_hash.in_(chunk))
                    .distinct()
                )
                covered = {row[0] for row in rows}
            else:
                rows = session.execute(
                    select(Prediction.commit_hash, Prediction.model_name).where(
                        Prediction.commit_hash.in_(chunk)
                    )
                )
                have: dict[str, set[str]] = {}
                for commit_hash, model_name in rows:
                    have.setdefault(commit_hash, set()).add(model_name)
                covered = {h for h, names in have.items() if wanted <= names}
            for commit_hash in chunk:
                if commit_hash in covered:
                    continue
                if limit is not None and len(pending) >= limit:
                    return pending, True
                pending.append(commit_hash)
    return pending, False


def _predicted_among(hashes: list[str]) -> set[str]:
    """给定哈希里**在线模型已覆盖全**的子集（供 pick_hashes_to_predict 做纯函数过滤）。"""
    pending, _ = _unpredicted(hashes)
    return set(hashes) - set(pending)


def is_first_run() -> bool:
    """prediction 表为空判定首启（建基线）。"""
    with SessionLocal() as session:
        return session.query(Prediction).first() is None


def _update_done(results: list, skipped: list) -> None:
    sync_state.set_state(done=len(results) + len(skipped))


def _run_batch(
    *,
    mode: str,
    scope: str,
    plan: Callable[[str], tuple[int, list[str], bool | None]],
) -> dict:
    """取锁 → fetch → 按 plan 算待预测 → 逐条预测入库 → 归还锁。

    手动增量与补齐到 HEAD 只差「怎么算 pending」，其余流程共用本函数（原先两处 90% 重复）。
    """
    if not _sync_lock.acquire(blocking=False):
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    sync_state.set_state(
        running=True,
        mode=mode,
        scope=scope,
        total=0,
        done=0,
        current_hash=None,
        started_at=datetime.now(UTC).replace(tzinfo=None),
        last_error=None,
    )
    try:
        repo = config.SOURCE_REPO
        if repo is None or not (repo / ".git").exists():
            raise AppError(40400, "sync source repository unavailable")

        tip = fetch_latest_tip(str(repo))
        scanned, pending, truncated = plan(str(repo))
        sync_state.set_state(total=len(pending))

        extract_repo, release = ensure_extractable(str(repo), tip)
        try:
            results: list[dict] = []
            skipped: list[dict] = []
            for commit_hash in pending:
                sync_state.set_state(current_hash=commit_hash)
                try:
                    predict_commit_all_models(commit_hash, repo=extract_repo)
                    results.append({"commit_hash": commit_hash})
                except AppError as exc:
                    skipped.append(
                        {"commit_hash": commit_hash, "code": exc.code, "message": exc.message}
                    )
                _update_done(results, skipped)
        finally:
            release()

        logger.info(
            "sync done: mode=%s tip=%s scanned=%s pending=%s predicted=%s skipped=%s truncated=%s",
            mode,
            tip[:10],
            scanned,
            len(pending),
            len(results),
            len(skipped),
            truncated,
        )
        data: dict = {
            "tip": tip,
            "scanned": scanned,
            "new": len(pending),
            "predicted": results,
            "skipped": skipped,
        }
        if truncated is not None:
            data["truncated"] = truncated
        return data
    except Exception as exc:
        sync_state.set_state(last_error=str(exc)[:200])
        raise
    finally:
        sync_state.set_state(running=False)
        _sync_lock.release()


def sync_recent(limit: int = 10, mode: str = "manual", scope: str = "latest") -> dict:
    """同步入口：fetch → 挑待预测 → 逐条走全模型预测链。任一条失败不中断整批。"""
    if not (1 <= limit <= MAX_LIMIT):
        raise AppError(40001, f"参数非法：limit 需在 1..{MAX_LIMIT}")

    def plan(repo: str) -> tuple[int, list[str], bool | None]:
        hashes = list_recent_hashes(repo, limit)
        pending = pick_hashes_to_predict(hashes, _predicted_among(hashes))
        return len(hashes), pending, None

    return _run_batch(mode=mode, scope=scope, plan=plan)


def sync_catchup(mode: str = "catchup", scope: str = "catchup-to-head") -> dict:
    """补齐到最新：扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并全模型预测。

    MUST NOT 接受日期参数（前端不提供历史区间预测）。缺口超出 SYNC_CATCHUP_LIMIT 时截断。
    """

    def plan(repo: str) -> tuple[int, list[str], bool | None]:
        hashes = list_all_hashes(repo)
        pending, truncated = _unpredicted(hashes, config.SYNC_CATCHUP_LIMIT)
        return len(hashes), pending, truncated

    return _run_batch(mode=mode, scope=scope, plan=plan)


def run_startup_sync() -> dict:
    """启动触发：首启建基线（限额），否则追到 HEAD（补齐缺口）。"""
    if is_first_run():
        return sync_recent(config.SYNC_INITIAL_LIMIT, mode="startup", scope="baseline")
    return sync_catchup(mode="startup", scope="catchup-to-head")


async def _event_stream():
    """SSE：同步状态变化时推送快照；同步结束发最终快照并关闭。"""
    last = None
    while True:
        snap = sync_state.get_sync_state()
        if snap != last:
            yield f"data: {json.dumps(snap, default=str)}\n\n"
            last = snap
        if not snap["running"]:
            break
        await asyncio.sleep(1)


@router.post("/api/sync")
def sync_endpoint(limit: int = Query(default=10, ge=1, le=MAX_LIMIT)) -> dict:
    """拉取 SOURCE_REPO 最新提交并逐条现算全模型预测入库；无待预测提交时幂等返回 0。"""
    data = sync_recent(limit)
    return ok(data)


@router.post("/api/sync/catchup")
def sync_catchup_endpoint() -> dict:
    """补齐到最新：DB 缺、git 有的 commit 全部现算全模型预测入库（无日期参数）。"""
    data = sync_catchup()
    return ok(data)


@router.get("/api/sync/status")
def sync_status() -> dict:
    """同步状态快照（running / mode / scope / total / done / current_hash / started_at / last_error）。"""
    return ok(sync_state.get_sync_state())


@router.get("/api/sync/stream")
def sync_stream() -> StreamingResponse:
    """SSE 实时推送同步进度（text/event-stream），替代前端轮询。"""
    return StreamingResponse(_event_stream(), media_type="text/event-stream")


__all__ = [
    "MAX_LIMIT",
    "build_fetch_args",
    "is_first_run",
    "router",
    "run_startup_sync",
    "sync_catchup",
    "sync_recent",
]
