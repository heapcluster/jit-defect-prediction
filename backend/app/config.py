"""后端配置：一律从 .env 读取，不入库、不写死在代码里（契约三 1.5 鉴权细则）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv("DATABASE_URL", "")
API_TOKEN = os.getenv("API_TOKEN", "")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "") or (REPO_ROOT / "data_model" / "pipelines" / "expert" / "models"))
SOURCE_REPO = Path(os.environ["SOURCE_REPO"]) if os.getenv("SOURCE_REPO") else None
# change realtime-commit-sync：启动时后台预同步一次最新提交（默认关）。
# 开启后启动会 fetch SOURCE_REPO 并可能建临时 worktree；失败只记日志，不阻塞启动。
SYNC_ON_STARTUP = os.getenv("SYNC_ON_STARTUP", "") == "1"

# 契约二 §3 的 14 项特征列顺序：模型输入向量按此顺序组装，不按 dict 插入顺序猜
FEATURE_COLUMNS = (
    "ns", "nd", "nf", "entropy",
    "la", "ld", "lt",
    "fix",
    "ndev", "age", "nuc",
    "exp", "rexp", "sexp",
)

HIGH_RISK_THRESHOLD = 0.5
