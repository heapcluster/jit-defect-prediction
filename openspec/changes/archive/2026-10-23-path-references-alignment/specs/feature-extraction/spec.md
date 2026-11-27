## MODIFIED Requirements

### Requirement: 全量产物与统计报告 MUST 可入库可复现

特征表落 `data_model/data/`（不入库）；统计报告落 `data_model/preparation/reports/feature_stats.md`（可入库），报告 MUST 含 14 项特征的取值外沿与契约缺口登记结论。

#### Scenario: 干净环境复现

- **WHEN** 在干净 clone 上按 `docs/model/data-pipeline.md` 第 5 节命令重跑特征计算
- **THEN** 特征表与既有产物逐值一致（版本已固定，允许 ±0）

#### Scenario: 上游产物缺失（边界场景）

- **WHEN** 干净 clone 后 `data_model/data/` 内尚无 01 / 02 的中间产物，就直接执行 03
- **THEN** 流程以非零退出码终止并提示先跑上游步骤，MUST NOT 产出零行特征表冒充完成
