# model（复用 + 改动）

模型注册表，一行对应一个已交付/已评估的模型。

| 字段 | 含义 |
|---|---|
| model_name | 主键，模型名（带线别后缀，全局唯一）：`lr_v1` / `lr_semantic_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| version_key | 模型版本键（训练快照标识） |
| trained_at | 训练完成时间 |
| algo | 算法：`lr` `rf` `xgb` `lgbm` `et` `svm` `mlp_deep` `tabnet` / `codebert_e2e` |
| feature_version | 该模型训练所用特征版本 |
| **line（新增）** | 所属主方案：`expert` / `semantic` / `fused` / `e2e`，供前端两级切换分组 |

**模型总量**：expert 8 + semantic 8 + fused 8 + e2e 1 = **25**，`model_name` 全部唯一。
