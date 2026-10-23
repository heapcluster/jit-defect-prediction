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
# 训练口径 = 8 个（2 类：经典 6 + 深度 2），四条线共用同一份清单，见
# pipelines/config-and-output-spec.md §0.1。model.py 的 MODEL_NAMES 是 12 个的
# 注册表（多 nb/dt/knn/mlp，历史产物兼容用），但**默认不训**：多训 4 个既拖慢
# 单线复现，又让四线对比的模型集合不一致。
DEFAULT_MODELS = ["lr", "rf", "xgb", "lgbm", "et", "svm", "mlp_deep", "tabnet"]

# ── Effort-aware 指标参数（与 06 同源，跨线可比）────────────────────────
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
EFFORT_FRACTIONS = (0.20, 0.50)      # Recall@20% / Recall@50%
# 预算感知排序的评审下限（LOC）：低于它的提交流程上不单独排期评审。
# 只影响 `budget` 这一对照口径，不改契约三的 `risk_score` 降序主口径。
MIN_REVIEW_LOC = 10

# ── SHAP 实测（契约三：95% 请求 < 500ms）───────────────────────────────
SHAP_ROWS = 100
LATENCY_BUDGET_MS = 500.0
