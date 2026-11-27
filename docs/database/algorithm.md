# algorithm

**一句话**：算法库表，登记每条模型线可用的算法及其超参数 schema；训练表单的元数据唯一来源，前端 MUST NOT 硬编码算法清单或超参数范围。

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| line | VARCHAR(16) | NOT NULL | 联合主键 | 所属模型线：`expert`（Kamei 14 维）/ `semantic`（冻结头 CodeBERT 768 维） |
| algo | VARCHAR(64) | NOT NULL | 联合主键 | 算法标识 |
| family | VARCHAR(32) | NOT NULL | — | 族：`linear` / `tree` / `boost` / `svm` / `mlp` / `tabnet` / `kernel` / `bayes` / `transformer` |
| hyperparams_json | TEXT | NOT NULL | — | 超参数 schema：`[{name, type, default, min, max, choices, desc}]` |
| enabled | TINYINT(1) | NOT NULL DEFAULT 1 | — | 是否默认参与训练 |
| description | VARCHAR(255) | 可空 | — | 一句话说明与适用提示 |

## 主键与约束理由

- 联合主键 `(line, algo)`：同一算法在不同线各有独立超参 schema（输入维度不同），一行一个线算组合。
- 训练任务创建时前置校验 `(line, algo)` 存在且 `enabled=1`；不兼容组合返回 40001，MUST NOT 进入训练后才失败。显式选择 disabled 算法须带确认参数。

## 默认登记清单

| line | algo | enabled | 说明 |
|---|---|---|---|
| expert | lr / rf / xgb / lgbm / et / svm / mlp_deep / tabnet / nb / dt / knn / mlp | 1 | 12 个可选算法，前 8 个默认勾选（Kamei 14 维输入） |
| semantic | lr / rf / xgb / lgbm / et / svm / mlp_deep / tabnet / nb / dt / knn / mlp | 1 | 12 个可选算法，前 8 个默认勾选（冻结头 CodeBERT 768 维输入） |

`mlp`（1 隐藏层）保留为可显式选择项但默认不训练，推荐使用 `mlp_deep`（3 隐藏层 + 早停）；`nb` / `dt` / `knn` 同为默认不训练的可选项。有效 `line` 取值只有 `expert` / `semantic`。前端算法清单来自 `/api/algorithms`，不从 `DEFAULT_MODELS` 或页面硬编码推导。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 建表预置默认清单；算法注册接口 | 算法库维护 |
| 读取 | 训练配置 API / 训练服务入参校验、解释兼容矩阵 | 表单与校验单源 |
| 展示 | 训练抽屉动态超参数表单、算法多选 | 表单完全由本表驱动 |

## 口径

- 超参数 schema 是表单与校验的共同来源：类型 / 默认值 / 范围 / 枚举一处维护；训练服务按 schema 校验入参，越界返回 40001。
- `family` 供解释器兼容矩阵与 SHAP 解释器选择复用，MUST NOT 在解释服务里再写一份族判定。
- **课程类别硬要求**：`family` 中 `mlp` / `tabnet` / `transformer` 属深度学习族，其余属经典机器学习族；登记清单 MUST 保证两类合计不少于 8 种启用模型（现两线 16 模型 = 6 经典 + 2 深度 × 2 线，满足要求，对照见 [`../function_point/train.md`](../function_point/train.md) §3）。
- 种子、早停、决策阈值等**训练级**参数属于训练配置模板，不在本表；本表只放算法专属超参数。
- 新增算法 = 插一行 + 实现注册，不改前端代码。

## 验收

- 训练表单算法多选与超参数控件完全由本表驱动；改一行 schema，前端表单随之变化。
- 提交越界超参数 / 不兼容线算组合 → 40001 且任务不创建。
- 默认清单与 pipelines 配置一致；disabled 算法不出现在默认多选中。