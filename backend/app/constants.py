"""全系统固定口径：列契约、算法清单、枚举。与 docs/约束/enums.md、docs/数据库/algorithm.md 对齐。"""

from __future__ import annotations

# ── 字段契约（docs/功能点/02-数据收集.md 第 4 节）────────────────────────────
META_COLUMNS = [
    "project",
    "commit_id",
    "commit_time",
    "author_name",
    "author_email",
    "commit_message",
]
EXPERT_FEATURES = [
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
SEMANTIC_FEATURES = [f"f_{i:04d}" for i in range(1, 769)]
EXPERT_COLUMNS = META_COLUMNS + EXPERT_FEATURES + ["bug"]
SEMANTIC_COLUMNS = META_COLUMNS + SEMANTIC_FEATURES + ["bug"]

FEATURE_VERSION = {"expert": "kamei14-v1", "semantic": "codebert768-v1"}
LINE_OF_VERSION = {v: k for k, v in FEATURE_VERSION.items()}

# ── 预测结果七列（接口/页面）────────────────────────────────────────────────
PREDICTION_VIEW_COLUMNS = [
    "commit_hash",
    "commit_message",
    "author_name",
    "commit_time",
    "bug",
    "risk_score",
    "predicted_label",
]
PREDICTION_EXTRA_COLUMNS = ["risk_score", "predicted_label", "threshold"]

# ── 算法清单（docs/数据库/algorithm.md）──────────────────────────────────────
ALGORITHMS: list[dict] = [
    {"algo": "lr", "family": "linear", "name": "逻辑回归",
     "defaults": {"C": 1.0, "max_iter": 1000}, "types": {"C": "number", "max_iter": "int"}},
    {"algo": "dt", "family": "tree", "name": "决策树",
     "defaults": {"max_depth": 10, "min_samples_split": 2},
     "types": {"max_depth": "int", "min_samples_split": "int"}},
    {"algo": "rf", "family": "ensemble", "name": "随机森林",
     "defaults": {"n_estimators": 200, "max_depth": 20},
     "types": {"n_estimators": "int", "max_depth": "int"}},
    {"algo": "et", "family": "ensemble", "name": "极端随机树",
     "defaults": {"n_estimators": 200, "max_depth": 20},
     "types": {"n_estimators": "int", "max_depth": "int"}},
    {"algo": "ada", "family": "boosting", "name": "AdaBoost",
     "defaults": {"n_estimators": 100, "learning_rate": 0.1},
     "types": {"n_estimators": "int", "learning_rate": "number"}},
    {"algo": "gbdt", "family": "boosting", "name": "梯度提升树",
     "defaults": {"n_estimators": 200, "learning_rate": 0.1, "max_depth": 3},
     "types": {"n_estimators": "int", "learning_rate": "number", "max_depth": "int"}},
    {"algo": "xgb", "family": "boosting", "name": "XGBoost",
     "defaults": {"n_estimators": 300, "learning_rate": 0.1, "max_depth": 6},
     "types": {"n_estimators": "int", "learning_rate": "number", "max_depth": "int"}},
    {"algo": "lgbm", "family": "boosting", "name": "LightGBM",
     "defaults": {"n_estimators": 300, "learning_rate": 0.1, "num_leaves": 31},
     "types": {"n_estimators": "int", "learning_rate": "number", "num_leaves": "int"}},
    {"algo": "svm", "family": "svm", "name": "支持向量机",
     "defaults": {"C": 1.0, "kernel": "rbf", "gamma": "scale"},
     "types": {"C": "number", "kernel": "choice:linear,rbf,poly", "gamma": "text"}},
    {"algo": "knn", "family": "neighbor", "name": "K 近邻",
     "defaults": {"n_neighbors": 5, "weights": "uniform"},
     "types": {"n_neighbors": "int", "weights": "choice:uniform,distance"}},
    {"algo": "mlp", "family": "neural", "name": "多层感知机",
     "defaults": {"hidden_layers": [128, 64], "alpha": 0.0001, "max_iter": 1000},
     "types": {"hidden_layers": "int_list", "alpha": "number", "max_iter": "int"}},
    {"algo": "dnn", "family": "neural", "name": "深度神经网络",
     "defaults": {"hidden_layers": [256, 128], "dropout": 0.2, "epochs": 50,
                  "batch_size": 256, "learning_rate": 0.001},
     "types": {"hidden_layers": "int_list", "dropout": "number", "epochs": "int",
               "batch_size": "int", "learning_rate": "number"}},
    {"algo": "tabnet", "family": "neural", "name": "TabNet",
     "defaults": {"n_d": 16, "n_a": 16, "epochs": 50, "batch_size": 256},
     "types": {"n_d": "int", "n_a": "int", "epochs": "int", "batch_size": "int"}},
]
ALGO_BY_NAME = {a["algo"]: a for a in ALGORITHMS}
PYTORCH_ALGOS = {"dnn", "tabnet"}

LINES = ("expert", "semantic")
SOURCE_TYPES = ("git_repo", "upload", "clean", "split", "prediction")
CLEAN_ELIGIBLE_SOURCES = ("git_repo", "upload", "clean")
TRAIN_ELIGIBLE_SOURCES = ("git_repo", "upload", "clean")
PREDICT_ELIGIBLE_SOURCES = ("git_repo", "upload", "clean", "split")

CLEAN_OPS = ("dedup", "missing", "outlier", "label", "balance")
CLEAN_DEFAULTS = {
    "dedup": {"key": "full"},
    "missing": {"mode": "drop", "columns": []},
    "outlier": {"method": "iqr_clip", "factor": 1.5, "columns": []},
    "label": {},
    "balance": {"method": "under", "ratio": 1.0},
}
EVAL_METRICS = ("accuracy", "precision", "recall", "f1", "auc", "ap", "mcc")
FIGURE_TYPES = ("roc", "pr", "confusion", "bar")
TECHNIQUES = ("shap", "lime", "permutation")

PAGES = ("collect", "clean", "train", "predict", "evaluate", "storage")
JOB_KINDS = ("collect", "clean", "train", "predict", "evaluate")
JOB_STATUSES = ("queued", "running", "success", "failed", "cancelled")
