"""expert 线配置：路径、特征列、模型清单、超参数集中管理。

改任何口径（特征列序 / 种子 / 阈值）只改这里；train.py 不写死数字。
特征列序与取值口径以 `docs/model/feature-columns.md`（契约二 v1.2）为唯一权威，
本文件只是其副本 —— 不一致时以契约为准。
"""

from __future__ import annotations

from pathlib import Path

# ── 路径 ────────────────────────────────────────────────────────────────
PKG = Path(__file__).resolve().parent
DATA_DIR = PKG.parent.parent / "data"          # data_model/data（01–05 共享上游）
MODELS_DIR = PKG / "models"
REPORTS_DIR = PKG / "reports"

TRAIN_CSV = DATA_DIR / "split_szz_train.csv"
TEST_CSV = DATA_DIR / "split_szz_test.csv"
FEATURES_RAW_CSV = DATA_DIR / "commit_features_raw.csv"   # 工作量取这里（未归一化）

# ── 特征与标签（契约二第三节 14 项，顺序即交付清单顺序）─────────────────
FEATURE_FIELDS = [
    "ns", "nd", "nf", "entropy",
    "la", "ld", "lt",
    "fix",
    "ndev", "age", "nuc",
    "exp", "rexp", "sexp",
]
LABEL_COL = "is_bug_inducing"        # 主标签 szz，不回退 szz_lite

# ── 训练设置 ────────────────────────────────────────────────────────────
SEED = 42                            # 随机种子显式固定，写进报告
DECISION_THRESHOLD = 0.5             # 契约三：服务端常量，非请求参数
DEFAULT_MODELS = ["lr", "rf", "xgb", "lgbm", "et", "svm",
                  "nb", "dt", "knn", "mlp", "mlp_deep", "tabnet"]

# ── Effort-aware 指标参数（与 06 同源，跨线可比）────────────────────────
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
EFFORT_FRACTIONS = (0.20, 0.50)      # Recall@20% / Recall@50%

# ── SHAP 实测（契约三：95% 请求 < 500ms）───────────────────────────────
SHAP_ROWS = 100
LATENCY_BUDGET_MS = 500.0
