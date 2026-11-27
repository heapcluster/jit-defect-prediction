## ADDED Requirements

### Requirement: 数据链路汇总

系统 SHALL 提供 `GET /api/storage/lineage`，按 `job.chain_id` 汇总任务链路，节点含 `job_id/kind/status/parent_job_ids/model_names/dataset_id/artifacts`，链路含 `chain_id/title/created_at/node_count/kinds`。链路关系 MUST 只来自已落库字段，不按文件名猜测；缺少父任务的孤立任务单独成链并标注“未关联”。

#### Scenario: 顺序链路

- **WHEN** 依次运行收集、清洗、训练、预测、评估
- **THEN** 返回同一条链，节点 `parent_job_ids` 逐级正确

#### Scenario: 训练分叉

- **WHEN** 同一清洗结果训练多个算法
- **THEN** 分叉节点仍属同一 `chain_id`，不做线性化

### Requirement: 整链删除

系统 SHALL 提供 `DELETE /api/storage/chains/{chain_id}?confirm=true`。缺少 `confirm=true` MUST 返回 40001。删除前 MUST 检查链内模型是否被链外 `prediction`/`model_figure` 引用、链内数据集是否被链外任务引用；存在引用时返回 40001 并在 `data.references` 列出引用方，不执行任何删除。

#### Scenario: 共享保护

- **WHEN** 链内模型被链外预测任务引用
- **THEN** 返回 40001 与引用方清单，链内数据保持不变

#### Scenario: 确认删除

- **WHEN** 链路内资产没有外部引用且 `confirm=true`
- **THEN** 删除链内任务、已发布产物、模型登记与数据集，返回计数
