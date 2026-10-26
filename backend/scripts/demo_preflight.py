"""录屏前自检脚本（Issue #138；裁定见 Issue #130 三，蒋励 2026-10-24）。

一条命令跑完六条判据，任一不满足退出码 1 并**打印实际值**；不静默通过、不拿跳过当绿
（口径同 `scripts/security_cases.py`）：依赖不可用、库为空、环境变量缺失、服务起不来
一律判 FAIL 并进入退出码，绝不「skip 后仍返回 0」。服务起不来同样判 FAIL。

六条判据（Issue #138 原文，逐条对应下面输出的 1~6 行）：
  1 `backend/.env` 的 `API_TOKEN` == `frontend/.env.local` 的 `VITE_API_KEY`（不等则前端全部 40100）
  2 库行数：`prediction` == 期望值（演示库口径 **83,943**）
  3 存在 `risk_score >= HIGH_RISK_THRESHOLD` 的行（演示库 **14,596** 条；联调库 `dev.db` 的
    seed 三行是 0.1/0.2/0.3，必然为 0 —— 这一项就是用来抓「拿错库上台」的）
  4 交付模型全部加载：服务启动日志的 `loaded models:` 含且仅含期望的八个（#153 起 expert
    全量上线：lr/rf/xgb/lgbm/et/svm/mlp_deep/tabnet），且无 `failed models:`
  5 四个接口 200 且 `code==0`：列表 / 详情 / 趋势 / 预测（契约三的四条路径，一条不多一条不少）
  6 同一 hash 连发两次 `POST /api/predict` → 两次都 200，`(commit_hash, model_name)` 仍恰 **1** 行，
    且 `prediction` 总行数前后不变（幂等 upsert，不新增行）

关于「只读自检」：判据 6 的两次 POST 是本脚本**唯一**的写操作。它刻意挑库内**已存在**
`(commit_hash, model_name)` 预测行来发 —— upsert 命中同一行、不插入新行 —— 并用
「总行数前后不变」把这一点钉死。其余五项全是只读 SELECT / GET。

两个**可选前置阶段**（Issue #142：把「建库→灌数→起服务→断言」并进同一条命令）：
  `--init-db`  阶段 0a 建库建表：等价于 `python -m app.db init`（ORM 路径，含 `_assert_indexes`
               自检）。**它只建表、不建数据库** —— MySQL 上库还不存在时会如实 FAIL 并指路
               `backend/scripts/schema_mysql.sql`（需 `CREATE DATABASE` 权限，见
               `docs/backend/mysql-setup.md` §2）。
  （数据入口已统一为实时预测：先用 `python infra/clone_camel_history.py` 建历史索引，
   再 `POST /api/sync-prs` 拉 Camel 最新 open PR 实时预测；本脚本不再做离线灌库。）
默认**不跑** `--init-db`：不加该开关时，本脚本是「只读 + 判据 6 一次幂等写」的自检。
任一阶段 FAIL → 六条判据一律记「前置不满足，未执行」并进 rc=1，不会拿后面的绿掩盖前面。

令牌与口令一律不回显：判据 1 只打印长度与掩码，`DATABASE_URL` 只打印方言/主机/库名，
仓库外的绝对路径（如 `MODEL_DIR` 指到的路径）在输出与证据文件里一律写作 `<仓库外路径>`
（`docs/repo/collaboration.md` §0 第 3 条）。

数据库口径（2026-10-25 裁定废除双库）：统一 **MySQL `jit_demo`**（联调 / 演示 / 验收同一套）。
本脚本只认 `DATABASE_URL`，不假设方言。

用法（cwd=`backend`，与 `scripts.seed_dev_data` 同一种起法）：
  python -m scripts.demo_preflight
  python -m scripts.demo_preflight --port 8055 --out scripts/evidence/preflight-2026-10-25.md
  DATABASE_URL=mysql+pymysql://<user>:<pwd>@127.0.0.1:3306/jit_demo python -m scripts.demo_preflight
  # 从零到断言一条命令（建库→起服务→六条判据；数据走实时同步，见下）：
  python -m scripts.demo_preflight --init-db --out scripts/evidence/preflight-2026-10-25.md
  # 数据入口改为实时预测：先 python infra/clone_camel_history.py 建历史索引，
  # 再 POST /api/sync-prs 拉 Camel 最新 open PR 现算预测（本脚本不再做离线灌库）
  # 对联调库跑（判据 2、3 会如实 FAIL，这正是它该有的行为，不要为了让它变绿而改期望值）：
  python -m scripts.demo_preflight --expect-predictions 3
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from app import config
from app.models import Commit, CommitFeature, CommitLabel, Prediction
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_BACKEND_ENV = BACKEND_DIR / ".env"
DEFAULT_FRONTEND_ENV = REPO_ROOT / "frontend" / ".env.local"
LOADED_RE = re.compile(r"loaded models:\s*(\[[^\]]*\])")
COUNT_MODELS = (Commit, CommitLabel, CommitFeature, Prediction)
TABLES = tuple(model.__tablename__ for model in COUNT_MODELS)
STAGE_NAMES = ("0a 建库建表",)
CRITERION_NAMES = (
    "1 令牌一致",
    "2 库行数",
    "3 存在高风险行",
    "4 交付模型全部加载",
    "5 四接口 200",
    "6 同 hash 两次预测只留一行",
)
DEFAULT_EXPECT_PREDICTIONS = 83943
DEFAULT_EXPECT_MODELS = "lr_v1,rf_v1,xgb_v1,lgbm_v1,et_v1,svm_v1,mlp_deep_v1,tabnet_v1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8055
DEFAULT_TIMEOUT = 120.0


def parse_dotenv(path: Path) -> dict[str, str]:
    """读 `KEY=VALUE` 形式的 .env；忽略空行与 `#` 注释，去掉成对引号与 `export ` 前缀。"""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def mask_secret(value: str) -> str:
    """令牌掩码：只留长度，不留任何一位原值。"""
    return f"***（{len(value)} 字符）" if value else "***（空）"


def mask_database_url(url: str) -> str:
    """`mysql+pymysql://user:pwd@host:3306/db` → `mysql+pymysql://user:***@host:3306/db`。"""
    if not url:
        return "（空）"
    return re.sub(r"(?<=://)([^:/@]+):([^@]+)@", r"\1:***@", url)


def display_path(path: str | Path | None) -> str:
    """仓库内路径显示相对仓库根；仓库外一律 `<仓库外路径>`，避免个人绝对路径进证据。"""
    if not path:
        return "（未设置）"
    p = Path(path)
    try:
        return str(p.resolve().relative_to(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        return "<仓库外路径>"


LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s；，、）)|]*"
    r"|(?<![A-Za-z0-9])/(?:Users|home|tmp|private/var|var/folders)/[^\s；，、）)|]*"
)


def local_replacements(*values: str | Path | None) -> dict[str, str]:
    """把**已知的**本机值整串登记为待替换项（库 URL、模型目录、两份 .env 路径）。

    正则只能兜底，真正可靠的是「我知道哪些值是本机路径」：SQLite 的 `DATABASE_URL`
    本身就是 `sqlite:///` + 绝对路径，驱动报错也可能带上它。
    """
    out: dict[str, str] = {}
    for value in values:
        text = str(value) if value else ""
        if text and (
            ":///" in text
            or re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", text)
            or text.startswith("/")
        ):
            out[text] = "<本机路径>"
    return out


def sanitize_for_evidence(text: str, replacements: dict[str, str] | None = None) -> str:
    """把落在文本里的本机绝对路径整段换成 `<本机路径>`。

    终端输出可以带真路径（方便当场排查），但 `--out` 写出的证据文件是要入库的，
    入库文件里不许出现个人绝对路径（`docs/repo/collaboration.md` §0 第 3 条）。
    先按已知值整串替换，再用正则兜底；`/api/...` 这类接口路径不在兜底名单里，不会被误伤。
    """
    for raw in replacements or {}:
        text = text.replace(raw, replacements[raw])
    return LOCAL_PATH_RE.sub("<本机路径>", text)


def count_rows(url: str) -> dict[str, int]:
    """四张表的行数。用 ORM 元数据而不是手写 SQL —— 表名 `commit` 是 SQL 保留字，
    裸写 `SELECT COUNT(*) FROM commit` 在 SQLite 上直接语法错误（本脚本的测试抓到的）。
    """
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return {
                model.__tablename__: int(
                    conn.execute(select(func.count()).select_from(model)).scalar_one()
                )
                for model in COUNT_MODELS
            }
    finally:
        engine.dispose()


def db_snapshot(url: str, threshold: float) -> tuple[dict[str, int], int]:
    """四张表行数 + 高风险行数，一次连接取完（判据 2、3 的实测值）。"""
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            counts = {
                model.__tablename__: int(
                    conn.execute(select(func.count()).select_from(model)).scalar_one()
                )
                for model in COUNT_MODELS
            }
            high = int(
                conn.execute(
                    select(func.count())
                    .select_from(Prediction)
                    .where(Prediction.risk_score >= threshold)
                ).scalar_one()
            )
        return counts, high
    finally:
        engine.dispose()


def count_pair(url: str, commit_hash: str, model_name: str) -> int:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return int(
                conn.execute(
                    select(func.count())
                    .select_from(Prediction)
                    .where(
                        Prediction.commit_hash == commit_hash, Prediction.model_name == model_name
                    )
                ).scalar_one()
            )
    finally:
        engine.dispose()


def init_database(db_url: str) -> tuple[bool, str]:
    """阶段 0a：建表（ORM 路径），等价于 `python -m app.db init`，含 `_assert_indexes` 自检。

    **只建表、不建数据库** —— MySQL 上库还不存在时 `create_all` 会抛 1049。这里如实 FAIL 并
    指路那条需要 `CREATE DATABASE` 权限的命令，不假装建好了。
    """
    from app import db as app_db

    if not db_url:
        return False, "DATABASE_URL 未设置（backend/.env 与 shell 环境变量都没有），无从建表"
    try:
        app_db.init_db()
    except (SQLAlchemyError, RuntimeError, OSError) as exc:
        detail = f"{type(exc).__name__}: {exc}"
        if "unknown database" in str(exc).lower() or "1049" in str(exc):
            detail += (
                " ｜ ORM 路径只建表不建库：先用有 CREATE DATABASE 权限的账号跑 "
                "`mysql -u root -p < backend/scripts/schema_mysql.sql`（cwd=仓库根；"
                "该脚本与权限/常见报错说明见 docs/backend/mysql-setup.md §2 与 §6，Issue #142）"
            )
        return False, detail
    try:
        counts = count_rows(db_url)
    except (SQLAlchemyError, OSError) as exc:
        return False, f"建表没报错，但随后读不到四表：{type(exc).__name__}: {exc}"
    return True, (
        "四表建好且索引自检通过（`CREATE TABLE IF NOT EXISTS`，连跑两次即验证幂等）："
        + " ".join(f"{name}={counts[name]}" for name in TABLES)
    )


def run_build_stages(args, db_url: str) -> tuple[list[tuple[str, bool, str]], list[str], list[str]]:
    """跑可选的阶段 0a/0b → (结果行, 信息行, 需要掩码的路径)。不加开关时返回三个空表。

    **0a FAIL 就不跑 0b**：库结构可能不对（例如四表在但索引自检失败），这时灌数会真的
    改掉演示库、最后却只能给 rc=1 —— 承诺是「任一前置阶段失败即停止」，不能先写再报错。
    """
    results: list[tuple[str, bool, str]] = []
    infos: list[str] = []
    secret_paths: list[str] = []
    init_ok = True
    if args.init_db:
        init_ok, detail = init_database(db_url)
        results.append((STAGE_NAMES[0], init_ok, detail))
    return results, infos, secret_paths


def pick_target(url: str, models: list[str]) -> tuple[str, str, float] | None:
    """挑一行**已存在**的 (commit_hash, model_name) 预测：优先默认清单里的模型。

    用它发判据 6 的两次 POST，upsert 只会更新这一行、不会插入新行。
    """
    columns = (Prediction.commit_hash, Prediction.model_name, Prediction.risk_score)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            for model in models:
                row = conn.execute(
                    select(*columns).where(Prediction.model_name == model).limit(1)
                ).first()
                if row is not None:
                    return row[0], row[1], float(row[2])
            row = conn.execute(select(*columns).limit(1)).first()
            return None if row is None else (row[0], row[1], float(row[2]))
    finally:
        engine.dispose()


def start_service(host: str, port: int, log_handle, env: dict[str, str]) -> subprocess.Popen:
    """起一个真 uvicorn 子进程：判据 4 要读的就是它的**启动日志**。

    日志句柄由调用方用 `with` 持有（子进程要在这个句柄上写一整段时间），本函数不负责开关。
    """
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )


def wait_ready(
    client: httpx.Client, base_url: str, proc: subprocess.Popen, timeout: float
) -> tuple[bool, str]:
    """轮询到服务能应答为止；进程先死就把日志尾巴当实际值报出来。"""
    deadline = time.time() + timeout
    last = "尚无响应"
    while time.time() < deadline:
        if proc.poll() is not None:
            return False, f"服务进程提前退出（退出码 {proc.returncode}）"
        try:
            resp = client.get(f"{base_url}/api/commits")
            return True, f"HTTP {resp.status_code}（无令牌，401 即为已就绪）"
        except httpx.HTTPError as exc:
            last = f"{type(exc).__name__}"
            time.sleep(0.5)
    return False, f"{timeout:.0f}s 内未就绪，最后一次异常 {last}"


def parse_startup_log(log_text: str) -> tuple[list[str] | None, bool, str]:
    """→ (加载到的模型名列表或 None, 是否有 failed models 行, 原始日志行)。"""
    match = LOADED_RE.search(log_text)
    loaded = ast.literal_eval(match.group(1)) if match else None
    failed = "failed models:" in log_text
    marks = ("loaded models:", "failed models:", "model dir not found")
    raw = " ｜ ".join(
        line.strip() for line in log_text.splitlines() if any(m in line for m in marks)
    )
    return loaded, failed, raw or "（启动日志里没有模型加载行）"


def log_tail(log_path: Path, limit: int = 400) -> str:
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError as exc:
        return f"（日志读不出来：{exc}）"


def run_service_checks(
    args,
    base_url: str,
    db_url: str,
    token: str,
    model_dir,
    target,
    expect_models: list[str],
    results: list[tuple[str, bool, str]],
    infos: list[str],
) -> None:
    """判据 4/5/6：自己起一个 uvicorn 子进程（判据 4 要读的就是它的启动日志），跑完立刻收掉。

    结果直接 append 进 `results`；任何一步跑不下去都写成 FAIL 行返回，**不静默跳过**。
    """
    commit_hash, model_name, stored_score = target
    log_path = Path(tempfile.mkdtemp(prefix="demo-preflight-")) / f"uvicorn-{args.port}.log"
    env = dict(
        os.environ, PYTHONUTF8="1", DATABASE_URL=db_url, API_TOKEN=token, MODEL_DIR=str(model_dir)
    )
    env.pop("PYTHONPATH", None)
    print(f"信息 服务日志：{log_path}（临时目录，不入库；证据文件里这一项一律掩码）")
    with log_path.open("wb") as log_handle:
        proc = start_service(args.host, args.port, log_handle, env)
        try:
            with httpx.Client(timeout=30) as client:
                ready, ready_detail = wait_ready(client, base_url, proc, args.timeout)
                infos.append(f"服务就绪探测：{ready_detail}")
                log_text = (
                    log_path.read_text(encoding="utf-8", errors="replace")
                    if log_path.is_file()
                    else ""
                )
                if not ready:
                    results.append(
                        (
                            "4 交付模型全部加载",
                            False,
                            f"服务没起来：{ready_detail}；日志尾巴：{log_tail(log_path)}",
                        )
                    )
                    for name in ("5 四接口 200", "6 同 hash 两次预测只留一行"):
                        results.append((name, False, f"服务未就绪，未执行：{ready_detail}"))
                    return

                loaded, has_failed, raw = parse_startup_log(log_text)
                ok4 = (
                    loaded is not None
                    and sorted(loaded) == sorted(expect_models)
                    and not has_failed
                )
                results.append(
                    (
                        "4 交付模型全部加载",
                        ok4,
                        (
                            f"启动日志：{raw}；期望清单 {sorted(expect_models)}、实际 {sorted(loaded or [])}"
                            + ("；且出现 failed models: 行" if has_failed else "")
                        ),
                    )
                )

                headers = {"X-API-Key": token}
                calls: list[tuple[str, int, object]] = []
                try:
                    r_list = client.get(
                        f"{base_url}/api/commits", params={"size": 1}, headers=headers
                    )
                    calls.append(
                        ("GET /api/commits", r_list.status_code, r_list.json().get("code"))
                    )
                    r_detail = client.get(f"{base_url}/api/commits/{commit_hash}", headers=headers)
                    calls.append(
                        (
                            "GET /api/commits/{commit_hash}",
                            r_detail.status_code,
                            r_detail.json().get("code"),
                        )
                    )
                    r_trends = client.get(
                        f"{base_url}/api/trends", params={"granularity": "week"}, headers=headers
                    )
                    calls.append(
                        ("GET /api/trends", r_trends.status_code, r_trends.json().get("code"))
                    )
                    pair_before = count_pair(db_url, commit_hash, model_name)
                    total_before = count_rows(db_url)["prediction"]
                    first_predict = client.post(
                        f"{base_url}/api/predict",
                        json={"commit_hash": commit_hash, "model_name": model_name},
                        headers=headers,
                    )
                    calls.append(
                        (
                            "POST /api/predict",
                            first_predict.status_code,
                            first_predict.json().get("code"),
                        )
                    )
                except (httpx.HTTPError, SQLAlchemyError, ValueError) as exc:
                    results.append(
                        ("5 四接口 200", False, f"请求异常：{type(exc).__name__}: {exc}")
                    )
                    results.append(
                        ("6 同 hash 两次预测只留一行", False, f"判据 5 的请求没跑完：{exc}")
                    )
                    return

                ok5 = len(calls) == 4 and all(s == 200 and c == 0 for _, s, c in calls)
                results.append(
                    (
                        "5 四接口 200",
                        ok5,
                        (
                            "；".join(f"{n} → HTTP {s} code={c}" for n, s, c in calls)
                            + ("" if ok5 else "（契约三只有这四条路径，少一条或多一条都不算过）")
                        ),
                    )
                )

                try:
                    r_p2 = client.post(
                        f"{base_url}/api/predict",
                        json={"commit_hash": commit_hash, "model_name": model_name},
                        headers=headers,
                    )
                    second = (
                        r_p2.status_code,
                        r_p2.json().get("code"),
                        (r_p2.json().get("data") or {}).get("risk_score"),
                    )
                    pair_after = count_pair(db_url, commit_hash, model_name)
                    total_after = count_rows(db_url)["prediction"]
                except (httpx.HTTPError, SQLAlchemyError, ValueError) as exc:
                    results.append(
                        (
                            "6 同 hash 两次预测只留一行",
                            False,
                            f"第二次 POST 异常：{type(exc).__name__}: {exc}",
                        )
                    )
                    return

                first_score = (first_predict.json().get("data") or {}).get("risk_score")
                ok6 = (
                    first_predict.status_code == 200
                    and second[0] == 200
                    and pair_before == 1
                    and pair_after == 1
                    and total_before == total_after
                )
                results.append(
                    (
                        "6 同 hash 两次预测只留一行",
                        ok6,
                        (
                            f"两次 POST → HTTP {first_predict.status_code}/{second[0]}；"
                            f"(hash, {model_name}) 行数 {pair_before} → {pair_after}（应恒为 1）；"
                            f"prediction 总行数 {total_before} → {total_after}（应不变，证明 upsert 没插新行）"
                        ),
                    )
                )
                infos.append(
                    f"两次返回的 risk_score：{first_score} / {second[2]}；库内原值 {stored_score}"
                    "（信息行，不计入判定：判据 6 按 Issue #138 只钉「只留一行」）"
                )
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="录屏前六条判据自检（Issue #138）")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="本脚本自己起服务用的端口")
    parser.add_argument("--backend-env", default=str(DEFAULT_BACKEND_ENV))
    parser.add_argument("--frontend-env", default=str(DEFAULT_FRONTEND_ENV))
    parser.add_argument(
        "--expect-predictions",
        type=int,
        default=DEFAULT_EXPECT_PREDICTIONS,
        help="判据 2 的期望 prediction 行数；演示库 83943，联调库 3",
    )
    parser.add_argument(
        "--expect-models",
        default=DEFAULT_EXPECT_MODELS,
        help="判据 4 的期望加载清单，逗号分隔；默认 = 交付清单八个（expert 全量，#153）",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="等服务就绪的秒数")
    parser.add_argument("--out", default="", help="可选：把结果写成证据 markdown")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="可选前置阶段 0a：先建表（等价 python -m app.db init，含索引自检）",
    )
    args = parser.parse_args()

    backend_env = Path(args.backend_env)
    frontend_env = Path(args.frontend_env)
    expect_models = [m.strip() for m in args.expect_models.split(",") if m.strip()]
    base_url = f"http://{args.host}:{args.port}"
    threshold = config.HIGH_RISK_THRESHOLD
    results: list[tuple[str, bool, str]] = []
    infos: list[str] = []

    db_url = config.DATABASE_URL
    model_dir = config.MODEL_DIR
    stage_results, stage_infos, stage_paths = run_build_stages(args, db_url)
    infos.extend(stage_infos)

    # ── 判据 1：两份 .env 的令牌必须逐字相等 ──────────────────────────
    backend_values = parse_dotenv(backend_env) if backend_env.is_file() else None
    frontend_values = parse_dotenv(frontend_env) if frontend_env.is_file() else None
    if backend_values is None or frontend_values is None:
        missing = display_path(backend_env if backend_values is None else frontend_env)
        results.append(
            (
                "1 令牌一致",
                False,
                (
                    f"配置文件不存在：{missing} —— 缺 backend/.env 则服务无令牌可校验，"
                    "缺 frontend/.env.local 则前端发空令牌、四接口全部 40100"
                ),
            )
        )
        backend_token = (backend_values or {}).get("API_TOKEN", "")
        frontend_token = (frontend_values or {}).get("VITE_API_KEY", "")
    else:
        backend_token = backend_values.get("API_TOKEN", "")
        frontend_token = frontend_values.get("VITE_API_KEY", "")
        ok = bool(backend_token) and backend_token == frontend_token
        detail = (
            f"backend/.env API_TOKEN={mask_secret(backend_token)} vs "
            f"frontend/.env.local VITE_API_KEY={mask_secret(frontend_token)} → "
            + ("逐字相等" if ok else "不相等（前端会全部 40100）")
        )
        if not backend_token:
            detail = "backend/.env 里没有 API_TOKEN（服务会因缺令牌拒绝所有请求）"
        results.append(("1 令牌一致", ok, detail))

    # 服务实际用的令牌可能来自 shell 环境变量（load_dotenv 不覆盖已有环境变量），如实报出来
    env_token = os.environ.get("API_TOKEN", "")
    if env_token and backend_token and env_token != backend_token:
        infos.append(
            f"shell 环境变量 API_TOKEN={mask_secret(env_token)} 与 backend/.env 不同，"
            "服务用的是环境变量那一份（load_dotenv 不覆盖已有环境变量）"
        )

    token = env_token or backend_token
    replacements = local_replacements(db_url, model_dir, backend_env, frontend_env, *stage_paths)
    infos.append(f"库：{mask_database_url(db_url)}")
    infos.append(f"模型目录：{display_path(model_dir)}")
    infos.append(
        f"高风险阈值：{threshold}（取自 app/config.py::HIGH_RISK_THRESHOLD，不在本脚本另立）"
    )
    infos.append(f"服务：{base_url}（本脚本自己起，判据 4 要读它的启动日志）")

    # 阶段 0a/0b 任一 FAIL：判据 2~6 一律记「未执行」并进 rc=1，不拿后面的绿掩盖前面的红。
    # 判据 1（两份 .env 的令牌）不依赖库，已经真跑过，就报它的实际结果，不改成「未执行」。
    if stage_results and not all(ok for _, ok, _ in stage_results):
        failed = "、".join(name for name, ok, _ in stage_results if not ok)
        for name in CRITERION_NAMES[1:]:
            results.append(
                (name, False, f"前置阶段未通过（{failed}），未执行；实际值见上面该阶段那一行的输出")
            )
        return finish(stage_results + results, infos, args, base_url, replacements)

    # ── 判据 2、3：库行数与高风险行 ──────────────────────────────────
    snapshot: tuple[dict[str, int], int] | None = None
    db_error = ""
    if not db_url:
        db_error = "DATABASE_URL 未设置（backend/.env 与 shell 环境变量都没有）"
    else:
        try:
            snapshot = db_snapshot(db_url, threshold)
        except (SQLAlchemyError, OSError) as exc:
            db_error = f"数据库不可用：{type(exc).__name__}: {exc}"
    if snapshot is None:
        results.append(("2 库行数", False, db_error))
        results.append(("3 存在高风险行", False, db_error))
    else:
        counts, high = snapshot
        got = counts["prediction"]
        results.append(
            (
                "2 库行数",
                got == args.expect_predictions,
                f"prediction={got}（期望 {args.expect_predictions}）；其余三表只报数不判定："
                + " ".join(f"{name}={counts[name]}" for name in TABLES if name != "prediction"),
            )
        )
        hint = (
            "；若这里是联调库 dev.db（seed 三行 0.1/0.2/0.3），说明**拿错库上台**了 —— "
            "演示与 T-ST-01~05 一律用演示库（Issue #130 更正裁定：MySQL jit_demo）"
            if high == 0
            else ""
        )
        results.append(
            (
                "3 存在高风险行",
                high > 0,
                f"risk_score >= {threshold} 的行 = {high}（演示库口径应为 14596）" + hint,
            )
        )

    # ── 判据 4、5、6：要起服务，前置不齐就三条一起 FAIL（不 skip） ────
    target = None
    if snapshot is not None:
        try:
            target = pick_target(db_url, expect_models)
        except SQLAlchemyError as exc:
            db_error = f"取不到可用的预测行：{type(exc).__name__}: {exc}"
    if not token:
        blocker = "没有可用令牌（判据 1 已 FAIL），不起服务"
    elif snapshot is None or db_error:
        blocker = db_error or "库不可用"
    elif target is None:
        blocker = (
            "库内没有任何 prediction 行，挑不出 (commit_hash, model_name) 来发判据 5/6 的 POST"
        )
    else:
        blocker = ""

    if blocker:
        for name in ("4 交付模型全部加载", "5 四接口 200", "6 同 hash 两次预测只留一行"):
            results.append((name, False, f"前置不满足，未执行：{blocker}"))
        return finish(stage_results + results, infos, args, base_url, replacements)

    commit_hash, model_name, stored_score = target
    infos.append(
        f"判据 5/6 用的样本：commit_hash={commit_hash}、model_name={model_name}、"
        f"库内 risk_score={stored_score}"
    )

    run_service_checks(
        args, base_url, db_url, token, model_dir, target, expect_models, results, infos
    )
    return finish(stage_results + results, infos, args, base_url, replacements)


def finish(
    results: list[tuple[str, bool, str]],
    infos: list[str],
    args,
    base_url: str,
    replacements: dict[str, str] | None = None,
) -> int:
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name} :: {detail}")
    for line in infos:
        print(f"信息 {line}")
    passed = sum(1 for _, ok, _ in results if ok)
    all_ok = passed == len(results)
    print(f"汇总：{passed}/{len(results)} 通过" + ("" if all_ok else " —— 存在 FAIL，别上台"))
    if args.out:
        write_evidence(Path(args.out), results, infos, args, base_url, all_ok, replacements)
    return 0 if all_ok else 1


# 会影响判定结果的参数与其默认值。证据里的命令必须记全**非默认**项，否则「照命令复跑」
# 会得出与本次不同的结论（sober-hub 在 #151 复审指出：只记阶段开关与 CSV 不够）。
VERDICT_FLAGS = (
    ("port", DEFAULT_PORT),
    ("host", DEFAULT_HOST),
    ("expect_predictions", DEFAULT_EXPECT_PREDICTIONS),
    ("expect_models", DEFAULT_EXPECT_MODELS),
    ("timeout", DEFAULT_TIMEOUT),
    ("backend_env", str(DEFAULT_BACKEND_ENV)),
    ("frontend_env", str(DEFAULT_FRONTEND_ENV)),
)


def evidence_command(args) -> str:
    """拼出能复现本次判定的命令：阶段开关 + 所有非默认的判据参数。"""
    parts = ["python -m scripts.demo_preflight"]
    if args.init_db:
        parts.append("--init-db")
    for name, default in VERDICT_FLAGS:
        value = getattr(args, name)
        if str(value) != str(default):
            parts.append(f"--{name.replace('_', '-')} {value}")
    return " ".join(parts)


def write_evidence(
    out: Path,
    results,
    infos,
    args,
    base_url: str,
    all_ok: bool,
    replacements: dict[str, str] | None = None,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    command = sanitize_for_evidence(evidence_command(args), replacements)
    lines = [
        f"# 录屏前自检 {datetime.now(UTC).astimezone().date().isoformat()}",
        "",
        f"- 命令：`{command}`（cwd=`backend`；令牌与库口令一律掩码）",
        "- 判据来源：Issue #138（裁定见 Issue #130 三）；演示库口径见 Issue #130 更正裁定（MySQL `jit_demo`）"
        + ("；前置阶段（建库）按 Issue #142 并入同一条命令" if args.init_db else ""),
    ]
    if "<本机路径>" in command or "<仓库外路径>" in command:
        lines.append(
            "- ⚠️ 上面命令里的 `<本机路径>` / `<仓库外路径>` 是**掩码占位**（§0 硬规矩 1：个人绝对路径不入库）；"
            "在本机复跑时要替换成自己的实际路径，其余参数照抄即可复现同一组判定"
        )
    lines += [
        "",
        "| 判据 / 阶段 | 结果 | 实际值 |",
        "|---|---|---|",
    ]
    lines += [
        f"| {name} | {'PASS' if ok else 'FAIL'} | {sanitize_for_evidence(detail, replacements)} |"
        for name, ok, detail in results
    ]
    passed = sum(1 for _, ok, _ in results if ok)
    if all_ok:
        verdict = f"**汇总：{passed}/{len(results)} 通过**"
    else:
        verdict = f"**汇总：{passed}/{len(results)}，存在 FAIL —— 别上台，也不得作为证据提交**"
    lines += ["", "**信息行（不计入判定）**", ""]
    lines += [f"- {sanitize_for_evidence(line, replacements)}" for line in infos]
    lines += ["", verdict, ""]
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"证据写入 {display_path(out)}")


if __name__ == "__main__":
    raise SystemExit(main())
