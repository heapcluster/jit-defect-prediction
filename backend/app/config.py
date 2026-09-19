"""后端配置：一律从 .env 读取，不入库、不写死在代码里（契约三 1.4 鉴权细则）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv("DATABASE_URL", "")
API_TOKEN = os.getenv("API_TOKEN", "")
MODEL_DIR = Path(os.getenv("MODEL_DIR", "") or (REPO_ROOT / "data_model" / "models"))

# 契约二 §3 的 14 项特征列顺序：模型输入向量按此顺序组装，不按 dict 插入顺序猜
FEATURE_COLUMNS = (
    "ns", "nd", "nf", "entropy",
    "la", "ld", "lt",
    "fix",
    "ndev", "age", "nuc",
    "exp", "rexp", "sexp",
)

HIGH_RISK_THRESHOLD = 0.5
