## MODIFIED Requirements

### Requirement: 报出七项统计

样本集产出后 MUST 报出七项统计：总提交数、时间跨度、打标成功数、正样本数、负样本数、正样本比例、打标方法。

#### Scenario: 统计表落盘

- **WHEN** 汇总流程正常结束
- **THEN** `data_model/preparation/reports/` 下生成统计表，且该文件可被版本库收录作为证据

#### Scenario: 样本集为空

- **WHEN** 汇总后样本集为 0 行
- **THEN** 流程以失败退出并给出提示，MUST NOT 生成一份空统计表冒充完成
