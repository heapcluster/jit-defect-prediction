"""验收测试用例设计：从活规格抽取全部 Scenario，并实跑可自动判定的子集。

注意职责边界：本脚本**只生成用例与执行结果**，不出验收结论、不代签。
正式验收方案/报告由 sober 整理，neon 现场判定并签字（AI-R5）。

    cd backend && python scripts/acceptance_scenarios.py
    python scripts/acceptance_scenarios.py --out evidence/2026-11-12-acceptance-checklist.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH = {"X-API-Key": os.getenv("API_TOKEN", "")}
SPECS = REPO_ROOT / "openspec" / "specs"
DEFAULT_OUT = (
    BACKEND_DIR.parent
    / "docs"
    / "test"
    / "integration_test"
    / "execution_records"
    / f"{date.today().isoformat()}-acceptance-checklist.md"
)


def collect_scenarios() -> list[dict]:
    items = []
    for spec in sorted(SPECS.glob("*/spec.md")):
        requirement = ""
        for raw in spec.read_text(encoding="utf-8").splitlines():
            if raw.startswith("### Requirement:"):
                requirement = raw.split(":", 1)[1].strip()
            elif raw.startswith("#### Scenario:"):
                items.append(
                    {
                        "capability": spec.parent.name,
                        "requirement": requirement,
                        "scenario": raw.split(":", 1)[1].strip(),
                        "mode": "人工判定",
                        "result": "未执行",
                    }
                )
    return items


def auto_checks() -> list[dict]:
    """可由 API 直接判定的验收子集；每条都是真实请求，不写推断结论。"""
    client = httpx.Client(trust_env=False, base_url=BASE_URL, headers=AUTH, timeout=120.0)
    checks: list[dict] = []

    def add(name: str, fn) -> None:  # noqa: ANN001
        try:
            ok, detail = fn(client)
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        checks.append({"name": name, "result": "PASS" if ok else "FAIL", "detail": str(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")

    add(
        "健康探针 status/db",
        lambda c: (
            lambda d: (
                d["status"] == "ok" and d["db"] == "up",
                f"status={d['status']} db={d['db']}",
            )
        )(c.get("/api/health").json()["data"]),
    )
    add(
        "四线 25 模型清单",
        lambda c: (
            lambda d: (
                len([m for line in d["lines"] for m in line["models"]]) == 25,
                f"lines={[line['line'] for line in d['lines']]}",
            )
        )(c.get("/api/models").json()["data"]),
    )
    add(
        "风险列表降序且概率在 [0,1]",
        lambda c: (
            lambda d: (
                all(0 <= i["risk_score"] <= 1 for i in d["items"])
                and all(
                    d["items"][i]["risk_score"] >= d["items"][i + 1]["risk_score"]
                    for i in range(len(d["items"]) - 1)
                ),
                f"total={d['total']} 首页={len(d['items'])}",
            )
        )(c.get("/api/commits", params={"size": 20}).json()["data"]),
    )

    def check_detail(c):  # noqa: ANN001
        lst = c.get("/api/commits", params={"size": 1}).json()["data"]["items"][0]
        det = c.get(
            f"/api/commits/{lst['commit_hash']}",
            params={"model_name": lst["model_name"]},
        ).json()["data"]
        return (
            abs(lst["risk_score"] - det["risk_score"]) < 1e-9,
            f"list={lst['risk_score']} detail={det['risk_score']} model={lst['model_name']}",
        )

    add("详情与列表同模型风险一致", check_detail)
    add(
        "未预测/不存在提交可区分",
        lambda c: (
            lambda r: (
                r.status_code == 404 and r.json().get("code") == 40400,
                f"{r.status_code}/{r.json().get('code')} {r.json().get('message')}",
            )
        )(c.get("/api/commits/" + "f" * 40)),
    )

    def check_predict(c):  # noqa: ANN001
        first = c.get("/api/commits", params={"size": 1}).json()["data"]["items"][0]
        p = c.post(
            "/api/predict",
            json={"commit_hash": first["commit_hash"], "model_name": first["model_name"]},
        ).json()["data"]
        return (
            0 <= p["risk_score"] <= 1 and len(p["features"]) == 14,
            f"risk={p['risk_score']} features={len(p['features'])}",
        )

    add("预测概率区间与 14 维特征", check_predict)
    add(
        "趋势周期格式",
        lambda c: (
            lambda d: (
                all(re.fullmatch(r"\d{4}-W\d{2}", s["period"]) for s in d["series"]),
                f"periods={len(d['series'])}",
            )
        )(c.get("/api/trends", params={"granularity": "week"}).json()["data"]),
    )

    def check_figures(c):  # noqa: ANN001
        first = c.get("/api/models").json()["data"]["lines"][0]["models"][0]
        name = first if isinstance(first, str) else first["model_name"]
        f = c.get("/api/figures", params={"model_name": name})
        s = httpx.get(BASE_URL + "/static/figures/", trust_env=False, timeout=30.0)  # 不带 key
        return (
            f.status_code == 200 and len(f.json()["data"]["figures"]) > 0 and s.status_code == 401,
            f"figures={len(f.json()['data']['figures'])} static_no_key={s.status_code}",
        )

    add("图集与静态资源鉴权", check_figures)

    def check_no_token(c):  # noqa: ANN001
        r = httpx.get(BASE_URL + "/api/commits", trust_env=False, timeout=30.0)
        return r.status_code == 401 and r.json().get(
            "code"
        ) == 40100, f"{r.status_code}/{r.json().get('code')}"

    add("缺令牌 401/40100", check_no_token)
    add(
        "非法参数 40001",
        lambda c: (
            lambda r: (
                r.status_code == 400 and r.json().get("code") == 40001,
                f"{r.status_code}/{r.json().get('code')}",
            )
        )(c.get("/api/commits", params={"size": 101})),
    )
    client.close()
    return checks


def render(scenarios: list[dict], checks: list[dict]) -> str:
    passed = len([c for c in checks if c["result"] == "PASS"])
    lines = [
        "# 验收用例清单（测试代码产物，非验收报告）",
        "",
        "> 本文件由 `backend/scripts/acceptance_scenarios.py` 生成：**只含用例设计与自动执行结果**。",
        "> 正式验收方案/报告由 sober 整理；逐条「通过/失败/未执行」由 neon 现场判定并签字（AI-R5）。",
        "",
        f"> 生成日期：{date.today().isoformat()} ｜ 活规格 Scenario 共 **{len(scenarios)}** 条 ｜ 自动子集 **{passed}/{len(checks)}** 通过",
        "",
        "## 1 · 自动可判定子集（本次实跑）",
        "",
        "| 用例 | 结果 | 实测 |",
        "|---|---|---|",
    ]
    lines += [f"| {c['name']} | {c['result']} | {c['detail']} |" for c in checks]
    lines += [
        "",
        "## 2 · 全部 Scenario 现场对照表（结果列留给 neon 填写）",
        "",
        "| # | 能力 | Requirement | Scenario | 判定方式 | 结果 |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {i} | {s['capability']} | {s['requirement']} | {s['scenario']} | {s['mode']} | {s['result']} |"
        for i, s in enumerate(scenarios, 1)
    ]
    lines += [
        "",
        "## 3 · 使用说明",
        "",
        "- 第 1 节是脚本实跑结果，不能代替现场验收；第 2 节每条需人工点验并写结论。",
        "- 「尚未预测」与「系统错误」的区分必须现场核对：详情 `risk_score=null` vs 错误码 40400/50000。",
        "- 发现不满足项要挂 GitHub Issue 并回填编号，交由 sober 汇总进验收文档。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--json", type=Path, help="可选：把 Scenario 结构化结果写入 JSON")
    args = ap.parse_args()

    scenarios = collect_scenarios()
    checks = auto_checks()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(scenarios, checks), encoding="utf-8")
    print(f"[acceptance] 活规格 Scenario={len(scenarios)} 自动子集={len(checks)} -> {args.out}")
    if args.json:
        args.json.write_text(
            json.dumps({"scenarios": scenarios, "auto": checks}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[acceptance] JSON -> {args.json}")


if __name__ == "__main__":
    main()
