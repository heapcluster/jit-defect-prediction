# labeled-dataset Specification

## Purpose
把提交清单与缺陷标签汇成一份可训练样本集，并报出判断数据是否可用的统计证据，使下游模型线拿到的是可复现、可对照的同一份数据。

## Requirements

### Requirement: 样本集字段完整且与上游一一对应

样本集 MUST 至少含 `commit_hash`、`committed_at`、`is_bug_inducing` 三列，MUST 与提交清单、标签表按 `commit_hash` 一一对应。

#### Scenario: 与标签表一一对应

- **WHEN** 按 `commit_hash` 比对样本集与标签表
- **THEN** 不存在「有标签却缺样本」或「有样本却缺标签」的行

#### Scenario: 存在未打标提交（边界）

- **WHEN** 部分提交未能判定标签
- **THEN** 这些提交 MUST NOT 以负样本身份进入样本集，其数量 MUST 在统计中单独列出

### Requirement: 报出七项统计

样本集产出后 MUST 报出七项统计：总提交数、时间跨度、打标成功数、正样本数、负样本数、正样本比例、打标方法。

#### Scenario: 统计表落盘

- **WHEN** 汇总流程正常结束
- **THEN** `data_model/reports/` 下生成统计表，且该文件可被版本库收录作为证据

#### Scenario: 样本集为空

- **WHEN** 汇总后样本集为 0 行
- **THEN** 流程以失败退出并给出提示，MUST NOT 生成一份空统计表冒充完成

### Requirement: 不做训练与切分

本能力 MUST NOT 输出训练/检验切分结果或模型产物。切分 MUST 按 `committed_at` 时间序进行（前 70% 训练、后 30% 检验），属下游 change 的职责。

#### Scenario: 样本集不含切分标记

- **WHEN** 检查样本集列
- **THEN** 不存在 `split`、`is_train` 一类的切分列或切分文件

#### Scenario: 下游要求随机切分

- **WHEN** 下游提出对样本集做随机切分的要求
- **THEN** 该要求 MUST 被拒绝并说明理由（时间相关特征会造成时序数据泄漏），改由下游 change 按时间序切分
