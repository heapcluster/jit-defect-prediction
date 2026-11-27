## MODIFIED Requirements

### Requirement: MUST 产出两类评估指标

评估 MUST 同时包含 Effort-unaware 指标（AUC、F1、精确率、召回率）与 Effort-aware 指标（按审查精力衡量性价比，如 Kamei 原文 P_opt 或同类 IFA/EPA 口径），全部在检验集上计算，落 `data_model/pipelines/expert/reports/`。

#### Scenario: 指标报告完整

- **WHEN** 任一模型训练完成
- **THEN** 报告目录下指标表同时含两类指标，并注明检验集时间范围与样本数

#### Scenario: 缺检验集不得出指标（边界场景）

- **WHEN** 检验集为空或时间序断言未通过
- **THEN** 脚本终止，报告目录下不产生任何评估指标
