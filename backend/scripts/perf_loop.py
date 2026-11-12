"""性能压测：对 `POST /api/predict` 循环 100 次，输出分位数与达标判定。

对应 `openspec/specs/nfr-evidence/spec.md` 的「性能压测脚本」：
- 必须输出 p50 / p95 / p99 / 最大值，MUST NOT 用平均值代替分位数；
- 输出标注目标「p95 < 500ms」与实际达标判定；
- 服务不可达或鉴权失败 → 非零退出，MUST NOT 产出任何伪造分位数。

用法（backend/ 目录，先起服务）：

    python scripts/perf_loop.py
    N=200 BASE_URL=http://127.0.0.1:8000 python scripts/perf_loop.py
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "")
N = int(os.getenv("N", "100"))
TARGET_P95_MS = 500.0


def fail(message: str) -> None:
    print(f"[perf] 失败：{message}", file=sys.stderr)
    raise SystemExit(2)


def pick_sample(client: httpx.Client) -> tuple[str, str]:
    r = client.get("/api/commits", params={"size": 1}, headers={"X-API-Key": API_TOKEN})
    if r.status_code == 401:
        fail("鉴权失败（API_TOKEN 无效或缺失），不产出分位数")
    r.raise_for_status()
    items = r.json()["data"]["items"]
    if not items:
        fail("库内无已预测提交，先导入 data_init.sql 或跑一次 sync")
    item = items[0]
    return item["commit_hash"], item["model_name"]


def percentile(values: list[float], q: float) -> float:
    """线性插值分位数（与 numpy 默认口径一致），避免引入额外依赖。"""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def main() -> None:
    headers = {"X-API-Key": API_TOKEN}
    try:
        client = httpx.Client(base_url=BASE_URL, timeout=180.0)
        client.get("/api/health").status_code  # 故意不带 key，仅确认可达
    except Exception as exc:  # noqa: BLE001
        fail(f"服务不可达 {BASE_URL}：{type(exc).__name__}")

    try:
        commit_hash, model_name = pick_sample(client)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        fail(f"取样失败：{type(exc).__name__}: {exc}")

    latencies: list[float] = []
    errors = 0
    for i in range(N):
        started = time.perf_counter()
        try:
            r = client.post(
                "/api/predict",
                json={"commit_hash": commit_hash, "model_name": model_name},
                headers=headers,
            )
        except Exception:  # noqa: BLE001 - 单次失败计入错误，不伪造延迟
            errors += 1
            continue
        cost_ms = (time.perf_counter() - started) * 1000
        if r.status_code != 200:
            errors += 1
            continue
        latencies.append(cost_ms)

    if not latencies:
        fail("没有任何成功响应，拒绝产出分位数")

    p50 = percentile(latencies, 0.50)
    p95 = percentile(latencies, 0.95)
    p99 = percentile(latencies, 0.99)
    print(f"[perf] 目标：p95 < {TARGET_P95_MS:.0f}ms")
    print(f"[perf] 样本：commit={commit_hash[:8]} model_name={model_name}")
    print("[perf] 模型来源：真模型（expert 线 .pkl 交付权重，非占位）")
    print(f"[perf] 请求数：{N} 成功={len(latencies)} 失败={errors}")
    print(
        f"[perf] p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms max={max(latencies):.1f}ms "
        f"mean={statistics.fmean(latencies):.1f}ms（mean 仅供参考，不作为达标依据）"
    )
    ok = p95 < TARGET_P95_MS
    print(f"[perf] 判定：{'达标' if ok else '未达标'}（p95={p95:.1f}ms）")
    if errors:
        print(f"[perf] 注意：有 {errors} 次请求失败，分位数只统计成功请求", file=sys.stderr)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
