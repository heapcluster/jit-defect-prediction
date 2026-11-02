"""测试集评估配置：25 个模型清单、各线输入路径、图表输出目录。

数据来源（均已校验覆盖测试集）：
  · data/split_szz_test.csv         测试集样本（14 维 + szz 标签），时间序后 30%
  · data/semantic_embeddings.npz    冻结 CodeBERT 768 维编码（83,943 条 × 768）
  · pipelines/e2e/data/prediction_result.csv  e2e 全量预测（含检验集）
  · data/commit_features_raw.csv    la / ld 原值（effort-aware 曲线的工作量）
  · data/commits.csv                完整提交信息（commit 表）
  · data/commit_labels_szz.csv      szz 真标签（commit_label 表）
"""

from __future__ import annotations

from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA_MODEL = PKG.parent
DATA_DIR = DATA_MODEL / "data"
PIPELINES = DATA_MODEL / "pipelines"
REPO_ROOT = DATA_MODEL.parent

# ── 输入路径 ────────────────────────────────────────────────────────────────
TEST_CSV = DATA_DIR / "split_szz_test.csv"
COMMITS_CSV = DATA_DIR / "commits.csv"
LABELS_SZZ_CSV = DATA_DIR / "commit_labels_szz.csv"
FEATURES_RAW_CSV = DATA_DIR / "commit_features_raw.csv"
EMBEDDINGS_NPZ = DATA_DIR / "semantic_embeddings.npz"
E2E_PRED_CSV = PIPELINES / "e2e" / "data" / "prediction_result.csv"

# ── 契约二第三节：Kamei 14 维（顺序即模型输入顺序）─────────────────────────
FEATURE_FIELDS = [
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
DECISION_THRESHOLD = 0.5

# ── 模型清单：8*3 + 1 = 25 ──────────────────────────────────────────────────
ALGOS = ["lr", "rf", "xgb", "lgbm", "et", "svm", "mlp_deep", "tabnet"]
LINES = ("expert", "semantic", "fused")
E2E_MODEL_NAME = "codebert_e2e_v1"

_MODEL_SUFFIX = {"expert": "_v1", "semantic": "_semantic_v1", "fused": "_fused_v1"}
FEATURE_VERSION = {"expert": "v1", "semantic": "v1", "fused": "v1", "e2e": "codebert"}

# (line, algo)，e2e 的 algo 记 codebert_e2e
MODEL_LIST: list[tuple[str, str]] = [(line, algo) for line in LINES for algo in ALGOS]
MODEL_LIST.append(("e2e", "codebert_e2e"))


def model_name(line: str, algo: str) -> str:
    if line == "e2e":
        return E2E_MODEL_NAME
    return f"{algo}{_MODEL_SUFFIX[line]}"


def models_dir(line: str) -> Path:
    return PIPELINES / line / "models"


def figs_dir(line: str) -> Path:
    """数据线自产目录：pipelines/{line}/reports/figs_by_model/{model}/。"""
    return PIPELINES / line / "reports" / "figs_by_model"


# 后端静态托管目录：model_figure.file_path 指向 /static/figures/{line}/{model}/{type}.png
BACKEND_STATIC_FIGURES = REPO_ROOT / "backend" / "static" / "figures"

# 交付物输出目录（生成的 SQL 较大，放这里，不入库）
OUT_DIR = PKG / "out"
SCHEMA_SQL = REPO_ROOT / "infra" / "schema.sql"
DATA_INIT_SQL = OUT_DIR / "data_init.sql"
