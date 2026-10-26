"""后端配置：一律从 .env 读取，不入库、不写死在代码里（契约三 1.5 鉴权细则）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

DATABASE_URL = os.getenv("DATABASE_URL", "")
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
