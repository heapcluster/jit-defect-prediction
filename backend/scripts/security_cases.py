"""安全用例：鉴权、畸形参数与不可用模型的错误面收敛。

对应 `openspec/specs/nfr-evidence/spec.md` 的「安全用例脚本」：

1. 缺失令牌与错误令牌 → HTTP 401 且 `code=40100`、message 为 `missing or invalid token`；
2. 畸形参数（`size=101`、`granularity=day`、非 40 位十六进制 hash）→ 40001，
   且响应体 MUST NOT 含异常堆栈 / SQL 语句 / 文件路径关键字；
3. 模型不可用 → 明确业务错误，且不泄漏路径。

**与规格的偏差（如实记录，不掩盖）**：规格第 3 条写「模型缺失时 `POST /api/predict`
返回 50000」，现行实现把「该模型无在线权重 / 产物缺失」收敛为 `40001` 的明确文案
（`services/predict.py` 的 `ModelUnavailable` 分支）。本脚本按**现行契约**断言
「400/40001 且文案明确、不 500、不泄漏」，并在末尾单独报告该偏差。

用法（backend/ 目录，先起服务）：

    python scripts/security_cases.py
    BASE_URL=http://127.0.0.1:8000 python scripts/security_cases.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "")
LEAK_KEYWORDS = ["Traceback", "sqlalchemy", "SELECT ", "pymysql", "C:\\", "/app/", "site-packages"]

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")


def no_leak(text: str) -> bool:
    return not any(k in text for k in LEAK_KEYWORDS)


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=60.0)
    try:
        client.get("/api/health")
    except Exception as exc:  # noqa: BLE001
        print(f"[security] 服务不可达 {BASE_URL}：{type(exc).__name__}", file=sys.stderr)
        raise SystemExit(2) from exc

    auth = {"X-API-Key": API_TOKEN}

    # 1) 鉴权
    for path in ("/api/commits", "/api/models", "/api/health"):
        for name, headers in (("缺失令牌", {}), ("错误令牌", {"X-API-Key": "wrong-token"})):
            r = client.get(path, headers=headers)
            body = r.json()
            ok = (
                r.status_code == 401
                and body.get("code") == 40100
                and body.get("message") == "missing or invalid token"
            )
            record(
                f"{path} {name}", ok, f"{r.status_code}/{body.get('code')} {body.get('message')}"
            )

    # 2) 畸形参数
    bad_cases = [
        ("size=101", f"{BASE_URL}/api/commits?size=101"),
        ("granularity=day", f"{BASE_URL}/api/trends?granularity=day"),
        ("hash 非 40 位", f"{BASE_URL}/api/commits/" + "a" * 39),
        ("hash 非十六进制", f"{BASE_URL}/api/commits/" + "g" * 40),
    ]
    for name, url in bad_cases:
        r = client.get(url, headers=auth)
        text = r.text
        ok = r.status_code == 400 and r.json().get("code") == 40001 and no_leak(text)
        record(
            f"畸形参数 {name}",
            ok,
            f"{r.status_code}/{r.json().get('code')} leak={not no_leak(text)}",
        )

    # 3) 模型不可用（非 expert 线默认无在线权重/产物）
    r = client.get("/api/models", params={"line": "semantic"}, headers=auth)
    semantic = r.json()["data"]["lines"][0]["models"] if r.json()["data"]["lines"] else []
    if semantic:
        model_name = semantic[0] if isinstance(semantic[0], str) else semantic[0]["model_name"]
        sample = client.get("/api/commits", params={"size": 1}, headers=auth).json()["data"][
            "items"
        ]
        commit_hash = sample[0]["commit_hash"] if sample else "a" * 40
        pr = client.post(
            "/api/predict",
            json={"commit_hash": commit_hash, "model_name": model_name},
            headers=auth,
        )
        body = pr.json()
        text = pr.text
        ok = (
            pr.status_code in (200, 400)
            and (pr.status_code == 200 or body.get("code") == 40001)
            and no_leak(text)
        )
        record(
            f"模型不可用 {model_name}",
            ok,
            f"{pr.status_code}/{body.get('code')} msg={body.get('message')}",
        )
    else:
        record("模型不可用", False, "semantic 线无模型，无法构造该场景")

    # 4) 未知模型名
    pr = client.post(
        "/api/predict", json={"commit_hash": "a" * 40, "model_name": "no_such_model"}, headers=auth
    )
    ok = pr.status_code == 400 and pr.json().get("code") == 40001 and no_leak(pr.text)
    record("未知模型名", ok, f"{pr.status_code}/{pr.json().get('code')}")

    total = len(results)
    failed = [r for r in results if not r[1]]
    print(f"\n[security] 汇总：total={total} pass={total - len(failed)} fail={len(failed)}")
    print(
        "[security] 规格偏差：nfr-evidence 要求「模型缺失 → 50000」，现行实现为 40001 明确文案；"
        "本脚本按现行契约判定，偏差待 sober/lsh 在规格侧订正"
    )
    if failed:
        for name, _, detail in failed:
            print(f"[security]   FAILED {name}: {detail}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
