"""批量同步最新提交并在线预测（POST /api/sync、/api/sync/catchup；change startup-baseline-sync 加 status/stream）。

职责：对配置的 SOURCE_REPO 执行「fetch → 挑待预测哈希 → 逐条现算特征并预测入库」。
预测复用 POST /api/predict 的单条路径（predict_commit_all_models 一次现算、逐模型打分），
本模块只负责批量编排，不另立预测口径、不直接写表。

三条边界（2026-10-25 审阅后固化）：
1. 绝不改动 SOURCE_REPO 的检出状态（临时 worktree，用后即焚）。
2. 「待预测」按 commit 是否已有 prediction 行判断（commit 表存在 ≠ 已预测）。
3. 不从请求接收仓库路径；复用冻结错误码集合（0/40001/40400/50000）。

本 change（startup-baseline-sync）新增：
- 统一落全部注册模型（predict_commit_all_models）；
- 启动分级：首启限额建基线 / 日常追到 HEAD（catchup）；
- 同步状态 _sync_state + status/stream 端点，供前端实时可见。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app import config
from app.api.predict import predict_commit_all_models
from app.auth import require_api_key
from app.db import SessionLocal
from app.errors import INTERNAL_ERROR_MESSAGE, AppError, ok
from app.models import Prediction

router = APIRouter(dependencies=[Depends(require_api_key)])

_GIT_TIMEOUT = 180
_sync_lock = threading.Lock()
logger = logging.getLogger("backend.sync")

MAX_LIMIT = 50

# 同步状态快照（实时可见）：前端 SSE 订阅；首启/手动/追到 HEAD 共用
_sync_state = {
    "running": False,
    "mode": None,  # "startup" | "manual" | "catchup"
    "scope": None,  # "baseline" | "catchup-to-head" | "latest"
    "total": 0,
    "done": 0,
    "current_hash": None,
    "started_at": None,
    "last_error": None,
}


def _set_state(**kwargs) -> None:
    for k, v in kwargs.items():
        if k in _sync_state:
            _sync_state[k] = v


def get_sync_state() -> dict:
    return dict(_sync_state)


def _run_git(repo: str, *args: str) -> str:
    """执行 git 命令；代理只认 `GIT_PROXY`（其次 `HTTPS_PROXY`），不让全局 git 配置掺进来。

    `encoding="utf-8"` 显式指定：Windows 默认按 locale（cp936）解码，Camel 的
    中文提交信息会乱码并最终写进 `commit.message`。
    """
    cmd = ["git", "-C", repo]
    proxy = os.getenv("GIT_PROXY", "").strip() or os.getenv("HTTPS_PROXY", "").strip()
    if proxy:
        cmd += ["-c", f"http.proxy={proxy}", "-c", f"https.proxy={proxy}"]
    else:
        cmd += ["-c", "http.proxy=", "-c", "https.proxy="]
    cmd += [*args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_GIT_TIMEOUT,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        logger.exception("sync git timeout: %s", args[:2])
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.exception("sync git failed: %s", args[:2])
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from exc
    return proc.stdout


def build_fetch_args() -> list[str]:
    """fetch 命令参数：取远端默认分支（HEAD），经命令行禁代理（纯函数，供测试）。"""
    return ["fetch", "origin", "HEAD"]


def fetch_latest_tip(repo: str, retries: int = 3) -> str:
    """fetch 远端并返回最新 tip 哈希（FETCH_HEAD 首个条目）；网络抖动时重试。"""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _run_git(repo, *build_fetch_args())
            break
        except AppError as exc:
            last = exc
            if attempt < retries:
                time.sleep(5)
    else:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE) from last
    tip = _run_git(repo, "rev-parse", "FETCH_HEAD").strip()
    if len(tip) != 40:
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    return tip


def _is_ancestor(repo: str, commit: str, base: str = "HEAD") -> bool:
    check = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", commit, base],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=_GIT_TIMEOUT,
        check=False,
    )
    return check.returncode == 0


def ensure_extractable(repo: str, tip: str) -> tuple[Path, Callable[[], None]]:
    """返回 (特征提取用仓库路径, 释放函数)。tip 已从 HEAD 可达直接用 SOURCE_REPO；否则建临时 worktree。"""
    if _is_ancestor(repo, tip):
        return Path(repo), lambda: None

    tmp = Path(tempfile.mkdtemp(prefix="jit-sync-"))
    try:
        _run_git(repo, "worktree", "add", "--detach", "--no-checkout", str(tmp), tip)
    except AppError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    def _release() -> None:
        try:
            _run_git(repo, "worktree", "remove", "--force", str(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    return str(tmp), _release


def pick_hashes_to_predict(hashes: list[str], predicted: set[str]) -> list[str]:
    """按最新在前挑出**尚无 prediction 行**的哈希（纯函数，供测试）。"""
    return [h for h in hashes if h not in predicted]


def list_recent_hashes(repo: str, limit: int, ref: str = "FETCH_HEAD") -> list[str]:
    out = _run_git(repo, "log", f"-n{limit}", "--format=%H", ref)
    return [line.strip() for line in out.splitlines() if line.strip()]


def list_all_hashes(repo: str, ref: str = "FETCH_HEAD") -> list[str]:
    """取 ref 历史全部哈希（时间倒序），用于 catchup 补齐 DB→HEAD 缺口。"""
    out = _run_git(repo, "log", "--format=%H", ref)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _predicted_commits(hashes: list[str] | None = None) -> set[str]:
    """已预测的 commit_hash 集合：prediction 表有任一行的即视为已预测。"""
    with SessionLocal() as session:
        q = session.query(Prediction.commit_hash)
        if hashes is not None:
            q = q.filter(Prediction.commit_hash.in_(hashes))
        return {r[0] for r in q.distinct().all()}


def is_first_run() -> bool:
    """prediction 表为空判定首启（建基线）。"""
    with SessionLocal() as session:
        return session.query(Prediction).first() is None


def _update_done(results: list, skipped: list) -> None:
    _set_state(done=len(results) + len(skipped))


def sync_recent(limit: int = 10, mode: str = "manual", scope: str = "latest") -> dict:
    """同步入口：fetch → 挑待预测 → 逐条走全模型预测链。任一条失败不中断整批。"""
    if not (1 <= limit <= MAX_LIMIT):
        raise AppError(40001, f"参数非法：limit 需在 1..{MAX_LIMIT}")
    if not _sync_lock.acquire(blocking=False):
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    _set_state(
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
        hashes = list_recent_hashes(str(repo), limit)
        predicted = _predicted_commits(hashes)
        pending = pick_hashes_to_predict(hashes, predicted)
        _set_state(total=len(pending))

        extract_repo, release = ensure_extractable(str(repo), tip)
        try:
            results: list[dict] = []
            skipped: list[dict] = []
            for h in pending:
                _set_state(current_hash=h)
                try:
                    predict_commit_all_models(h, repo=extract_repo)
                    results.append({"commit_hash": h})
                except AppError as exc:
                    skipped.append({"commit_hash": h, "code": exc.code, "message": exc.message})
                _update_done(results, skipped)
        finally:
            release()

        logger.info(
            "sync done: tip=%s scanned=%s pending=%s predicted=%s skipped=%s",
            tip[:10],
            len(hashes),
            len(pending),
            len(results),
            len(skipped),
        )
        return {
            "tip": tip,
            "scanned": len(hashes),
            "new": len(pending),
            "predicted": results,
            "skipped": skipped,
        }
    except Exception as exc:
        _set_state(last_error=str(exc)[:200])
        raise
    finally:
        _set_state(running=False)
        _sync_lock.release()


def sync_catchup(mode: str = "catchup", scope: str = "catchup-to-head") -> dict:
    """补齐到最新：扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并全模型预测。

    MUST NOT 接受日期参数（前端不提供历史区间预测）。缺口超出 SYNC_CATCHUP_LIMIT 时截断。
    """
    if not _sync_lock.acquire(blocking=False):
        raise AppError(50000, INTERNAL_ERROR_MESSAGE)
    _set_state(
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
        all_hashes = list_all_hashes(str(repo))
        predicted = _predicted_commits()
        pending = [h for h in all_hashes if h not in predicted]
        truncated = len(pending) > config.SYNC_CATCHUP_LIMIT
        if truncated:
            pending = pending[: config.SYNC_CATCHUP_LIMIT]
        _set_state(total=len(pending))

        extract_repo, release = ensure_extractable(str(repo), tip)
        try:
            results: list[dict] = []
            skipped: list[dict] = []
            for h in pending:
                _set_state(current_hash=h)
                try:
                    predict_commit_all_models(h, repo=extract_repo)
                    results.append({"commit_hash": h})
                except AppError as exc:
                    skipped.append({"commit_hash": h, "code": exc.code, "message": exc.message})
                _update_done(results, skipped)
        finally:
            release()

        logger.info(
            "catchup done: tip=%s scanned=%s pending=%s predicted=%s skipped=%s truncated=%s",
            tip[:10],
            len(all_hashes),
            len(pending),
            len(results),
            len(skipped),
            truncated,
        )
        return {
            "tip": tip,
            "scanned": len(all_hashes),
            "new": len(pending),
            "predicted": results,
            "skipped": skipped,
            "truncated": truncated,
        }
    except Exception as exc:
        _set_state(last_error=str(exc)[:200])
        raise
    finally:
        _set_state(running=False)
        _sync_lock.release()


def run_startup_sync() -> dict:
    """启动触发：首启建基线（限额），否则追到 HEAD（补齐缺口）。"""
    if is_first_run():
        return sync_recent(config.SYNC_INITIAL_LIMIT, mode="startup", scope="baseline")
    return sync_catchup(mode="startup", scope="catchup-to-head")


async def _event_stream():
    """SSE：_sync_state 变化时推送快照；同步结束发最终快照并关闭。"""
    last = None
    while True:
        snap = get_sync_state()
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
    return ok(get_sync_state())


@router.get("/api/sync/stream")
def sync_stream() -> StreamingResponse:
    """SSE 实时推送同步进度（text/event-stream），替代前端轮询。"""
    return StreamingResponse(_event_stream(), media_type="text/event-stream")


__all__ = [
    "MAX_LIMIT",
    "build_fetch_args",
    "ensure_extractable",
    "fetch_latest_tip",
    "get_sync_state",
    "is_first_run",
    "list_all_hashes",
    "list_recent_hashes",
    "pick_hashes_to_predict",
    "router",
    "run_startup_sync",
    "sync_catchup",
    "sync_recent",
]
