"""批量同步最新提交并在线预测（POST /api/sync、GET /api/sync/status；docs/api/sync.md）。

分层现状：本模块承担**批量编排**（取锁 / 状态快照 / 逐条调度 / 失败隔离），底层原语已下沉
`services.git`（git 命令与临时 worktree）、`services.predict`（特征与打分）、
`services.sync_state`（状态快照与互斥锁）；status 只做响应包络。

口径（docs/api/sync.md）：
1. 全系统唯一会触发计算的入口；查询类接口一律只读。
2. 「刷新」按架构（line）/ 模型（model_name）/ commit 时间区间补算；时间范围为空时按
   服务端内部默认批次（config.SYNC_BATCH_LIMIT）取最新一批。
3. `POST /api/sync/catchup` 与 `/api/sync/stream` 已下线：catchup 仅作启动内部同步，进度轮 status。
"""

from __future__ import annotations

import logging
import subprocess  # noqa: F401  # 供测试按 app.api.sync.subprocess 打补丁（与 services.git 同对象）
import threading
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app import config, feature_source, model_registry
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import AppError, ok
from app.models import Model, Prediction
from app.services import sync_state
from app.services.git import (
    build_fetch_args,
    ensure_extractable,
    fetch_latest_tip,
    list_all_hashes,
    list_hashes_in_range,
    list_recent_hashes,
    run_git,
)
from app.services.predict import (
    predict_commit_all_models,
    predict_single,
    store_extracted_features,
)
from app.timeutil import iso_z, parse_time_param

router = APIRouter(dependencies=[Depends(require_api_key)])

logger = logging.getLogger("backend.sync")

# 并发冲突走 40001（业务可解释错误），不回 50000「internal error」：前端据此置灰按钮而非报服务异常
SYNC_BUSY_MESSAGE = "同步进行中，请稍候"

# 架构取值（与库表 model.line 同值，小写）
VALID_LINES = ("expert", "semantic", "fused", "e2e")
# 单次 IN 查询的分批大小：catchup 时若把全表 prediction.commit_hash 拉进内存，
# 内存与首屏时间都会随预测规模线性增长（这是启动路径，代价被放大）
_PREDICTED_CHUNK = 500

# 同步互斥锁与状态快照同源（services.sync_state 为唯一定义点）；
# 本模块级别名保留「按 app.api.sync._sync_lock 持锁」的既有用法。
_sync_lock = sync_state._sync_lock


def _loaded_model_names() -> set[str]:
    """当前「在线模型」集合 = 已加载模型（docs：未指定模型时缺「任一在线模型」即算缺口）。"""
    return {entry.name for entry in model_registry.all_models()}


def _resolve_scope_models(session, line: str | None, model_name: str | None) -> set[str]:
    """把 line / model_name 解析成要补齐的模型集合。

    显式指定 `line` / `model_name` 时覆盖四线交付模型（semantic/fused/e2e 懒加载）；
    未指定时只取已加载模型（当前为 expert 批量路径），保持普通「刷新」轻量。
    """
    if model_name:
        if not model_registry.has(model_name):
            raise AppError(40001, "参数非法：model_name 不存在")
        return {model_name}
    if line:
        rows = session.execute(
            select(Model.model_name).where(Model.line == line)
        ).scalars().all()
        return {name for name in rows if model_registry.has(name)}
    return _loaded_model_names()


def _unpredicted(
    hashes: list[str], models: set[str], limit: int | None = None
) -> tuple[list[str], bool]:
    """按输入顺序挑出缺「models 中任一模型」预测行的哈希；分批 IN，不整表载入。

    `models` 为空集时无缺口（全部视为已覆盖）。`limit` 非空时最多返回 limit 条，
    并在「还有更多」时把第二项置为 True。
    """
    wanted = set(models)
    if not wanted:
        return [], False
    pending: list[str] = []
    with SessionLocal() as session:
        for start in range(0, len(hashes), _PREDICTED_CHUNK):
            chunk = hashes[start : start + _PREDICTED_CHUNK]
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


def is_first_run() -> bool:
    """prediction 表为空判定首启（建基线）。"""
    with SessionLocal() as session:
        return session.query(Prediction).first() is None


def _update_done(results: list, skipped: list) -> None:
    sync_state.set_state(done=len(results) + len(skipped))


def _prefetch_features(hashes: list[str], repo) -> int:
    """批量现算待补提交的 14 维特征并落库。

    逐条预测各自调用 extract_single_commit 会各扫一遍全历史；这里一次扫描算完
    整批，N 条新提交的耗时从 N×110s 降到约 1×110s + 批量打分。
    """
    if not hashes:
        return 0
    try:
        items = feature_source.extract_many(hashes, repo)
        return store_extracted_features(items)
    except Exception:  # noqa: BLE001 —— 预取失败退回逐条现算，不阻断同步
        logger.exception("batch feature prefetch failed; fallback to per-commit extraction")
        return 0


def _predict_commit_models(commit_hash: str, repo, model_names: list[str]) -> None:
    """按模型线分流：expert 走 14 维批量路径，semantic/fused/e2e 走单模型在线路径。

    非 expert 线的输入维度/文本不同，不能复用 14 维批量打分；缺向量或文本时由
    `predict_single` 的在线补算兜底。
    """
    expert = [name for name in model_names if model_registry.line_of(name) == "expert"]
    others = [name for name in model_names if name not in expert]
    if expert:
        predict_commit_all_models(commit_hash, repo=repo, model_names=expert)
    for name in others:
        predict_single(commit_hash, name, repo=repo)


def _run_batch(
    *,
    mode: str,
    scope: str,
    models: set[str],
    plan: Callable[[str, str], tuple[int, list[str], bool | None]],
) -> dict:
    """取锁 → （可选 fetch）→ 按 plan 算待预测 → 批量抽特征 → 逐条预测入库 → 归还锁。"""
    if not _sync_lock.acquire(blocking=False):
        raise AppError(40001, SYNC_BUSY_MESSAGE)
    sync_state.set_state(
        running=True,
        phase="fetch" if config.SYNC_FETCH else "plan",
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

        tip = (
            fetch_latest_tip(str(repo))
            if config.SYNC_FETCH
            else run_git(str(repo), "rev-parse", "HEAD").strip()
        )
        sync_state.set_state(phase="plan")
        scanned, pending, truncated = plan(str(repo), tip)
        sync_state.set_state(
            total=len(pending), phase="extract" if pending else "predict"
        )

        model_names = sorted(models)
        extract_repo, release = ensure_extractable(str(repo), tip)
        try:
            extracted = _prefetch_features(pending, extract_repo)
            if pending:
                logger.info("sync prefetch: pending=%s extracted=%s", len(pending), extracted)
            sync_state.set_state(phase="predict")
            results: list[dict] = []
            skipped: list[dict] = []
            for commit_hash in pending:
                sync_state.set_state(current_hash=commit_hash)
                try:
                    _predict_commit_models(commit_hash, extract_repo, model_names)
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
        sync_state.set_state(running=False, phase=None)
        _sync_lock.release()


def sync_manual(
    line: str | None = None,
    model_name: str | None = None,
    start=None,
    end=None,
) -> dict:
    """POST /api/sync：按架构 / 模型 / commit 时间区间补算（前端「刷新」唯一入口）。

    时间范围为空时按服务端内部默认批次（config.SYNC_BATCH_LIMIT）取最新一批。
    """
    with SessionLocal() as session:
        models = _resolve_scope_models(session, line, model_name)

    def plan(repo: str, tip: str) -> tuple[int, list[str], bool | None]:
        if start is not None or end is not None:
            hashes = list_hashes_in_range(repo, start, end, ref=tip)
        else:
            hashes = list_recent_hashes(repo, config.SYNC_BATCH_LIMIT, ref=tip)
        pending, _ = _unpredicted(hashes, models)
        return len(hashes), pending, None

    return _run_batch(mode="manual", scope="latest", models=models, plan=plan)


def sync_catchup(mode: str = "startup", scope: str = "catchup-to-head") -> dict:
    """补齐到最新：扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并全模型预测。

    仅供启动内部同步调用（不暴露 HTTP 端点）。缺口超出 SYNC_CATCHUP_LIMIT 时截断。
    """
    models = _loaded_model_names()

    def plan(repo: str, tip: str) -> tuple[int, list[str], bool | None]:
        hashes = list_all_hashes(repo, ref=tip)
        pending, truncated = _unpredicted(hashes, models, config.SYNC_CATCHUP_LIMIT)
        return len(hashes), pending, truncated

    return _run_batch(mode=mode, scope=scope, models=models, plan=plan)


def run_startup_sync() -> dict:
    """启动触发：首启建基线（限额），否则追到 HEAD（补齐缺口）。"""
    if is_first_run():
        models = _loaded_model_names()

        def plan(repo: str, tip: str) -> tuple[int, list[str], bool | None]:
            hashes = list_recent_hashes(repo, config.SYNC_INITIAL_LIMIT, ref=tip)
            pending, _ = _unpredicted(hashes, models)
            return len(hashes), pending, None

        return _run_batch(mode="startup", scope="baseline", models=models, plan=plan)
    return sync_catchup(mode="startup", scope="catchup-to-head")


def _spawn_sync_worker(fn: Callable[[], dict]) -> None:
    """后台线程跑同步任务；失败只记日志，并确保状态不卡在 running=True。"""

    def _run() -> None:
        try:
            fn()
        except Exception as exc:
            logger.exception("sync worker failed")
            sync_state.set_state(running=False, last_error=str(exc)[:200])

    threading.Thread(target=_run, daemon=True, name="sync-worker").start()


@router.post("/api/sync")
def sync_endpoint(
    line: str | None = Query(default=None),
    model_name: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
) -> dict:
    """按架构 / 模型 / commit 时间区间**异步**补算入库（docs/api/sync.md）。

    提交后立即返回；进度轮 `/api/sync/status`。同一时刻只允许一个同步任务，
    已在同步中时返回 40001（可解释冲突，不排队）。
    """
    if line is not None and line not in VALID_LINES:
        raise AppError(40001, "参数非法：line 取值需为 expert / semantic / fused / e2e")
    if model_name is not None and not model_registry.has(model_name):
        raise AppError(40001, "参数非法：model_name 不存在")
    start = parse_time_param(start_time, "start_time") if start_time else None
    end = parse_time_param(end_time, "end_time", "end") if end_time else None
    # 「检查 running + 置 running=True」必须在锁内原子完成：否则两个并发请求都能通过
    # 检查、各 spawn 一个 worker，败者 worker 的异常处理会把 running=False 写回，
    # 覆盖胜者正在跑的状态。
    with _sync_lock:
        if sync_state.get_sync_state()["running"]:
            raise AppError(40001, SYNC_BUSY_MESSAGE)
        # 在请求内先置 running=True：否则前端提交后立即轮询时，worker 可能还没启动，
        # 会读到上一次任务的 running=false 而误判「已完成」。
        sync_state.set_state(
            running=True,
            phase="fetch" if config.SYNC_FETCH else "plan",
            mode="manual",
            scope="latest",
            total=0,
            done=0,
            current_hash=None,
            started_at=datetime.now(UTC).replace(tzinfo=None),
            last_error=None,
        )
    _spawn_sync_worker(lambda: sync_manual(line=line, model_name=model_name, start=start, end=end))
    return ok({"accepted": True})


@router.get("/api/sync/status")
def sync_status() -> dict:
    """同步状态快照（running / mode / scope / total / done / current_hash / started_at / last_error）。"""
    state = sync_state.get_sync_state()
    # 契约三：时间字段统一 UTC + Z；内存里是 naive UTC，出参前统一格式化
    state["started_at"] = iso_z(state.get("started_at"))
    return ok(state)


__all__ = [
    "VALID_LINES",
    "build_fetch_args",
    "is_first_run",
    "router",
    "run_startup_sync",
    "sync_catchup",
    "sync_manual",
]
