# model（复用表）

模型注册表，一行对应一个已交付/已评估的模型。

| 字段 | 含义 |
|---|---|
| model_name | 主键，模型名（带线别后缀，全局唯一）：`lr_v1` / `lr_semantic_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| version_key | 模型版本键（排序用；跨族名会退化成字典序，默认模型由冠军口径决定） |
| trained_at | 训练完成时间 |
| algo | 算法：`lr` `rf` `xgb` `lgbm` `et` `svm` `mlp_deep` `tabnet` / `codebert_e2e` |
| feature_version | 该模型训练所用特征版本 |
| **line（新增）** | 所属主方案：`expert` / `semantic` / `fused` / `e2e`，供前端两级切换分组 |

**模型总量**：expert 8 + semantic 8 + fused 8 + e2e 1 = **25**，`model_name` 全部唯一。

## 线别（line）落库
`line` 是新增列，由交付时写入（见 `data_model/evaluation/export_sql.py`），不从 `model_name` 后缀现场推导：

| line | 模型名示例 | 交付目录 |
|---|---|---|
| `expert` | `lr_v1` | `data_model/pipelines/expert/` |
| `semantic` | `lr_semantic_v1` | `data_model/pipelines/semantic/` |
| `fused` | `lr_fused_v1` | `data_model/pipelines/fused/` |
| `e2e` | `codebert_e2e_v1` | `data_model/pipelines/e2e/` |

**理由**：前端两级切换（line → model）直接按列 `GROUP BY line`，不依赖命名约定；与磁盘交付目录同名同口径，但**以数据库列为准**，避免「改了名字没改目录」的漂移。新增线时必须同步写入 `line`，MUST NOT 靠猜。
