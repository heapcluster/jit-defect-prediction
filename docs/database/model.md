# model（复用表）

模型注册表，一行对应一个已交付/已评估的模型。

| 字段 | 含义 |
|---|---|
| model_name | 主键，模型名（带线别后缀，全局唯一）：`lr_v1` / `lr_semantic_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| version_key | 模型版本键（排序用；跨族名会退化成字典序，默认模型由冠军口径决定） |
| trained_at | 训练完成时间 |
| algo | 算法：`lr` `rf` `xgb` `lgbm` `et` `svm` `mlp_deep` `tabnet` / `codebert_e2e` |
| feature_version | 该模型训练所用特征版本 |

**模型总量**：expert 8 + semantic 8 + fused 8 + e2e 1 = **25**，`model_name` 全部唯一。

## 线别（line）怎么来的——不加列
`line` **不落数据库列**，由 `model_name` 后缀约定推导，与磁盘上的交付目录同名同口径：

| 判定 | 归属 line | 交付目录 |
|---|---|---|
| `*_v1` 且不含 `semantic` / `fused` / `e2e` | `expert` | `data_model/pipelines/expert/` |
| `*_semantic_v1` | `semantic` | `data_model/pipelines/semantic/` |
| `*_fused_v1` | `fused` | `data_model/pipelines/fused/` |
| `*e2e*` | `e2e` | `data_model/pipelines/e2e/` |

**理由**：加一列要为 4 张老表做迁移、重灌权重、还可能与目录名不一致；后缀与目录同源，一条规则就能算出来，前端两级切换（line → model）直接用规则分组即可。新增线时必须同步更新本表，MUST NOT 靠猜。
