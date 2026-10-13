## ADDED Requirements

### Requirement: 双路线语义特征提取

系统 SHALL 支持用两条预训练路线从代码变更提取深层语义特征：
① **打底路线（全量）**——轻量句向量模型（默认 `all-MiniLM-L6-v2`）对全部样本提特征；
② **增强路线（抽样）**——代码专用预训练模型（CodeBERT / GraphCodeBERT 等）在抽样子集上提特征。
提取结果 MUST 以新 `feature_version`（v2）标识落盘，MUST NOT 改动契约二既有 14 项列名与顺序。

#### Scenario: 按文件构造变更文本

- **WHEN** 给定一次提交的 diff
- **THEN** 每个改动文件生成一条文本（文件路径 + 变更类型 + 增删行 + 提交信息首行），单文件文本超模型上限时按行截断，并记录被截断的文件数与行数

#### Scenario: 按提交聚合语义向量

- **WHEN** 一次提交改动多个文件
- **THEN** 该提交的语义向量为各文件向量的均值；仅改动 1 个文件时即该文件向量

#### Scenario: 落盘带特征版本标识

- **WHEN** 语义特征提取完成
- **THEN** 产出 `semantic_<模型>_<feature_version>.csv`，含 `commit_hash` 与 `sem_0 … sem_{d-1}` 列，且不写入 `commit_feature` 表

### Requirement: 三类设置对比实验

系统 SHALL 在同一切分、同一测试集、同一套模型下对比三类设置：仅 Kamei 14 专家特征、仅语义特征、二者融合；评估 MUST 沿用现有两类指标（Effort-unaware 与 Effort-aware）。

#### Scenario: 输出三类对比表

- **WHEN** 三类设置评测完成
- **THEN** 产出对比表（含 AUC / F1 / Precision / Recall / Accuracy 与 `P_norm`、同预算重排召回），并标注每类所用特征版本与模型清单

#### Scenario: 语义特征不占优时如实报告

- **WHEN** 语义或融合设置的指标不优于专家特征基线
- **THEN** 报告 MUST 如实写出该结论与可能原因（样本量、文本构造、模型容量），**不得**选择性只报更优的一组

### Requirement: 契约与交付边界

语义特征 MUST NOT 改动契约二既有列名与顺序；MUST NOT 新增接口或库表列；交付模型 MUST NOT 因本 change 静默切换。

#### Scenario: 契约边界

- **WHEN** 语义特征接入样本集
- **THEN** 既有 14 项专家特征列保持不变，语义特征以附加列或独立文件存在，并经契约变更流程登记 `feature_version` v2

#### Scenario: 不静默切换交付模型

- **WHEN** 语义或融合模型指标优于现交付模型
- **THEN** 本 change 不改动后端加载的交付模型，切换须另开「模型切换」提案（spec `model-coverage` R6）

### Requirement: 计算资源约束与如实标注

语义特征提取 SHALL 在可用算力约束下运行；当无 GPU 或时间受限时，SHALL 支持 CPU 推理或抽样方案。

#### Scenario: 无 GPU 降级

- **WHEN** 运行环境无 GPU
- **THEN** 采用 CPU 推理或抽样方案，报告中如实标注模型名、设备、样本量、是否全量、截断统计，**不得**声称全量 GPU 结果

#### Scenario: 环境隔离

- **WHEN** 安装语义特征依赖（`torch` / `sentence-transformers`）
- **THEN** MUST 装在独立环境（`jit-semantic`），MUST NOT 改动既有 `jit-defect` 环境的包版本

### Requirement: 专家特征消融与重要性分析

系统 SHALL 支持对 Kamei 14 维专家特征做留一法（leave-one-out）与置换重要性分析，输出特征效力排序。

#### Scenario: 留一法消融

- **WHEN** 对 14 项特征逐一移除后重训同一模型
- **THEN** 输出每项移除后的指标变化，并给出「移除后指标下降最多」的 Top-K 特征

#### Scenario: 置换重要性

- **WHEN** 在检验集上对单项特征做随机置换
- **THEN** 输出该项造成的指标衰减，作为与留一法交叉验证的第二口径

### Requirement: 跨项目不可迁移的设计登记

系统 SHALL 在模型线报告中显式登记「跨项目 JIT 预测不可迁移」这一文献结论，并说明本组采用单仓库（ActiveMQ）设计的依据。

#### Scenario: 报告登记

- **WHEN** 产出模型线报告
- **THEN** 报告 MUST 包含一节说明：依据 Kamei et al. 2013 的项目内可用 / 跨项目不可迁移结论，本组采用单一固定仓库 + 时间序切分的设计选择及其理由
