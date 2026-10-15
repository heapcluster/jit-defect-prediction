"""融合 pipeline 包：Kamei 14 左连接 CodeBERT 768 = 782 维 + 8 个分类器。

状态：**⬜ 计划态** —— 训练脚本未落地，本包只定产出归属与路径常量。
方案与口径：`docs/model/pipelines/fused.md`（权威）。

产出归属（只归本线，四线隔离）：

- ``data/``     融合样本集 ``dataset_fused_v2.csv``（782 维）
- ``models/``   ``{model}_fused_v1.pkl`` + 本线交付清单（如产生）
- ``reports/``  ``model_metrics_fused.md``、``model_matrix_fused.md``、
                 ``feature_ablation_fused.md``；三线对比汇总
                 ``three_way_comparison.md`` 归 14_compare_settings.py 统一产出

共享上游产物（专家样本集作左表、语义向量作右表、切分下标）在 ``data_model/data/``，
四线共用，不按线分。
"""

from pathlib import Path

#: 线名，与产物命名后缀、`docs/model/pipelines/` 下的文档一一对应
LINE = "fused"

PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR / "data"
MODELS_DIR = PKG_DIR / "models"
REPORTS_DIR = PKG_DIR / "reports"

#: 共享上游产物目录（四线共用，不按线分）
SHARED_DATA_DIR = PKG_DIR.parent.parent / "data"

#: 融合特征版本（v2：专家 14 项 + 语义 768 项；升版本不覆盖旧版）
FEATURE_VERSION = "v2"

#: 融合维度 = 专家 14 + 语义 768
FEATURE_DIM = 782

__all__ = [
           "DATA_DIR",
           "FEATURE_DIM",
           "FEATURE_VERSION",
           "LINE",
           "MODELS_DIR",
           "PKG_DIR",
           "REPORTS_DIR",
           "SHARED_DATA_DIR",
]
