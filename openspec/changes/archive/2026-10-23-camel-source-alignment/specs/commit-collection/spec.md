## ADDED Requirements

### Requirement: Camel 固定数据源

采集 MUST 使用 Apache Camel 仓库 `https://github.com/apache/camel.git`，默认目录为 `data_model/data/camel/`，固定 tag 为 `camel-4.23.0`，完整提交为 `b2329103df8f5d1edfca2ad262be09e3be95ee68`；产出 `repo_name` MUST 为 `camel`。登记位置 MUST 为 `docs/model/data-pipeline.md`，不得继续使用旧 ActiveMQ 版本作为当前数据源。

#### Scenario: 干净环境复现
- **WHEN** 按当前数据链路文档克隆并采集
- **THEN** 默认路径、固定提交和 CSV 仓库名均与 Camel 登记一致，已有字段名和类型不变

#### Scenario: 旧仓库版本被误用
- **WHEN** 默认采集命令读取到与登记值不同的 HEAD
- **THEN** 失败退出且不产出提交清单，要求先核对版本
