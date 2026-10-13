## ADDED Requirements

### Requirement: 公开数据集加载与保存

系统 SHALL 支持加载并保存现有公开 JIT 缺陷数据集，解析为与 `commit` / `commit_label` / `commit_feature` 对齐的记录；缺必需字段 MUST 报错终止，MUST NOT 产出半成品。

#### Scenario: 正常加载

- **WHEN** 给定一个公开数据集目录
- **THEN** 产出与契约一 `commit` / `commit_label` 字段对齐的记录集，并附带来源、许可证、获取日期元数据

#### Scenario: 缺必需字段

- **WHEN** 数据集缺少 `commit_hash` / 标签列 / 时间戳中任一项
- **THEN** 加载器报错终止并指明缺哪个字段，MUST NOT 以默认值填充后继续

#### Scenario: 字段映射可追溯

- **WHEN** 公开数据集的字段名与本组契约字段名不一致
- **THEN** 输出字段映射表；口径冲突显式登记，MUST NOT 静默对齐

### Requirement: 标签粒度治理（回应课程 (3)-①）

系统 SHALL 对每个加载的数据集标注其标签粒度；有缺陷类型则保留类型字段，无缺陷类型 MUST 在元数据中明确写「无缺陷类型」，MUST NOT 伪造类型。

#### Scenario: 无缺陷类型的数据集

- **WHEN** 数据集仅含「是否引入缺陷」二值标签
- **THEN** 元数据记录「标签粒度 = 二值，无缺陷类型」，并在质量报告中作为已知局限列出

#### Scenario: 有缺陷类型的数据集

- **WHEN** 数据集含缺陷类型字段
- **THEN** 保留该字段并输出类型分布统计，作为「突破标签粒度过粗」的证据

### Requirement: 语种分布统计（回应课程 (3)-②）

系统 SHALL 统计并报告每个数据集及合并后数据集的编程语言构成。

#### Scenario: 输出语种分布

- **WHEN** 数据集加载完成
- **THEN** 质量报告含「各数据集语言 × 提交数 × 占比」表；若含非 Java 项目，明确标注为对「主要针对 Java」问题的回应证据

### Requirement: 数据质量评价（回应课程 (3)-③）

系统 SHALL 按高质量数据集评价口径输出质量报告，至少覆盖缺失率、重复率、字段一致性、时间序一致性。

#### Scenario: 输出质量报告

- **WHEN** 数据集加载完成
- **THEN** 产出 `data_model/reports/public_dataset_quality.md`，含四项指标、异常样本清单（可点回具体记录）与处置建议

#### Scenario: 重复记录

- **WHEN** 同一 `commit_hash` 出现多次且标签不一致
- **THEN** 计入重复率并单列「标签冲突」子项，MUST NOT 静默去重保留其一

#### Scenario: 时间序不一致

- **WHEN** 记录的 `committed_at` 无法解析或早于仓库首个提交
- **THEN** 计入时间序不一致项并单列，MUST NOT 静默剔除

### Requirement: 与 ActiveMQ 基线并列而非替换

公开数据集 MUST NOT 替换 ActiveMQ 基线；MUST NOT 进入交付链（不入库、不改交付模型、不改接口路径）。

#### Scenario: 基线不变

- **WHEN** 公开数据集加载与治理完成
- **THEN** `data_model/models/[models]` 段、契约三接口、契约二 14 项列名与顺序均无改动

#### Scenario: 用途限定

- **WHEN** 使用公开数据集产出任何结论
- **THEN** 结论 MUST 标注「基于公开数据集 X，与 ActiveMQ 基线并列对照」，MUST NOT 表述为替换了交付数据

### Requirement: 抽样不得随机

当数据集体积过大需抽样时，抽样 SHALL 按时间序分层，MUST NOT 随机抽样。

#### Scenario: 分层抽样

- **WHEN** 对大数据集抽样
- **THEN** 按 `committed_at` 分层等距抽取，抽样方法、样本量、层级边界写入报告
