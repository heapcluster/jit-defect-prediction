"""负载测试（新版考核说明 §4.1：并发用户数 / 响应时间 / 吞吐量 / 错误率）。

本机没有 JMeter/Locust 且按要求不安装，这里用标准库线程池 + httpx 做等价负载，
输出可直接写进性能测试报告的四个指标；另附 `locustfile.py` 供有 Locust 的环境复跑。

    cd backend && python scripts/load_test.py
    USERS=20 REQUESTS=10 python scripts/load_test.py

退出码：错误率为 0 且 p95 < 500ms → 0，否则 1。
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH = {"X-API-Key": os.getenv("API_TOKEN", "")}


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=int(os.getenv("USERS", "20")))
    ap.add_argument("--requests", type=int, default=int(os.getenv("REQUESTS", "10")))
    ap.add_argument(
        "--out",
        type=Path,
        default=BACKEND_DIR.parent
        / "docs"
        / "test"
        / "integration_test"
        / "execution_records"
        / f"{datetime.now().date().isoformat()}-load-test.md",
    )
    args = ap.parse_args()

    # 预热并取样
    with httpx.Client(trust_env=False, base_url=BASE_URL, headers=AUTH, timeout=60.0) as c:
        first = c.get("/api/commits", params={"size": 1}).json()["data"]["items"][0]
    payload = {"commit_hash": first["commit_hash"], "model_name": first["model_name"]}

    def one(_: int) -> tuple[float, bool]:
        with httpx.Client(trust_env=False, base_url=BASE_URL, headers=AUTH, timeout=60.0) as c:
            t0 = time.perf_counter()
            try:
                r = c.post("/api/predict", json=payload)
                return (time.perf_counter() - t0) * 1000, r.status_code == 200
            except Exception:  # noqa: BLE001
                return (time.perf_counter() - t0) * 1000, False

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.users) as pool:
        results = list(pool.map(one, range(args.users * args.requests)))
    elapsed = time.perf_counter() - started

    ok = [ms for ms, good in results if good]
    errors = len(results) - len(ok)
    rps = len(results) / elapsed
    p95 = percentile(ok, 0.95) if ok else float("inf")

    print(f"[load] 并发用户={args.users} 每用户请求={args.requests} 总请求={len(results)}")
    print(f"[load] 耗时={elapsed:.2f}s 吞吐量={rps:.2f} req/s 错误率={errors / len(results):.2%}")
    print(
        f"[load] p50={percentile(ok, 0.5):.1f}ms p95={p95:.1f}ms max={max(ok):.1f}ms mean={statistics.fmean(ok):.1f}ms"
    )

    block = [
        f"## 复跑：并发 {args.users} × {args.requests}（{datetime.now().isoformat(timespec='seconds')}）",
        "",
        f"> 服务：`{BASE_URL}` ｜ 接口：`POST /api/predict` ｜ 模型：`{payload['model_name']}`（真模型，非占位）",
        "",
        "| 指标 | 实测 |",
        "|---|---|",
        f"| 并发用户数 | {args.users} |",
        f"| 每用户请求数 / 总请求数 | {args.requests} / {len(results)} |",
        f"| 总耗时 | {elapsed:.2f}s |",
        f"| 吞吐量 | {rps:.2f} req/s |",
        f"| 响应时间 p50 / p95 / max | {percentile(ok, 0.5):.1f} / {p95:.1f} / {max(ok):.1f} ms |",
        f"| 错误数 / 错误率 | {errors} / {errors / len(results):.2%} |",
        f"| p95 < 500ms | {'达标' if p95 < 500 else '**未达标**'} |",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# 负载测试证据（测试代码产物）",
        "",
        "> 生成：`backend/scripts/load_test.py`；每次复跑追加一段，保留全部实测，不覆盖历史。",
        "> 本机无 JMeter/Locust 且未安装；用线程池做等价负载，`locustfile.py` 供有 Locust 的环境复跑。",
        "> 指标来自真实请求，不含推断值；截图由实际操作者采集（红线规则：不得造假）。",
        "",
    ]
    if args.out.is_file() and args.out.stat().st_size > 0:
        args.out.write_text(
            args.out.read_text(encoding="utf-8") + "\n---\n\n" + "\n".join(block), encoding="utf-8"
        )
    else:
        args.out.write_text("\n".join(header + block), encoding="utf-8")
    print(f"[load] 证据 -> {args.out}")
    raise SystemExit(0 if errors == 0 and p95 < 500 else 1)


if __name__ == "__main__":
    main()
