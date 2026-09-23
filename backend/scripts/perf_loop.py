"""性能压测脚本（change nfr-evidence-scripts，周报任务 10）。

对 POST /api/predict 循环发送 N 次请求（默认 100），输出 p50/p95/p99 与最大值，
标注目标 p95<500ms 与达标判定。独立 HTTP 客户端，不 import 应用代码（design D2）。

用法：
  python scripts/perf_loop.py --base-url http://127.0.0.1:8000 --model-source "占位模型（待真 .pkl 重跑）" \
      --out scripts/evidence/perf-2026-09-19.md
令牌从环境变量 API_TOKEN 读取。
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


def percentile(sorted_values: list[float], q: float) -> float:
    idx = max(0, math.ceil(q * len(sorted_values)) - 1)
    return sorted_values[idx]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--model-source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    token = os.environ.get("API_TOKEN", "")
    if not token:
        print("缺少环境变量 API_TOKEN", file=sys.stderr)
        return 2
    headers = {"X-API-Key": token}

    with httpx.Client(timeout=30) as client:
        try:
            resp = client.get(f"{args.base_url}/api/commits", params={"size": 1}, headers=headers)
        except httpx.HTTPError as exc:
            print(f"服务不可达：{exc}", file=sys.stderr)
            return 1
        if resp.status_code != 200:
            print(f"鉴权或服务异常：HTTP {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            return 1
        items = resp.json()["data"]["items"]
        if not items:
            print("库中无预测行，无法压测 predict", file=sys.stderr)
            return 1
        target = items[0]["commit_hash"]

        latencies: list[float] = []
        errors = 0
        for _ in range(args.n):
            start = time.perf_counter()
            r = client.post(f"{args.base_url}/api/predict", json={"commit_hash": target}, headers=headers)
            latencies.append((time.perf_counter() - start) * 1000)
            if r.status_code != 200:
                errors += 1

    if errors:
        print(f"{errors}/{args.n} 次请求失败，证据不可信，退出", file=sys.stderr)
        return 1

    ordered = sorted(latencies)
    p50, p95, p99, mx = (percentile(ordered, q) for q in (0.5, 0.95, 0.99, 1.0))
    verdict = "达标" if p95 < 500 else "未达标"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"""# 性能压测证据 {datetime.now(timezone.utc).date().isoformat()}

- 靶子：`POST /api/predict`（契约三 §4 指定，不用查询接口代替）
- 服务：{args.base_url}（构建来源见提交记录）
- 模型来源：{args.model_source}
- 请求数：{args.n}（成功 {args.n - errors} / 失败 {errors}）
- 命令：`python scripts/perf_loop.py --base-url {args.base_url} --n {args.n} --model-source "{args.model_source}" --out {args.out}`

| 分位 | 耗时(ms) |
|---|---|
| p50 | {p50:.1f} |
| p95 | {p95:.1f} |
| p99 | {p99:.1f} |
| max | {mx:.1f} |

**目标 p95 < 500ms：{verdict}**（分位数口径：升序第 ceil(q*n) 位，design D4；非平均值）
""",
        encoding="utf-8",
    )
    print(f"p50={p50:.1f}ms p95={p95:.1f}ms p99={p99:.1f}ms max={mx:.1f}ms → {verdict}；证据写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
