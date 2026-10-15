"""仅专家（基线）pipeline 包：Kamei 14 专家特征 + 8 个分类器。

产出归属（只归本线，四线隔离）：

- ``models/``    8 个 ``*_v1.pkl`` + ``feature_order.txt``（契约二第三节副本，
                 ``[models]`` 段只列交付模型 ``lr`` / ``rf`` / ``xgb``）
- ``reports/``   ``model_metrics.md``（⑥ 训练指标，两类指标齐全）、
                 ``model_matrix.md``（⑧ 覆盖矩阵 + 与基线逐项自证，差异须为 0）、
                 ``split_stats{tag}.md``（⑤ 切分统计，如在本包产出）、
                 ``calibration_threshold.md``（⑨）、``prediction_stats.md``（⑦）
- ``data/``      本线私有中间结果。当前为空：样本集 ``dataset_{szz,szz_lite}.csv``
                 与切分下标 ``split_{tag}_{train,test}.csv`` 是**四线共享**产物，
                 按约定放 ``data_model/data/``（见 ``pipelines/__init__.py`` 约定 2）。

入口：在 ``data_model/`` 目录下执行 ``python -m pipelines.expert.train``。
"""

from pathlib import Path

#: 线名，与产物命名后缀、`docs/model/pipelines/` 下的文档一一对应
LINE = "expert"

PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR / "data"
MODELS_DIR = PKG_DIR / "models"
REPORTS_DIR = PKG_DIR / "reports"

#: 共享上游产物目录（四线共用，不按线分）
SHARED_DATA_DIR = PKG_DIR.parent.parent / "data"

#: 本期交付模型（契约三 / model-coverage R6：其余 5 个仅评估对照，不进交付链）
DELIVERY_MODELS = "lr,rf,xgb"

#: 本线训练的 8 个模型（性能优先选型，见 docs/model/pipelines/expert-only.md §6.2）
MODELS = "lr,rf,xgb,lgbm,et,svm,mlp_deep,tabnet"

__all__ = [
    "DATA_DIR",
    "DELIVERY_MODELS",
    "LINE",
    "MODELS",
    "MODELS_DIR",
    "PKG_DIR",
    "REPORTS_DIR",
    "SHARED_DATA_DIR",
]
