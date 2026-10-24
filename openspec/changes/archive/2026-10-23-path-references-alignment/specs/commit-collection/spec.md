## MODIFIED Requirements

### Requirement: 报出采集统计

采集 MUST 输出可核对的最小统计：抽取到的提交总数与提交时间跨度（最早至最晚）。

#### Scenario: 正常输出采集统计

- **WHEN** 采集流程正常结束
- **THEN** 提交总数与时间跨度同时出现在标准输出与 `data_model/preparation/reports/` 下

#### Scenario: 采集结果为空

- **WHEN** 采集结果为 0 条提交
- **THEN** 流程以失败退出并给出提示，MUST NOT 继续进入打标步骤
