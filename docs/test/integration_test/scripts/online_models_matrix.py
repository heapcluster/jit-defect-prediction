"""25 模型在线矩阵：逐个 `POST /api/predict`，输出逐条结果并作为测试门禁。

用法（先起后端）：

    cd backend && python scripts/online_models_matrix.py
    python scripts/online_models_matrix.py --json out.json
    BASE_URL=http://127.0.0.1:8001 python scripts/online_models_matrix.py

退出码：全部 25 个模型可预测 → 0；任一失败 → 1（可直接作为 CI/验收门禁）。
当前已知阻塞：`tabnet_semantic_v1` / `tabnet_fused_v1` 的 CUDA 权重（#222）。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH = {"X-API-Key": os.getenv("API_TOKEN", "")}
PIPELINES = REPO_ROOT / "data_model" / "pipelines"
NPZ = PIPELINES / "semantic" / "data" / "semantic_embeddings.npz"
TEXT_CSV = PIPELINES / "e2e" / "data" / "commit_text.csv"


def covered_hashes() -> set[str] | None:
    """语义表与 e2e 文本表都覆盖的 hash 集合；缺表时返回 None（不静默跳过）。"""
    if not NPZ.is_file() or not TEXT_CSV.is_file():
        return None
    import numpy as np  # noqa: PLC0415 - 只在需要时加载大依赖

    npz = np.load(NPZ, allow_pickle=False)
    sem = {str(h).lower() for h in npz["commit_hash"]}
    with TEXT_CSV.open(encoding="utf-8", newline="") as fh:
        e2e = {(row.get("commit_hash") or "").lower() for row in csv.DictReader(fh)}
    return sem & e2e


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, help="把逐条结果写成 JSON")
    ap.add_argument("--size", type=int, default=100, help="从风险列表取多少条候选提交（<=100）")
    args = ap.parse_args()

    # .env 里可能带失效的 HTTP_PROXY，本机请求必须绕过环境代理
    client = httpx.Client(trust_env=False, base_url=BASE_URL, headers=AUTH, timeout=600.0)
    lines = client.get("/api/models").json()["data"]["lines"]
    models = [
        (m if isinstance(m, str) else m["model_name"], line["line"])
        for line in lines
        for m in line["models"]
    ]
    rows = client.get("/api/commits", params={"size": min(args.size, 100)}).json()["data"]["items"]
    if not rows:
        print("[matrix] 库内无已预测提交，先跑 sync 或导入 data_init.sql", file=sys.stderr)
        raise SystemExit(2)

    both = covered_hashes()
    if both is None:
        print(
            "[matrix] 语义表或 e2e 文本表不在约定路径，本次只用默认提交（semantic/fused/e2e 可能失败）",
            file=sys.stderr,
        )
    commit = next(
        (r["commit_hash"] for r in rows if both and r["commit_hash"] in both),
        rows[0]["commit_hash"],
    )
    print(f"[matrix] models={len(models)} commit={commit}")

    results = []
    for name, line in models:
        started = time.perf_counter()
        r = client.post("/api/predict", json={"commit_hash": commit, "model_name": name})
        body = r.json()
        ok = r.status_code == 200 and body.get("code") == 0
        risk = body.get("data", {}).get("risk_score") if ok else None
        sec = round(time.perf_counter() - started, 2)
        results.append(
            {
                "model": name,
                "line": line,
                "status": r.status_code,
                "code": body.get("code"),
                "risk_score": risk,
                "sec": sec,
                "message": None if ok else body.get("message"),
            }
        )
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name:26} {line:9} {r.status_code}/{body.get('code')} risk={risk} {sec}s"
            + ("" if ok else f" {body.get('message')}")
        )

    passed = [x for x in results if x["risk_score"] is not None]
    print(
        f"\n[matrix] 汇总：total={len(results)} pass={len(passed)} fail={len(results) - len(passed)}"
    )
    if args.json:
        args.json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[matrix] JSON -> {args.json}")
    raise SystemExit(0 if len(passed) == len(results) else 1)


if __name__ == "__main__":
    main()
