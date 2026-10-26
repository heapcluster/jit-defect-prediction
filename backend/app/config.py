"""后端配置：一律从 .env 读取，不入库、不写死在代码里（契约三 1.5 鉴权细则）。"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── 数据库连接：MySQL，分字段配置（口令单独一格、免转义）─────────────────────
# 为什么要分字段：`mysql+pymysql://user:pwd@host/db` 里口令只要含 `@ : / # ? %` 就必须做
# 百分号编码，手写几乎必错（写错的表现是「连不上」或「连上了别的库」）。分开填则原样写入，
# 由本模块负责编码 —— 用户只关心「账号是什么、口令是什么」。
DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "").strip() or "3306"
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "").strip() or "jit_demo"
DB_TEST_NAME = os.getenv("DB_TEST_NAME", "").strip() or "jit_test"
DB_CHARSET = os.getenv("DB_CHARSET", "").strip() or "utf8mb4"


def _with_database(url: str, database: str) -> str:
    """把显式 DSN 的库名换掉（保留口令与 query），pytest 切测试库用。"""
    from sqlalchemy.engine import make_url

    try:
        return make_url(url).set(database=database).render_as_string(hide_password=False)
    except Exception:  # noqa: BLE001 —— 非法 DSN 原样返回，把报错留给连接层
        return url


def build_database_url(database: str | None = None) -> str:
    """按分字段拼 MySQL DSN；显式 `DATABASE_URL` 优先（CI / 容器一行搞定）。缺字段返回空串。

    `database` 非空时覆盖库名：pytest 用它把 `DB_NAME` 换成 `DB_TEST_NAME`。
    """
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return _with_database(explicit, database) if database else explicit
    if not (DB_HOST and DB_USER):
        return ""
    credential = quote(DB_USER, safe="")
    if DB_PASSWORD:
        credential += f":{quote(DB_PASSWORD, safe='')}"
    return (
        f"mysql+pymysql://{credential}@{DB_HOST}:{DB_PORT}/"
        f"{database or DB_NAME}?charset={DB_CHARSET}"
    )


def test_database_url() -> str:
    """pytest 专用：`TEST_DATABASE_URL` > 当前配置把库名换成 `DB_TEST_NAME`。

    这样跑测试不必手工改 `.env`（改错就会把演示库的表当成测试表清空）。
    """
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    return build_database_url(DB_TEST_NAME)


DATABASE_URL = build_database_url()
API_TOKEN = os.getenv("API_TOKEN", "")
MODEL_DIR = Path(
    os.getenv("MODEL_DIR", "") or (REPO_ROOT / "data_model" / "pipelines" / "expert" / "models")
)
# 历史索引仓库：apache/camel 的 **blobless 克隆**（`git clone --filter=blob:none`，
# 只取提交+树、不含 blob，几十 MB），仅供 feature_source 跑 `git log --numstat` /
# `git cat-file` 计算 14 维特征。它**不是开发库、不进工作流、不持有预测状态**，
# 纯粹是「只读历史索引」。实时 PR 清单与提交来自 GitHub REST API（见 app/github.py）。
SOURCE_REPO = Path(os.environ["SOURCE_REPO"]) if os.getenv("SOURCE_REPO") else None
# change realtime-commit-sync：启动时后台预同步一次最新提交（默认关）。
# 开启后启动会 fetch SOURCE_REPO 并可能建临时 worktree；失败只记日志，不阻塞启动。
SYNC_ON_STARTUP = os.getenv("SYNC_ON_STARTUP", "") == "1"

# 实时 PR 数据来源（GitHub REST API，只读）。公开仓库可不带 GITHUB_TOKEN（60 req/h 限流），
# 带令牌升到 5000 req/h。拉取的是「apache/camel 当前 open 的 PR 及其提交」。
GITHUB_REPO = os.getenv("GITHUB_REPO", "apache/camel")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# 契约二 §3 的 14 项特征列顺序：模型输入向量按此顺序组装，不按 dict 插入顺序猜
FEATURE_COLUMNS = (
    "ns",
    "nd",
    "nf",
    "entropy",
    "la",
    "ld",
    "lt",
    "fix",
    "ndev",
    "age",
    "nuc",
    "exp",
    "rexp",
    "sexp",
)

HIGH_RISK_THRESHOLD = 0.5
