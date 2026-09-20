"""安全用例脚本（change nfr-evidence-scripts，周报任务 10）。

两组用例 + 全响应泄露扫描：
  组一 鉴权：缺失令牌 / 错误令牌 → HTTP 401 且 code=40100、message=missing or invalid token
  组二 畸形参数：size=101 / granularity=day / 非 40 位十六进制 hash → 400 且 code=40001
  扫描：所有用例响应体不得含 Traceback / 堆栈帧 / SQL 关键字 / 服务器文件路径
另引用 5.3 真库自检的 50000 掩码例（模型缺失场景，见 evidence-5.3-mysql.md）。

用法：
  API_TOKEN=... python scripts/security_cases.py --base-url http://127.0.0.1:8000 --out scripts/evidence/security-2026-09-19.md
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

LEAK_PATTERNS = [
    re.compile(r"Traceback", re.IGNORECASE),
    re.compile(r"\bSELECT\b.*\bFROM\b", re.IGNORECASE),
    re.compile(r"[A-Za-z]:\\[^\s\"]+\.py"),
    re.compile(r"/[a-z_]+/[a-z_]+\.py\s*,\s*line", re.IGNORECASE),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    token = os.environ.get("API_TOKEN", "")
    if not token:
        print("缺少环境变量 API_TOKEN", file=sys.stderr)
        return 2
    good = {"X-API-Key": token}

    def check(name: str, fn: callable) -> tuple[str, bool, str]:
        try:
            ok, detail = fn()
        except httpx.HTTPError as exc:
            return name, False, f"请求异常 {exc}"
        return name, ok, detail

    with httpx.Client(timeout=30) as client:
        def s1() -> tuple[bool, str]:
            r = client.get(f"{args.base_url}/api/commits")
            body = r.json()
            ok = r.status_code == 401 and body["code"] == 40100 and body["message"] == "missing or invalid token"
            return ok, f"HTTP {r.status_code} code={body['code']} message={body['message']}"

        def s2() -> tuple[bool, str]:
            r = client.get(f"{args.base_url}/api/commits", headers={"X-API-Key": "wrong-token"})
            body = r.json()
            ok = r.status_code == 401 and body["code"] == 40100
            return ok, f"HTTP {r.status_code} code={body['code']}"

        def s3() -> tuple[bool, str]:
            r = client.get(f"{args.base_url}/api/commits", params={"size": 101}, headers=good)
            body = r.json()
            ok = r.status_code == 400 and body["code"] == 40001 and "size" in body["message"]
            return ok, f"HTTP {r.status_code} code={body['code']} message={body['message']}"

        def s4() -> tuple[bool, str]:
            r = client.get(f"{args.base_url}/api/trends", params={"granularity": "day"}, headers=good)
            body = r.json()
            ok = r.status_code == 400 and body["code"] == 40001 and "granularity" in body["message"]
            return ok, f"HTTP {r.status_code} code={body['code']} message={body['message']}"

        def s5() -> tuple[bool, str]:
            r = client.get(f"{args.base_url}/api/commits/{'a' * 39}", headers=good)
            body = r.json()
            ok = r.status_code == 400 and body["code"] == 40001
            return ok, f"HTTP {r.status_code} code={body['code']}"

        results = [check(n, f) for n, f in [("S1 缺失令牌", s1), ("S2 错误令牌", s2), ("S3 size=101", s3), ("S4 granularity=day", s4), ("S5 hash 39 位", s5)]]

        leaks: list[str] = []
        probes = [
            ("GET /api/commits 无令牌", lambda: client.get(f"{args.base_url}/api/commits")),
            ("GET size=101", lambda: client.get(f"{args.base_url}/api/commits", params={"size": 101}, headers=good)),
            ("GET granularity=day", lambda: client.get(f"{args.base_url}/api/trends", params={"granularity": "day"}, headers=good)),
            ("GET hash 39 位", lambda: client.get(f"{args.base_url}/api/commits/{'a' * 39}", headers=good)),
        ]
        for label, probe in probes:
            r = probe()
            for pat in LEAK_PATTERNS:
                if pat.search(r.text):
                    leaks.append(f"{label} 响应命中泄露模式 {pat.pattern}")

    all_ok = all(ok for _, ok, _ in results) and not leaks
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# 安全用例证据 {datetime.now(timezone.utc).date().isoformat()}", "", f"- 服务：{args.base_url}", f"- 命令：`API_TOKEN=*** python scripts/security_cases.py --base-url {args.base_url} --out {args.out}`", "", "| 用例 | 结果 | 实际 |", "|---|---|---|"]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines.append(f"| 泄露扫描（4 探针 × 4 模式） | {'PASS' if not leaks else 'FAIL'} | {'无命中' if not leaks else '; '.join(leaks)} |")
    lines.append("| 50000 掩码（模型缺失） | 引用 | 见 evidence-5.3-mysql.md：500 响应 message=internal error，不含堆栈/SQL/路径 |")
    lines.append("")
    lines.append("**汇总：全部通过**" if all_ok else "**汇总：存在 FAIL，禁止作为证据提交**")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name} :: {detail}")
    print(f"{'PASS' if not leaks else 'FAIL'} 泄露扫描 :: {'无命中' if not leaks else leaks}")
    print(f"证据写入 {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
