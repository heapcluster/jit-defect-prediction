"""运行配置：只从环境变量读取，不写入仓库、不下发前端。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / "backend" / ".env")

DB_HOST = os.getenv("DB_HOST", "").strip()
DB_PORT = os.getenv("DB_PORT", "").strip() or "3306"
DB_USER = os.getenv("DB_USER", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "").strip() or "jit_demo"
DB_TEST_NAME = os.getenv("DB_TEST_NAME", "").strip() or "jit_test"
DB_CHARSET = os.getenv("DB_CHARSET", "").strip() or "utf8mb4"

TEMP_ROOT = REPO_ROOT / "temp"
REPOS_DIR = TEMP_ROOT / "repos"
UPLOADS_DIR = TEMP_ROOT / "uploads"
OUTPUTS_DIR = TEMP_ROOT / "outputs"
DATASETS_DIR = TEMP_ROOT / "datasets"
MODELS_DIR = TEMP_ROOT / "models"
EVALUATIONS_DIR = TEMP_ROOT / "evaluations"


def _with_database(url: str, database: str) -> str:
    from sqlalchemy.engine import make_url

    try:
        return make_url(url).set(database=database).render_as_string(hide_password=False)
    except Exception:  # noqa: BLE001
        return url


def build_database_url(database: str | None = None) -> str:
    explicit = os.getenv("DATABASE_URL", "").strip()
    if explicit:
        return _with_database(explicit, database) if database else explicit
    if not (DB_HOST and DB_USER):
        return ""
    credential = quote(DB_USER, safe="")
    if DB_PASSWORD:
        credential += f":{quote(DB_PASSWORD, safe='')}"
    db = database or DB_NAME
    return f"mysql+pymysql://{credential}@{DB_HOST}:{DB_PORT}/{db}?charset={DB_CHARSET}"


def test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL", "").strip()
    if explicit:
        return explicit
    return build_database_url(DB_TEST_NAME)


DATABASE_URL = build_database_url()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITEE_TOKEN = os.getenv("GITEE_TOKEN", "").strip()
MODEL_DIR = Path(os.getenv("MODEL_DIR", "") or MODELS_DIR)
SEMANTIC_EMBEDDINGS = os.getenv("SEMANTIC_EMBEDDINGS", "").strip()
SEMANTIC_TEXT_MODEL = os.getenv("SEMANTIC_TEXT_MODEL", "").strip() or "microsoft/codebert-base"
SEMANTIC_MAX_LEN = int(os.getenv("SEMANTIC_MAX_LEN", "512") or 512)

SESSION_COOKIE = "jit_session"
SESSION_TTL_DAYS = 7
MAX_DATA_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_MODEL_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_PAGE_STATE_BYTES = 64 * 1024
