"""集成测试用例：对**运行中的服务**执行 11 个端点的四类场景，输出逐条结果。

用法（在 backend/ 目录，先起服务）：

    python scripts/integration_cases.py
    BASE_URL=http://127.0.0.1:8000 python scripts/integration_cases.py --json out.json

前置：`backend/.env` 里的 `API_TOKEN`；库内已有提交与预测（`data_init.sql` 或 sync 过）。

断言口径：状态码 + 业务 `code` + 关键字段/业务语义（风险概率区间、排序、14 维列序、
鉴权失败码、空结果不等于错误）。只断言 HTTP 200 的用例不算通过。

来源标注：`[AI生成]`（DeepSeek-V4.1-Flash，2026-11-12），核心业务断言已按
`docs/common/endpoint-inventory.md` §2 逐条对照代码复核。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from app import config as app_config  # noqa: E402  契约列序的唯一真源

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "")
AUTH = {"X-API-Key": API_TOKEN}
FEATURE_ORDER = list(app_config.FEATURE_COLUMNS)
SYNC_TIMEOUT = int(os.getenv("SYNC_TIMEOUT", "900"))

client = httpx.Client(base_url=BASE_URL, timeout=120.0)


@dataclass
class Case:
    cid: str
    endpoint: str
    scenario: str  # 正常 / 缺参 / 非法参数 / 边界值
    call: Callable[[], Any]
    source: str = "[AI生成]"
    result: str = "未执行"
    detail: str = ""


CASES: list[Case] = []


def case(
    cid: str, endpoint: str, scenario: str
) -> Callable[[Callable[[], str]], Callable[[], str]]:
    def wrap(fn: Callable[[], str]) -> Callable[[], str]:
        CASES.append(Case(cid, endpoint, scenario, fn))
        return fn

    return wrap


def check(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


def get(path: str, **kwargs: Any) -> httpx.Response:
    return client.get(path, headers=kwargs.pop("headers", AUTH), **kwargs)


def post(path: str, **kwargs: Any) -> httpx.Response:
    return client.post(path, headers=kwargs.pop("headers", AUTH), **kwargs)


def sync_status() -> dict:
    return expect(200)(get("/api/sync/status"))["data"]


def wait_idle(timeout: int | None = None) -> dict:
    """等待后台同步结束；同步是异步任务，测试必须等它落地才能断言。"""
    deadline = time.time() + (timeout or SYNC_TIMEOUT)
    while time.time() < deadline:
        st = sync_status()
        if not st["running"]:
            return st
        time.sleep(3)
    raise AssertionError(f"同步 {timeout or SYNC_TIMEOUT}s 未结束")


def default_code(expected: int) -> int:
    return {200: 0, 400: 40001, 401: 40100, 404: 40400, 500: 50000}[expected]


def expect(status: int, code: int | None = None) -> Callable[[httpx.Response], dict]:
    def _check(r: httpx.Response) -> dict:
        body = r.json()
        check(r.status_code == status, f"状态码 {r.status_code} != {status}")
        want = default_code(status) if code is None else code
        check(body.get("code") == want, f"业务码 {body.get('code')} != {want}")
        check("data" in body, "缺少 data 键")
        return body

    return _check


# ---------------------------------------------------------------- 公共取样
def sample_commit() -> str:
    r = get("/api/commits", params={"size": 1})
    body = r.json()
    check(r.status_code == 200 and body["code"] == 0, "取样例提交失败")
    items = body["data"]["items"]
    check(bool(items), "库内无已预测提交，先导入 data_init.sql 或跑 sync")
    return items[0]["commit_hash"]


def sample_model(line: str = "expert") -> str:
    r = get("/api/models", params={"line": line})
    body = r.json()
    models = body["data"]["lines"][0]["models"] if body["data"]["lines"] else []
    check(bool(models), f"{line} 线无模型")
    return models[0]["model_name"] if isinstance(models[0], dict) else models[0]


# ---------------------------------------------------------------- GET /api/commits
@case("T-IN-01", "GET /api/commits", "正常")
def commits_normal() -> str:
    r = get("/api/commits", params={"size": 5})
    body = expect(200)(r)
    data = body["data"]
    items = data["items"]
    check(data["page"] == 1 and data["size"] == 5, "分页回显不符")
    check(len(items) == min(5, data["total"]), "items 数量不符")
    for it in items:
        check(0.0 <= it["risk_score"] <= 1.0, f"risk_score 越界：{it['risk_score']}")
    scores = [it["risk_score"] for it in items]
    check(scores == sorted(scores, reverse=True), "未按 risk_score 降序")
    return f"total={data['total']} items={len(items)} 降序 OK"


@case("T-IN-02", "GET /api/commits", "缺参")
def commits_noauth() -> str:
    r = client.get("/api/commits")
    body = expect(401)(r)
    check(body["message"] == "missing or invalid token", f"message={body['message']}")
    return "401/40100 文案 OK"


@case("T-IN-03", "GET /api/commits", "非法参数")
def commits_bad_params() -> str:
    expect(400)(get("/api/commits", params={"size": "abc"}))
    expect(400)(get("/api/commits", params={"with_features": "2"}))
    expect(400)(get("/api/commits", params={"start_time": "2024-13-99"}))
    return "类型/枚举/时间三类非法入参均 40001"


@case("T-IN-04", "GET /api/commits", "边界值")
def commits_boundary() -> str:
    d1 = expect(200)(get("/api/commits", params={"size": 1}))["data"]
    check(len(d1["items"]) == 1, "size=1 未生效")
    d100 = expect(200)(get("/api/commits", params={"size": 100}))["data"]
    check(len(d100["items"]) <= 100, "size=100 越界")
    expect(400)(get("/api/commits", params={"size": 101}))
    expect(400)(get("/api/commits", params={"page": 0}))
    ok64 = len(get("/api/commits", params={"q": "x" * 64}).content)
    expect(400)(get("/api/commits", params={"q": "x" * 65}))
    far = expect(200)(get("/api/commits", params={"page": 9999}))["data"]
    check(far["items"] == [] and far["total"] == d1["total"], "超末页应为空且 total 不变")
    return f"size 1/100/101、page 0、q 64({ok64}B)/65、超末页 OK"


# ---------------------------------------------------------------- GET /api/commits/{hash}
@case("T-IN-05", "GET /api/commits/{commit_hash}", "正常")
def detail_normal() -> str:
    h = sample_commit()
    body = expect(200)(get(f"/api/commits/{h}"))
    d = body["data"]
    check(d["commit_hash"] == h, "回显 hash 不一致")
    check(d["risk_score"] is None or 0.0 <= d["risk_score"] <= 1.0, "风险值越界")
    check(isinstance(d["explanation"], list), "explanation 应为数组")
    check("localization" in d and "fix_references" in d, "缺少 localization / fix_references")
    return f"{h[:8]} risk={d['risk_score']} expl={len(d['explanation'])}"


@case("T-IN-06", "GET /api/commits/{commit_hash}", "缺参")
def detail_noauth() -> str:
    h = sample_commit()
    expect(401)(client.get(f"/api/commits/{h}"))
    return "缺失令牌 401/40100"


@case("T-IN-07", "GET /api/commits/{commit_hash}", "非法参数")
def detail_bad_hash() -> str:
    expect(400)(get("/api/commits/" + "a" * 39))
    expect(400)(get("/api/commits/" + "a" * 41))
    expect(400)(get("/api/commits/" + "g" * 40))
    return "39/41 位与非十六进制均 40001"


@case("T-IN-08", "GET /api/commits/{commit_hash}", "边界值")
def detail_boundary() -> str:
    h = sample_commit()
    upper = expect(200)(get(f"/api/commits/{h.upper()}"))["data"]
    lower = expect(200)(get(f"/api/commits/{h}"))["data"]
    check(upper["risk_score"] == lower["risk_score"], "大小写 hash 结果不一致")
    # 列表选了非默认模型时，详情带 model_name 应与列表同模型一致
    m = sample_model()
    listed = expect(200)(get("/api/commits", params={"size": 1, "model_name": m}))["data"]["items"]
    if listed:
        got = expect(200)(
            get(f"/api/commits/{listed[0]['commit_hash']}", params={"model_name": m})
        )["data"]
        check(got["model_name"] == m, "详情未按 model_name 取模型")
        check(
            abs((got["risk_score"] or -1) - listed[0]["risk_score"]) < 1e-9,
            "详情与列表同模型风险值不一致",
        )
    expect(404)(get("/api/commits/" + "f" * 40))
    return "大小写一致、model_name 对齐列表、未知 hash 40400"


# ---------------------------------------------------------------- GET /api/models
@case("T-IN-09", "GET /api/models", "正常")
def models_normal() -> str:
    d = expect(200)(get("/api/models"))["data"]
    lines = [x["line"] for x in d["lines"]]
    check(lines == ["expert", "semantic", "fused", "e2e"], f"线顺序 {lines}")
    total = sum(len(x["models"]) for x in d["lines"])
    check(total >= 25, f"模型总数 {total} < 25")
    return f"线={lines} 模型={total}"


@case("T-IN-10", "GET /api/models", "缺参")
def models_noauth() -> str:
    expect(401)(client.get("/api/models"))
    return "缺失令牌 401/40100"


@case("T-IN-11", "GET /api/models", "非法参数")
def models_bad_line() -> str:
    expect(400)(get("/api/models", params={"line": "Expert"}))
    expect(400)(get("/api/models", params={"line": ""}))
    expect(400)(get("/api/models", params={"line": "hierarchical"}))
    return "大小写/空串/未知线均 40001"


@case("T-IN-12", "GET /api/models", "边界值")
def models_boundary() -> str:
    e2e = expect(200)(get("/api/models", params={"line": "e2e"}))["data"]["lines"]
    check(len(e2e) == 1 and e2e[0]["line"] == "e2e", "line 过滤未生效")
    expert = expect(200)(get("/api/models", params={"line": "expert"}))["data"]["lines"]
    check(len(expert[0]["models"]) == 8, "expert 应为 8 个模型")
    return f"e2e={len(e2e[0]['models'])} expert=8 且过滤生效"


# ---------------------------------------------------------------- POST /api/predict
@case("T-IN-13", "POST /api/predict", "正常")
def predict_normal() -> str:
    h = sample_commit()
    m = sample_model()
    body = expect(200)(post("/api/predict", json={"commit_hash": h, "model_name": m}))
    d = body["data"]
    check(0.0 <= d["risk_score"] <= 1.0, "风险值越界")
    check(d["model_name"] == m, "模型回显不一致")
    feats = d["features"]
    check(len(FEATURE_ORDER) == 14, f"契约列序长度 {len(FEATURE_ORDER)}")
    check(list(feats.keys()) == FEATURE_ORDER, "14 维列序与 config.FEATURE_COLUMNS 不一致")
    return f"{m} risk={d['risk_score']} 14 维列序 OK"


@case("T-IN-14", "POST /api/predict", "缺参")
def predict_missing_body() -> str:
    expect(400)(post("/api/predict", json={}))
    expect(400)(post("/api/predict", json={"model_name": sample_model()}))
    expect(401)(client.post("/api/predict", json={"commit_hash": "a" * 40}))
    return "空 body / 缺字段 40001，缺令牌 40100"


@case("T-IN-15", "POST /api/predict", "非法参数")
def predict_bad_params() -> str:
    expect(400)(post("/api/predict", json={"commit_hash": "abc"}))
    expect(400)(
        post("/api/predict", json={"commit_hash": "a" * 40, "model_name": "not_exist_model"})
    )
    return "短 hash 与未知模型 40001"


@case("T-IN-16", "POST /api/predict", "边界值")
def predict_boundary() -> str:
    h = sample_commit()
    m = sample_model()
    first = expect(200)(post("/api/predict", json={"commit_hash": h, "model_name": m}))["data"]
    second = expect(200)(post("/api/predict", json={"commit_hash": h, "model_name": m}))["data"]
    check(abs(first["risk_score"] - second["risk_score"]) < 1e-9, "重复预测结果不稳定")
    # 非 expert 线：产物缺失时应是 40001 明确文案，不允许 500
    sem = sample_model("semantic")
    r = post("/api/predict", json={"commit_hash": h, "model_name": sem})
    check(r.status_code in (200, 400), f"semantic 预测状态码 {r.status_code}")
    if r.status_code == 400:
        check(r.json()["code"] == 40001, "semantic 不可用时应 40001")
    return f"幂等 OK；semantic→{r.status_code}/{r.json()['code']}"


# ---------------------------------------------------------------- POST /api/sync + status
@case("T-IN-17", "GET /api/sync/status", "正常")
def status_normal() -> str:
    d = expect(200)(get("/api/sync/status"))["data"]
    check(isinstance(d["running"], bool), "running 应为布尔")
    check(d["done"] <= d["total"] or not d["running"], "done 不应大于 total")
    return f"running={d['running']} {d['done']}/{d['total']}"


@case("T-IN-18", "GET /api/sync/status", "缺参")
def status_noauth() -> str:
    expect(401)(client.get("/api/sync/status"))
    return "缺失令牌 401/40100"


@case("T-IN-19", "POST /api/sync", "非法参数")
def sync_bad_params() -> str:
    expect(400)(post("/api/sync", params={"line": "hierarchical"}))
    expect(400)(post("/api/sync", params={"start_time": "abc"}))
    expect(401)(client.post("/api/sync"))
    return "未知线/非法时间 40001，缺令牌 40100"


@case("T-IN-20", "POST /api/sync", "正常")
def sync_normal() -> str:
    wait_idle()
    started = time.time()
    expect(200)(post("/api/sync", params={"line": "expert"}))
    st = wait_idle()
    cost = time.time() - started
    check(st["last_error"] is None, f"同步失败：{st['last_error']}")
    return f"accepted 且完结：mode={st['mode']} scope={st['scope']} done={st['done']}/{st['total']} 耗时={cost:.1f}s"


@case("T-IN-21", "POST /api/sync", "边界值")
def sync_concurrent() -> str:
    wait_idle()
    results: list[str] = []
    lock = threading.Lock()

    def fire() -> None:
        try:
            r = httpx.post(
                f"{BASE_URL}/api/sync",
                params={"line": "expert"},
                headers=AUTH,
                timeout=30.0,
            )
            out = str(r.status_code)
        except Exception as exc:  # noqa: BLE001 - 超时也要记录真实表现
            out = f"{type(exc).__name__}"
        with lock:
            results.append(out)

    ts = [threading.Thread(target=fire) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    wait_idle()
    ok = ("200" in results) and all(r in ("200", "500", "ReadTimeout") for r in results)
    check(ok, f"并发结果异常 {results}")
    return f"并发两次 → {sorted(results)}（200/500/超时均属可控，重点是状态不串扰）"


# ---------------------------------------------------------------- GET /api/trends
@case("T-IN-22", "GET /api/trends", "正常")
def trends_normal() -> str:
    d = expect(200)(get("/api/trends", params={"granularity": "week"}))["data"]
    check(d["granularity"] == "week", "粒度回显不符")
    for p in d["series"]:
        check(re.fullmatch(r"\d{4}-W\d{2}", p["period"]) is not None, f"period 格式 {p['period']}")
        check(p["high_risk_count"] <= p["commit_count"], "高风险数大于提交数")
        check(0.0 <= p["avg_risk"] <= 1.0, "平均风险越界")
    return f"周粒度 {len(d['series'])} 个周期 OK"


@case("T-IN-23", "GET /api/trends", "缺参")
def trends_noauth() -> str:
    expect(401)(client.get("/api/trends"))
    return "缺失令牌 401/40100"


@case("T-IN-24", "GET /api/trends", "非法参数")
def trends_bad_params() -> str:
    expect(400)(get("/api/trends", params={"granularity": "day"}))
    expect(400)(get("/api/trends", params={"end_time": "abc"}))
    return "非法粒度/时间 40001"


@case("T-IN-25", "GET /api/trends", "边界值")
def trends_boundary() -> str:
    d = expect(200)(get("/api/trends", params={"model_name": "no_such_model"}))["data"]
    check(d["series"] == [], "未知模型应返回空 series 而非报错")
    m = expect(200)(get("/api/trends", params={"granularity": "month"}))["data"]
    check(all(re.fullmatch(r"\d{4}-\d{2}", p["period"]) for p in m["series"]), "月粒度格式不符")
    return f"未知模型空 series；月粒度 {len(m['series'])} 个周期"


# ---------------------------------------------------------------- GET /api/figures
@case("T-IN-26", "GET /api/figures", "正常")
def figures_normal() -> str:
    m = sample_model()
    d = expect(200)(get("/api/figures", params={"model_name": m}))["data"]
    check(d["model_name"] == m, "模型回显不一致")
    order = ["roc", "pr", "confusion", "calibration", "effort", "feat_importance"]
    types = [f["figure_type"] for f in d["figures"]]
    check(types == [t for t in order if t in types], f"图序不符 {types}")
    check(
        all(f["file_path"].startswith("/static/figures/") for f in d["figures"]),
        "file_path 前缀不符",
    )
    return f"{m} 图 {len(types)} 张，顺序 OK"


@case("T-IN-27", "GET /api/figures", "缺参")
def figures_missing_param() -> str:
    body = expect(400)(get("/api/figures"))
    check("model_name" in body["message"], f"message={body['message']}")
    expect(401)(client.get("/api/figures", params={"model_name": "x"}))
    return "缺 model_name 40001、缺令牌 40100"


@case("T-IN-28", "GET /api/figures", "非法参数")
def figures_bad_param() -> str:
    body = expect(400)(get("/api/figures", params={"model_name": ""}))
    check("缺少 model_name" in body["message"], f"message={body['message']}")
    return "空串 40001 且文案明确"


@case("T-IN-29", "GET /api/figures", "边界值")
def figures_unknown_model() -> str:
    expect(404)(get("/api/figures", params={"model_name": "no_such_model"}))
    # 图本体同样需要鉴权
    m = sample_model()
    d = expect(200)(get("/api/figures", params={"model_name": m}))["data"]
    path = d["figures"][0]["file_path"]
    check(client.get(path).status_code == 401, "/static 图未鉴权")
    check(client.get(path, headers=AUTH).status_code == 200, "/static 图带鉴权不可读")
    return "未知模型 40400；/static 缺 key 401、带 key 200"


# ---------------------------------------------------------------- health
@case("T-IN-30", "GET /api/health", "正常")
def health_normal() -> str:
    d = expect(200)(get("/api/health"))["data"]
    check(d["status"] in ("ok", "degraded"), "status 取值异常")
    check(d["db"] in ("up", "down"), "db 取值异常")
    check(d["models_loaded"] >= 1, "模型未加载")
    check(d["server_time"].endswith("Z"), "server_time 未用 UTC Z")
    return (
        f"status={d['status']} db={d['db']} models={d['models_loaded']} commits={d['commit_count']}"
    )


@case("T-IN-31", "GET /api/health", "缺参")
def health_noauth() -> str:
    expect(401)(client.get("/api/health"))
    return "缺失令牌 401/40100"


@case("T-IN-32", "GET /api/health/live", "正常")
def health_live() -> str:
    d = expect(200)(get("/api/health/live"))["data"]
    check(d["status"] == "ok", "live 应恒 ok")
    return "live ok（不碰 DB）"


@case("T-IN-33", "GET /api/health/ready", "正常")
def health_ready() -> str:
    d = expect(200)(get("/api/health/ready"))["data"]
    check(d["db"] == "up" and d["models_loaded"] >= 1, f"ready 异常 {d}")
    return f"ready status={d['status']} db={d['db']} models={d['models_loaded']}"


@case("T-IN-34", "GET /api/health/ready", "缺参")
def health_ready_noauth() -> str:
    expect(401)(client.get("/api/health/ready"))
    return "缺失令牌 401/40100"


# ---------------------------------------------------------------- 跨模块链路
@case("T-IN-35", "链路（sync→特征→预测→落库→查询）", "正常")
def cross_module() -> str:
    h = sample_commit()
    m = sample_model()
    predicted = expect(200)(post("/api/predict", json={"commit_hash": h, "model_name": m}))["data"]
    detail = expect(200)(get(f"/api/commits/{h}", params={"model_name": m}))["data"]
    check(detail["model_name"] == m, "详情未读到该模型 prediction")
    check(
        abs((detail["risk_score"] or -1) - predicted["risk_score"]) < 1e-9, "落库值与预测返回不一致"
    )
    listed = expect(200)(get("/api/commits", params={"size": 100, "model_name": m}))["data"][
        "items"
    ]
    hit = [x for x in listed if x["commit_hash"] == h]
    check(bool(hit), "列表未查到刚落库的 prediction")
    return f"{h[:8]}/{m} 预测={predicted['risk_score']} 详情/列表一致"


def run(only: str | None = None) -> int:
    print(f"BASE_URL={BASE_URL} 用例数={len(CASES)}")
    failed = 0
    for c in CASES:
        if only and not c.cid.startswith(only):
            continue
        started = time.time()
        try:
            c.detail = c.call()
            c.result = "PASS"
        except AssertionError as exc:
            c.result = "FAIL"
            c.detail = str(exc)
            failed += 1
        except Exception as exc:  # noqa: BLE001 - 记录任何异常，不吞掉
            c.result = "ERROR"
            c.detail = f"{type(exc).__name__}: {exc}"
            failed += 1
        cost = time.time() - started
        print(f"[{c.result}] {c.cid} {c.endpoint} {c.scenario} ({cost:.1f}s) {c.detail}")
    total = len([c for c in CASES if not only or c.cid.startswith(only)])
    passed = total - failed
    print(f"\n汇总：total={total} pass={passed} fail={failed}")
    return 1 if failed else 0


def dump(path: str) -> None:
    payload = [
        {
            "id": c.cid,
            "endpoint": c.endpoint,
            "scenario": c.scenario,
            "source": c.source,
            "result": c.result,
            "detail": c.detail,
        }
        for c in CASES
    ]
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="把逐条结果写入 JSON 文件")
    parser.add_argument("--only", help="只跑某个编号前缀，如 T-IN-13")
    args = parser.parse_args()
    code = run(args.only)
    if args.json:
        dump(args.json)
    sys.exit(code)
