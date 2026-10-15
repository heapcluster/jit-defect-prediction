"""仅语义 pipeline 包：冻结 CodeBERT 768 维 + 8 个分类器。

状态：**⬜ 计划态** —— 训练脚本未落地，本包只定产出归属与路径常量。
方案与口径：`docs/model/pipelines/semantic-only.md`（权威）。

产出归属（只归本线，四线隔离）：

- ``data/``     变更文本 ``semantic_text_v2.csv``、语义向量
                 ``semantic_codebert_v2.csv``、样本集 ``dataset_semantic_v2.csv``
- ``models/``   ``{model}_semantic_v1.pkl`` + 本线交付清单（如产生）
- ``reports/``  ``model_metrics_semantic.md``、``model_matrix_semantic.md``、
                 ``feature_ablation_semantic.md``；三线对比汇总
                 ``three_way_comparison.md`` 归 14_compare_settings.py 统一产出

共享上游产物（Camel 仓库副本、提交清单、标签、切分下标）在 ``data_model/data/``，
四线共用，不按线分。
"""

from pathlib import Path

#: 线名，与产物命名后缀、`docs/model/pipelines/` 下的文档一一对应
LINE = "semantic"

PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR / "data"
MODELS_DIR = PKG_DIR / "models"
REPORTS_DIR = PKG_DIR / "reports"

#: 共享上游产物目录（四线共用，不按线分）
SHARED_DATA_DIR = PKG_DIR.parent.parent / "data"

#: 语义特征版本（契约边界：v2 不入库、不进交付链；契约二既有 14 项一字不动）
FEATURE_VERSION = "v2"

__all__ = [
           "DATA_DIR",
           "FEATURE_VERSION",
           "LINE",
           "MODELS_DIR",
           "PKG_DIR",
           "REPORTS_DIR",
           "SHARED_DATA_DIR",
]
