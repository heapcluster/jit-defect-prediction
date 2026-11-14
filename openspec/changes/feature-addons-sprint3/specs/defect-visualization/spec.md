## ADDED Requirements

### Requirement: 提交级归因与真实差异展示

提交详情页 SHALL 展示已加载模型给出的提交级特征归因；配置的 `SOURCE_REPO` 中能读取目标提交时，SHALL 展示该提交真实 diff 的文件和新增行。文件与新增行展示 MUST NOT 标为文件级 SHAP 贡献或行级缺陷概率。

#### Scenario: 有可达的源仓库

- **WHEN** 打开已预测提交且 `SOURCE_REPO` 能读取其真实 diff
- **THEN** 展示提交级特征归因及实际变更文件与新增行，并注明新增行展示不等于行级模型归因

#### Scenario: 源仓库未配置或提交不可达

- **WHEN** `SOURCE_REPO` 缺失或无法读取目标提交 diff
- **THEN** 降级展示提交级特征归因及说明，不编造文件与行级证据

### Requirement: 归因缺失的空态

模型未提供归因时，页面 SHALL 展示明确空态说明，MUST NOT 留白、MUST NOT 回显服务端路径与堆栈。

#### Scenario: 归因缺失

- **WHEN** 提交存在但 `explanation` 为空数组（模型不支持解释器）
- **THEN** 页面展示「该模型未提供归因」的空态文案，风险分与其他信息照常展示

#### Scenario: 单文件提交

- **WHEN** 真实 diff 仅涉及一个文件
- **THEN** 文件清单只有一行，显示该文件及真实新增行，不出现排序错乱或除零异常
