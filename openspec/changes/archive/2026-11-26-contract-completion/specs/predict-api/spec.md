## ADDED Requirements

### Requirement: 批量预测结果预览

系统 SHALL 提供 `GET /api/predict/preview/{job_id}?page=&size=`，优先读取 `prediction` 表中该任务的记录并分页；无记录时回退读取核心 CSV。返回 `columns/preview/total/page/size`，列 MUST 严格等于 `PREDICTIONS_COLUMNS`。

#### Scenario: 分页预览

- **WHEN** 前端请求成功批量预测任务的预览
- **THEN** 返回前 20 行（默认）与总数；`size` 上限 100

#### Scenario: 非预测任务

- **WHEN** `job_id` 不属于 `predict_batch` 或不存在
- **THEN** 返回 40400

### Requirement: 测试集来源与父任务

`POST /api/predict/run` SHALL 接受 `testset_ref`、`output_name`、`save_to_db`。`testset_ref` MUST 指向 `train` 成功任务，并从其核心 `train_testset_<job_id>.csv` 读取测试集；网页 MUST NOT 上传任意表格作为测试集。父任务 SHALL 为由 `testset_ref` 推导的训练任务与 `model_artifact.train_job_id` 去重后的集合。

批量预测成功后 SHALL 将全部结果行写入 `prediction`；`save_to_db=false` 时不写库。核心产物名为 `predict_predictions_<job_id>.csv` 或 `<output_name>.csv`，不预生成 XLSX。

#### Scenario: 从训练任务取测试集

- **WHEN** 请求携带 `testset_ref` 且不携带表格
- **THEN** 从该训练任务读取 `train_testset_*.csv` 与 manifest，写入链路父节点并执行预测

#### Scenario: 保存预测结果

- **WHEN** 预测任务成功且 `save_to_db=true`
- **THEN** `prediction` 表中每个成功提交一行，含风险分、判定标签、阈值与版本
