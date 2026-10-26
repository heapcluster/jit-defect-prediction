"""fused 线配置：双模态输入路径、拼接维度、分类器清单。"""

from __future__ import annotations

from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA_DIR = PKG.parent.parent / "data"  # data_model/data（共享上游）
MODELS_DIR = PKG / "models"
REPORTS_DIR = PKG / "reports"

# ── 双模态输入 ──────────────────────────────────────────────────────────
# 模态 A：Kamei 14（来自共享切分文件，天然带 14 列）
TRAIN_CSV = DATA_DIR / "split_szz_train.csv"
TEST_CSV = DATA_DIR / "split_szz_test.csv"
FEATURES_RAW_CSV = DATA_DIR / "commit_features_raw.csv"
# 模态 B：语义 768 维 —— 依赖 semantic 线的编码缓存（包间唯一数据衔接）
EMBEDDINGS_NPZ = PKG.parent / "semantic" / "data" / "semantic_embeddings.npz"

FEATURE_FIELDS = [  # 与 expert 同序（契约二第三节副本）
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
]
LABEL_COL = "is_bug_inducing"
EXPECTED_DIM = len(FEATURE_FIELDS) + 768  # 782

# ── 训练设置 ────────────────────────────────────────────────────────────
SEED = 42
DECISION_THRESHOLD = 0.5
# 训练口径 = 8 个（与 expert / semantic 共用，见 pipelines/config-and-output-spec.md §0.1）。
# model.py 的 MODEL_NAMES 仍是 12 个的注册表（多 nb/dt/knn/mlp，兼容旧产物），默认不训。
DEFAULT_MODELS = ["lr", "rf", "xgb", "lgbm", "et", "svm", "mlp_deep", "tabnet"]
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
