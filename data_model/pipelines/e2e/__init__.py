"""端到端 pipeline 包：不冻结 backbone，在变更文本上 fine-tune。

状态：**⬜ 计划态 · 尚未立项** —— 本包只定产出归属与路径常量；脚本落地前必须
先有 openspec change（proposal → specs → design → tasks），不得先跑代码再补规格。
方案与口径：`docs/model/pipelines/end-to-end.md`（权威）。

产出归属（只归本线，四线隔离）：

- ``data/``     端到端数据集 ``e2e_dataset_v2.csv``
                 （commit_hash + 文本 + 标签 + 切分归属）
- ``models/``   ``codebert_e2e_v1.pkl``（仅评估，不进交付链）
- ``reports/``  ``end_to_end.md``（第四类结论，单独一份）

共享上游产物（变更文本、标签、切分下标）在 ``data_model/data/``，四线共用。
"""

from pathlib import Path

#: 线名，与产物命名后缀、`docs/model/pipelines/` 下的文档一一对应
LINE = "e2e"

PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = PKG_DIR / "data"
MODELS_DIR = PKG_DIR / "models"
REPORTS_DIR = PKG_DIR / "reports"

#: 共享上游产物目录（四线共用，不按线分）
SHARED_DATA_DIR = PKG_DIR.parent.parent / "data"

__all__ = [
           "DATA_DIR",
           "LINE",
           "MODELS_DIR",
           "PKG_DIR",
           "REPORTS_DIR",
           "SHARED_DATA_DIR",
]
