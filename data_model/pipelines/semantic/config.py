"""semantic 线配置：冻结编码器、文本路径、编码超参、分类器清单。"""

from __future__ import annotations

from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA_DIR = PKG.parent.parent / "data"          # data_model/data（共享上游）
MODELS_DIR = PKG / "models"
REPORTS_DIR = PKG / "reports"

# ── 冻结编码器（只做前向，不训练）────────────────────────────────────────
TEXT_MODEL = "microsoft/codebert-base"
MAX_LEN = 512                       # CodeBERT 上限
POOLING = "mean"                    # 变更文本逐文件编码后按提交取均值 → 这里对最终文本取 mean-pool
ENCODE_BATCH = 32
ENCODE_DEVICE = "auto"              # auto=有 CUDA 用 CUDA；CPU 仅够 --limit 冒烟，全量请上 CUDA

# ── 文本与缓存 ──────────────────────────────────────────────────────────
TEXT_CSV = PKG / "data" / "commit_text.csv"               # 本线自建文本（与 e2e 格式一致）
EMBEDDINGS_NPZ = PKG / "data" / "semantic_embeddings.npz" # 编码缓存（fused 线也吃它）
MAX_CHARS = 4000                   # 单条提交文本上限（512 token ≈ 2000 字符，留余量）

# ── 切分（与 expert 同一份，跨线可比的前提）──────────────────────────────
TRAIN_CSV = DATA_DIR / "split_szz_train.csv"
TEST_CSV = DATA_DIR / "split_szz_test.csv"
FEATURES_RAW_CSV = DATA_DIR / "commit_features_raw.csv"
DATASET_CSV = DATA_DIR / "dataset_szz.csv"                # 自建文本时的标签来源

# ── 分类器与指标 ────────────────────────────────────────────────────────
SEED = 42
DECISION_THRESHOLD = 0.5
# 训练口径 = 8 个（与 expert / fused 共用，见 pipelines/config-and-output-spec.md §0.1）。
# model.py 的 MODEL_NAMES 仍是 12 个的注册表（多 nb/dt/knn/mlp，兼容旧产物），默认不训。
DEFAULT_MODELS = ["lr", "rf", "xgb", "lgbm", "et", "svm", "mlp_deep", "tabnet"]
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
