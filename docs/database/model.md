# model（复用表）

**一句话**：模型注册表，一行对应一个已交付/已评估的模型；是 `prediction` / `model_figure` 的外键目标，也是前端「选线 → 选模型」两级选择器的数据源。

## 字段

| 字段 | 类型 | 键 | 含义 |
|---|---|---|---|
| model_name | VARCHAR(64) | 主键 | 模型名，全局唯一：`lr_v1` / `lr_semantic_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| line | VARCHAR(16) | 索引 | 所属主方案：`expert` / `semantic` / `fused` / `e2e` |
| algo | VARCHAR(64) | — | 算法：`lr` `rf` `xgb` `lgbm` `et` `svm` `mlp_deep` `tabnet` / `codebert_e2e` |
| version_key | VARCHAR(64) | — | 版本键（同族内排序用） |
| trained_at | DATETIME | — | 训练完成时间（可空） |
| feature_version | VARCHAR(32) | — | 该模型训练所用特征版本（可空） |
| updated_at | DATETIME | — | 审计列 |

## 主键为什么直接用 `model_name`（BCNF）
- 函数依赖只有一组：`model_name → line / algo / version_key`（名字的前缀后缀决定这三列），决定因素是主键 → **满足 BCNF**。
- `model_name` 是**交付契约的一部分**：出现在 `feature_order.txt` 的 `[models]` 段、模型文件名 `.pkl`、图目录名里，全局唯一且稳定，不存在「改名级联」的实际风险——所以不需要自增代理键。
- 与 `commit` 表同口径：`commit_hash` 是内容寻址的自然主键，`model_name` 是交付清单锁定的自然主键，都直接做主键，不造死 id。

## 约束与索引
- `model_name` 主键唯一；`line` 单列索引（前端 `GROUP BY line` 分组）。

**模型总量**：expert 8 + semantic 8 + fused 8 + e2e 1 = **25**，`model_name` 全部唯一。

## 被谁所用
| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 后端启动 `ensure_model_rows`、模型线交付导入（`export_sql.py`） | 注册已加载/已交付模型 |
| 读取 | 后端 `models`（清单）、`figures` / `test_detail`（join 取 line）、`predict`（校验存在性） | 两级选择器、图/明细分组、推理定位模型 |
| 展示 | 前端风险列表、趋势看板、测试集评估页的两级选择器 | 选线 → 选模型 |

## 线别（line）落库
`line` 是显式列，由交付时写入（见 `data_model/evaluation/export_sql.py`），不从 `model_name` 后缀现场推导。前端两级切换（line → model）直接按 `line` 列 `GROUP BY`；新增线时必须同步写入 `line`，MUST NOT 靠猜。

## 默认模型口径（写死，不再热切换）
`runtime_setting` 已删除、冠军模型热切换已下线。**默认模型 = 已加载模型中 `version_key` 最大者**（确定性规则，见 `model_registry.default_model`）。所有「未指定 `model_name`」的查询/预测统一走这条规则，不再有运行时改写入口。
