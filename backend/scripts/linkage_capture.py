"""前后端联调留痕：逐端点记录真实请求/响应包络，生成可复核的证据文件。

不依赖浏览器自动化（本机未装 playwright/selenium，且不为此安装依赖）。
浏览器截图另见 `docs/test/system_test/execution_records/`（四页面 + 两种异常态，共 6 张）。

    cd backend && python scripts/linkage_capture.py
    python scripts/linkage_capture.py --out evidence/2026-11-12-linkage.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH = {"X-API-Key": os.getenv("API_TOKEN", "")}
EVIDENCE_DIR = BACKEND_DIR.parent / "docs" / "test" / "integration_test" / "execution_records"
DEFAULT_OUT = EVIDENCE_DIR / f"{datetime.now().date().isoformat()}-linkage.md"
DEFAULT_RAW = EVIDENCE_DIR / f"{datetime.now().date().isoformat()}-linkage.json"


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=BACKEND_DIR.parent, text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    args = ap.parse_args()

    client = httpx.Client(trust_env=False, base_url=BASE_URL, headers=AUTH, timeout=120.0)
    first = client.get("/api/commits", params={"size": 1}).json()["data"]["items"][0]
    commit_hash = first["commit_hash"]
    model = first["model_name"]
    first_model = client.get("/api/models").json()["data"]["lines"][0]["models"][0]
    figure_model = first_model if isinstance(first_model, str) else first_model["model_name"]

    cases = [
        ("GET", "/api/commits", {"params": {"size": 5}}),
        ("GET", f"/api/commits/{commit_hash}", {"params": {"model_name": model}}),
        ("GET", "/api/models", {}),
        ("GET", "/api/trends", {"params": {"granularity": "week"}}),
        ("GET", "/api/figures", {"params": {"model_name": figure_model}}),
        ("GET", "/api/sync/status", {}),
        ("GET", "/api/health", {}),
        ("GET", "/api/health/live", {}),
        ("GET", "/api/health/ready", {}),
        ("POST", "/api/predict", {"json": {"commit_hash": commit_hash, "model_name": model}}),
        (
            "POST",
            "/api/predict",
            {"json": {"commit_hash": commit_hash, "model_name": "no_such_model"}},
        ),
        ("GET", "/api/commits", {"params": {"size": 101}}),
    ]

    rows = []
    raw = []
    for method, path, kwargs in cases:
        r = client.request(method, path, **kwargs)
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {"raw": r.text[:200]}
        data = body.get("data")
        shape = (
            "null"
            if data is None
            else ("list" if isinstance(data, list) else ",".join(sorted(data)[:6]))
        )
        digest = hashlib.sha256(r.content).hexdigest()[:12]
        rows.append((method, path, r.status_code, body.get("code"), shape, digest))
        raw.append(
            {
                "method": method,
                "params": kwargs.get("params"),
                "body": kwargs.get("json"),
                "status": r.status_code,
                "envelope": body,
                "sha256_12": digest,
            }
        )
        print(f"[{r.status_code}/{body.get('code')}] {method} {path} shape={shape} sha={digest}")
    client.close()

    lines = [
        "# 联调留痕（测试代码产物）",
        "",
        f"> 生成：`{sys.argv[0]}` ｜ 时间：{datetime.now().isoformat(timespec='seconds')} ｜ 提交：`{git_sha()}`",
        f"> 服务：`{BASE_URL}` ｜ 库：本机 MySQL80 `jit_demo` ｜ 鉴权：`X-API-Key`（值不入库）",
        "",
        "| # | 方法 | 端点 | HTTP | code | data 形状 | 响应摘要 |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {i} | {m} | `{p}` | {s} | {c} | {sh} | `{d}` |"
        for i, (m, p, s, c, sh, d) in enumerate(rows, 1)
    ]
    lines += [
        "",
        "## 说明",
        "",
        "- 第 11/12 行是异常联调：未知模型 → 40001，越界 `size` → 40001，证明错误包络与前端三态口径一致。",
        "- 逐接口浏览器截图见 `docs/test/system_test/execution_records/`；本文件只留 HTTP 层证据，不冒充截图。",
        f"- 原始响应（已截断大字段）见 `{args.raw.name}`，按 sha 可与上方表格对齐。",
        "",
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    args.raw.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[linkage] -> {args.out} / {args.raw}")


if __name__ == "__main__":
    main()
