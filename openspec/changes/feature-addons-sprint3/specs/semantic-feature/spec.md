## ADDED Requirements

### Requirement: 预训练模型语义特征提取

系统 SHALL 支持用预训练代码模型（如 CodeBERT / GraphCodeBERT 等）从源代码变更中提取深层语义特征，作为与 Kamei 14 维专家特征并列的**新增特征路线**；提取结果 MUST 以新增列或新特征版本的方式落盘，MUST NOT 改动契约二既有 14 项列名与顺序。

#### Scenario: 提取语义特征

- **WHEN** 给定一个提交的代码变更
- **THEN** 系统输出该变更的语义特征向量（维度由所选预训练模型决定），并以新特征版本标识

#### Scenario: 契约边界

- **WHEN** 语义特征接入样本集
- **THEN** 既有 14 项专家特征列保持不变，语义特征以附加列或独立特征版本存在，经契约变更流程登记

### Requirement: 专家特征 vs 语义特征对比实验

系统 SHALL 支持在同一数据切分下对比三类设置：仅 Kamei 14 专家特征、仅语义特征、二者融合；评估沿用现有两类指标（Effort-unaware / effort-aware）。

#### Scenario: 输出对比结论

- **WHEN** 三种设置在同一检验集上评测完成
- **THEN** 产出对比表（含 AUC / F1 / Precision / Recall 与 effort-aware 指标），作为附加功能证据

#### Scenario: 不静默切换交付模型

- **WHEN** 语义特征模型指标优于现交付模型
- **THEN** 本实验不改动后端加载的交付模型，切换须另开「模型切换」提案（spec `model-coverage` R6）

### Requirement: 计算资源与降级

语义特征提取 SHALL 在可用算力约束下运行；当无 GPU 或时间受限时，SHALL 支持抽样或缩减模型规模，并在报告中标注所用配置（模型、设备、样本量）。

#### Scenario: 无 GPU 降级

- **WHEN** 运行环境无 GPU
- **THEN** 采用 CPU 推理或抽样方案，报告中如实标注，不声称全量 GPU 结果
