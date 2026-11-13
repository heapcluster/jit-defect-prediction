"""系统测试的两类异常场景：缺权重、失败恢复。

为避免破坏正在运行的 8000 服务，本脚本**自己起/停独立的 uvicorn 子进程**（端口自动选空闲端口），
只对自己的子进程发信号；不移动、不删除任何权重文件。

    cd backend && python scripts/system_exceptions.py                 # 两个场景都跑
    python scripts/system_exceptions.py --scenario missing-weights
    python scripts/system_exceptions.py --scenario failure-recovery
    python scripts/system_exceptions.py --scenario empty-db

退出码：全部断言通过 0；任一失败 1（并列出失败项与复现条件）。
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
AUTH = {"X-API-Key": os.getenv("API_TOKEN", "")}

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start(port: int, extra_env: dict[str, str], log: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(extra_env)
    env["SYNC_ON_STARTUP"] = "0"
    handle = log.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_ready(port: int, timeout: int = 90) -> httpx.Client:
    client = httpx.Client(
        trust_env=False, base_url=f"http://127.0.0.1:{port}", headers=AUTH, timeout=30.0
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if client.get("/api/health").status_code in (200, 401):
                return client
        except Exception:  # noqa: BLE001 - 启动中连接失败属正常
            time.sleep(1)
    client.close()
    raise AssertionError(f"端口 {port} 上的服务 {timeout}s 未就绪")


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def no_leak(text: str) -> bool:
    return not any(k in text for k in ("Traceback", "sqlalchemy", "SELECT ", "C:\\", "/app/"))


def scenario_missing_weights(logdir: Path) -> None:
    """MODEL_DIR 指向空目录 → expert 权重缺失：健康降级、预测明确报错、不 500。"""
    empty = Path(tempfile.mkdtemp(prefix="neon-empty-models-"))
    port = free_port()
    proc = start(port, {"MODEL_DIR": str(empty)}, logdir / "missing-weights.log")
    try:
        client = wait_ready(port)
        h = client.get("/api/health").json()["data"]
        record(
            "缺权重 / health 降级",
            h["status"] == "degraded" and h["db"] == "up" and h["models_loaded"] == 0,
            f"status={h['status']} db={h['db']} models_loaded={h['models_loaded']}",
        )
        r = client.post("/api/predict", json={"commit_hash": "a" * 40, "model_name": "xgb_v1"})
        body = r.json()
        record(
            "缺权重 / predict 明确拒绝",
            r.status_code in (400, 404) and body.get("code") in (40001, 40400) and no_leak(r.text),
            f"{r.status_code}/{body.get('code')} msg={body.get('message')}",
        )
        r2 = client.get("/api/models")
        record(
            "缺权重 / 模型清单仍可读",
            r2.status_code == 200,
            f"{r2.status_code}（清单来自 catalog，不等于可用）",
        )
        client.close()
    finally:
        stop(proc)
        for item in empty.iterdir():
            item.unlink()
        empty.rmdir()


def scenario_empty_db(logdir: Path) -> None:
    """空库：DB_NAME 指向空的测试库 → 空数据返回 code=0，不是系统错误。"""
    port = free_port()
    db = os.getenv("DB_TEST_NAME", "jit_test")
    proc = start(port, {"DB_NAME": db}, logdir / "empty-db.log")
    try:
        client = wait_ready(port)
        h = client.get("/api/health").json()["data"]
        record(
            "空库 / 健康检查",
            h["db"] == "up" and h["commit_count"] == 0 and h["prediction_count"] == 0,
            f"db={h['db']} commits={h['commit_count']} predictions={h['prediction_count']}",
        )
        commits = client.get("/api/commits").json()
        record(
            "空库 / 列表返回空而非报错",
            commits.get("code") == 0
            and commits["data"]["total"] == 0
            and commits["data"]["items"] == [],
            f"code={commits.get('code')} total={commits['data']['total']}",
        )
        trends = client.get("/api/trends").json()
        record(
            "空库 / 趋势返回空 series",
            trends.get("code") == 0 and trends["data"]["series"] == [],
            f"code={trends.get('code')} series={len(trends['data']['series'])}",
        )
        r = client.get("/api/figures", params={"model_name": "et_v1"})
        record(
            "空库 / 图集 40400",
            r.status_code == 404 and r.json().get("code") == 40400,
            f"{r.status_code}/{r.json().get('code')}",
        )
        client.close()
    finally:
        stop(proc)


def scenario_restart_recovery(logdir: Path) -> None:
    """同步进行中强杀服务 → 重启后内存状态清空、DB 可用、接口不 500。"""
    port = free_port()
    first = start(port, {}, logdir / "recovery-before.log")
    try:
        client = wait_ready(port)
        before = client.get("/api/sync/status").json()["data"]
        record("失败恢复 / 初始状态", before["running"] is False, f"running={before['running']}")

        fired = client.post("/api/sync", params={"line": "expert"})
        accepted = fired.status_code == 200
        record("失败恢复 / 触发同步", accepted, f"{fired.status_code}/{fired.json().get('code')}")
        time.sleep(2)  # 让后台 worker 真正开始
        client.close()
    finally:
        # 不等同步结束就强杀：模拟进程中断
        if first.poll() is None:
            first.kill()
            first.wait(timeout=10)

    second = start(port, {}, logdir / "recovery-after.log")
    try:
        client = wait_ready(port)
        h = client.get("/api/health").json()["data"]
        record(
            "失败恢复 / 重启后健康",
            h["status"] == "ok" and h["db"] == "up",
            f"status={h['status']} db={h['db']}",
        )
        status = client.get("/api/sync/status").json()["data"]
        record(
            "失败恢复 / 状态不残留",
            status["running"] is False and status["last_error"] is None,
            f"running={status['running']} last_error={status['last_error']}",
        )
        commits = client.get("/api/commits", params={"size": 1})
        record(
            "失败恢复 / 查询链路可用",
            commits.status_code == 200 and commits.json().get("code") == 0,
            f"{commits.status_code}/{commits.json().get('code')}",
        )
        predict = client.post(
            "/api/predict",
            json={
                "commit_hash": commits.json()["data"]["items"][0]["commit_hash"],
                "model_name": "xgb_v1",
            },
        )
        record(
            "失败恢复 / 可再次预测",
            predict.status_code == 200,
            f"{predict.status_code}/{predict.json().get('code')}",
        )
        client.close()
    finally:
        stop(second)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--scenario",
        choices=("missing-weights", "failure-recovery", "empty-db", "all"),
        default="all",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=BACKEND_DIR.parent
        / "docs"
        / "test"
        / "integration_test"
        / "execution_records"
        / f"{date.today().isoformat()}-system-exceptions.md",
    )
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="neon-system-exceptions-") as tmp:
        logdir = Path(tmp)
        if args.scenario in ("missing-weights", "all"):
            scenario_missing_weights(logdir)
        if args.scenario in ("empty-db", "all"):
            scenario_empty_db(logdir)
        if args.scenario in ("failure-recovery", "all"):
            scenario_restart_recovery(logdir)

    failed = [r for r in results if not r[1]]
    print(
        f"\n[system] 汇总：total={len(results)} pass={len(results) - len(failed)} fail={len(failed)}"
    )
    for name, _, detail in failed:
        print(f"[system]   FAILED {name}: {detail}", file=sys.stderr)

    lines = [
        "# 系统异常场景执行证据（测试代码产物）",
        "",
        f"> 生成：`backend/scripts/system_exceptions.py --scenario {args.scenario}` ｜ 时间：{datetime.now().isoformat(timespec='seconds')}",
        "> 环境：本机 MySQL80 `jit_demo`；脚本自起/自停独立 uvicorn 子进程（空闲端口），**不移动、不删除任何权重**，不影响 8000 主服务。",
        "",
        "| 场景 | 结果 | 实测 |",
        "|---|---|---|",
    ]
    lines += [f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |" for name, ok, detail in results]
    lines += [
        "",
        f"汇总：{len(results) - len(failed)}/{len(results)} 通过。",
        "",
        "- 缺权重：`MODEL_DIR` 指向空目录 → `health=degraded`、`POST /api/predict` 40001 明确文案，不 500、不泄漏路径。",
        "- 空库：`DB_NAME` 指向空的 `jit_test` → 列表/趋势返回 `code=0` 空结果，图集 40400，空数据不是系统错误。",
        "- 失败恢复：同步进行中强杀子进程 → 重启后 `sync/status` 内存态清空、DB 可用、可再次预测。",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[system] 证据 -> {args.out}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
