## MODIFIED Requirements

### Requirement: 模型组合 MUST 覆盖不少于 2 类且不少于 8 种

模型组合 MUST 同时满足：**类别数 ≥ 2**（至少含「经典机器学习」与「神经网络（深度学习）」两类的划分）且**模型数 ≥ 8**；每个模型 MUST 登记 `model_name`（`<算法>_v<序号>`）与所属类别，登记结果 MUST 落 `data_model/pipelines/expert/reports/`。

#### Scenario: 覆盖达标

- **WHEN** 覆盖矩阵报告产出
- **THEN** 报告中出现 8 个模型，每个模型有 `model_name`、所属类别与两类指标，且类别集合含「经典机器学习」与「神经网络（深度学习）」

#### Scenario: 只有一类（边界场景）

- **WHEN** 用经典机器学习族的模型凑到 8 种，但没有任何神经网络模型
- **THEN** 判定为**不达标**（类别数仍为 1），MUST 补神经网络类模型后才算完成

### Requirement: 交付模型 MUST 保持不变

本 change MUST NOT 改动后端加载路径：`data_model/pipelines/expert/models/feature_order.txt` 的 `[models]` 段 MUST 保持既有交付模型不变，`python -m pipelines.expert.predict` 的产物 `prediction_result.csv` 口径不变，新增模型 MUST NOT 进入后端加载清单。

#### Scenario: 交付清单不变

- **WHEN** 本 change 合入
- **THEN** `[models]` 段仍为既有交付模型，报告中新增模型标注为「评估用，不参与交付」

#### Scenario: 评估出更优模型（边界场景）

- **WHEN** 矩阵显示某新增模型在两类指标上均显著优于交付模型
- **THEN** 登记为「模型切换」提案（另开 change，含后端加载与契约影响评估），MUST NOT 在本 change 静默切换交付模型
