"""e2e 线配置：微调超参、路径、模态标识集中管理。"""

from __future__ import annotations
from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA_DIR = PKG.parent.parent / "data"          # data_model/data（共享上游）
MODELS_DIR = PKG / "models"
REPORTS_DIR = PKG / "reports"

# ── 骨干与微调 ──────────────────────────────────────────────────────────
TEXT_MODEL = "microsoft/codebert-base"
MAX_LEN = 512
EPOCHS = 4
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
GRAD_ACCUM_TARGET = 32              # 有效 batch = 32（batch_size×累积步）
EVAL_FRAC = 0.1                     # 共享切分缺失时的兜底（时间序尾部分留验）

# ── 路径 ────────────────────────────────────────────────────────────────
TEXT_CSV = PKG / "data" / "commit_text.csv"     # build_text_dataset.py 产出
TRAIN_CSV = DATA_DIR / "split_szz_train.csv"    # 共享切分（跨线可比）
TEST_CSV = DATA_DIR / "split_szz_test.csv"
FEATURES_RAW_CSV = DATA_DIR / "commit_features_raw.csv"
MODEL_DIR = PKG / "models" / "codebert_e2e_v1"
REPORT = REPORTS_DIR / "model_metrics.md"

# ── 标识 ────────────────────────────────────────────────────────────────
SEED = 42
DECISION_THRESHOLD = 0.5
MODEL_NAME = "codebert_e2e_v1"
FEATURE_VERSION = "codebert"        # 本线模态标识（区别于 expert 的 Kamei14 v1）
RANDOM_BASELINE_REPEATS = 200
RANDOM_BASELINE_SEED = 0
