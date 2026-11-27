# contract-completion — 设计说明

## 图集读取模型

- `model_figure` 主键保持 `(job_id, model_name, figure_type)`。
- 写入方：评估任务发布成功后逐图登记；storage 导入图文件仍按 `(job_id="", model_name, figure_type)` 登记。
- 读取方：`GET /api/figures` 先按 `job_id`/`model_name` 过滤行，再归一历史 `effort` 类型，最后按固定顺序输出；`batches[]` 用于模型性能页选择批次。
- 历史数据不迁移，读取层兼容。

## 评估

- 阈值与预测标签只来自 predictions 文件；评估配置不接受新阈值。
- 产物：`evaluate_figures_<suffix>.zip`（图集）、`<metrics_name>.csv|xlsx`（指标表）为用户可见；`evaluate_metrics_*`、`evaluate_confusion_*`、`evaluate_comparison_*`、`evaluate_report_*` 为内部记录；逐图 PNG 单独落盘用于登记与按批次下载。
- 图集 zip 内命名固定 `evaluate_<job_id>_<figure_type>.png`。

## storage 链路

- 链路关系只来自 `job.chain_id` 与 `job.parent_job_ids`，不按文件名猜测。
- 孤立任务单独成链并标注“未关联”。
- 整链删除先检查链内模型被链外 `prediction`/`model_figure` 引用、链内数据集被链外任务引用；有引用返回 40001 与 `data.references`。
- 删除产物目录复用 `output_store.discard_output`；不删除仓库内交付权重。

## collect 公开数据集

- 公开模式 HTTP 只允许 `https`，无凭证/query/hash；URL 抓取与列读取复用 `public_load`。
- `field_mapping` 为“目标列 → 来源列”，必需 `commit_hash/committed_at/is_bug_inducing`；`label_mapping` 支持 `{positive, negative}` 或值级 `{源值: 1/0}`。
- Git 与公开模式输出同一 `collected_commits` CSV；收集任务不再预生成 XLSX，下载时按需生成由下载端点负责。

## predict / explain 链路

- `predict_batch` 父任务：`testset_ref` 指向的训练任务 + `model_artifact.train_job_id`，去重。
- 批量预测成功后在同一事务写入 `prediction`；模型未登记时任务失败。
- `explain` 父任务：模型训练任务 + 预测核对表 manifest 对应的预测任务。

## 前端

- 模型性能抽屉先取 `batches[]`，默认“最新批次”，切换后按 `job_id` 取图。
- storage 增加“数据链路”tab；整链删除二次确认。
- 详情页使用 `LocalizationPanel` 内联运行定位；路由移除 `/predict/explain` 与 `/predict/localization`。
