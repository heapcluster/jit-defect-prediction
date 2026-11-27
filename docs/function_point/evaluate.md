# 功能点 6 预测评估

一句话：选择系统已保存的一次模型预测结果（单一模型、单一测试集），按用户勾选的指标评估该次预测质量，输出评估图集 zip 与评估指标表（CSV / Excel）；不重算预测、不重新判定标签。

predictions 列契约与训练测试集、模型文件契约；API 见 [`../api/evaluate.md`](../api/evaluate.md)；页面见 [`../web_page/evaluate.md`](../web_page/evaluate.md)；图集入库见 [`../database/model_figure.md`](../database/model_figure.md)。

## 1 职责

- 从已保存的预测结果读取 `predicted_label` 与 `decision_threshold`，按勾选指标计算指标值。
- 产出评估图集 zip（内含逐张标准命名图片）与评估指标表（CSV / Excel）。
- 逐张图按后端标准命名单独保存并登记到 `model_figure`，支持按批次与模型查找。
- 校验预测结果的列契约、真标签完整性、单模型单测试集约束与标签 / 阈值一致性。

## 2 不负责

- 不训练、不预测、不重算概率、不重新判定标签；不生成特征。
- 不提供判定阈值选择；评估沿用预测结果中的 `decision_threshold`。
- 不做解释、定位与修复建议。
- 不把配置变更变成隐式重算：结果永远对应一次显式运行。

## 3 输入

| 输入 | 说明 |
|---|---|
| 已保存预测结果 | 必填，来自 `predict_batch` 成功任务，底层为 predictions Excel；固定单一模型、单一测试集，`predicted_label` 与 `decision_threshold` 必填且一致 |
| effort 来源 | 可选，`train_testset` 或 `clean_dataset`，用于 effort-aware 指标 |

`config`：`metrics`、`primary_metric`、`effort_enabled`、`figure_zip_name`、`metrics_name`、`output_format(csv|xlsx)`。`labels.csv` 不是有效输入，`dataset_id` 被忽略；`threshold`、`model_names`、`report_format`、`format` 不属于本接口，传入即拒绝。

## 4 流程

1. 用户从下拉框选择已保存预测结果，页面显示该结果详情介绍（模型、测试集、样本规模、阈值、生成时间）。
2. 用户确认排序质量 / 分类质量 / 工作量感知的指标勾选，逐项可查看指标含义。
3. 用户确认图集 zip 名称与指标表名称（有默认值可修改），核对完整配置。
4. 后端解析预测结果，校验列、真标签、单模型单测试集与标签 / 阈值一致性；按勾选指标计算指标值。
5. 合并可选 effort 来源，渲染排序 / 分类 / 工作量图；逐图按标准命名单独保存并登记到 `model_figure`。
6. 打包图集 zip、导出指标表 CSV / Excel，写入 manifest 与 summary 等内部记录；任务完成。

## 5 输出

用户可见产物（结果文件区只显示这两类）：

```text
<figure_zip_name>.zip                # 评估图集，内含逐张标准命名的图片
<metrics_name>.csv / .xlsx           # 评估指标表，按 output_format 导出
```

图集内每张图后端标准命名为 `evaluate_<job_id>_<figure_type>.png`（`figure_type` 取 `roc` / `pr` / `confusion` / `calibration` / `effort_unaware` / `effort_aware`），逐张保存并登记到 `model_figure`。

内部记录（不进入结果文件区）：

```text
evaluate_metrics_<job_id>.csv
evaluate_confusion_<job_id>.csv
<stem>.manifest.json
```

`summary`：`model_name`、`testset_ref`、`rows`、`unavailable`、`primary_metric`、`decision_threshold`、`label_stats`、`config{metrics,primary_metric,effort_enabled,figure_zip_name,metrics_name,output_format,dataset_version}`。

## 6 约束

- 空集或单类时相关指标置 null 并给警告，不编造 0。
- effort 缺失时 aware 指标标记 unavailable。
- 一次运行对应单一模型、单一测试集与一个数据集版本，不跨模型 / 版本混合。
- 阈值沿用预测结果；预测结果缺真标签或标签与阈值冲突时前置拒绝。
- 指标含义以 `GET /api/evaluate/metrics` 的 `description` / `formula` 为唯一数据源。

## 7 验收

- 指标与公式单源一致，退化场景处理正确。
- 单模型单测试集结果正确；传入 `threshold` / `model_names` 被拒绝。
- 图集 zip 可下载，内含逐张标准命名图片；指标表可导出 CSV / Excel。
- 每张图登记到 `model_figure`，可按 `job_id` 与 `model_name` 查询。
- 缺真标签、非单模型单测试集、标签与阈值冲突被前置拒绝。

## 8 边界

评估是独立工具：输入是已保存的预测结果文件而非某次训练的运行状态；同一批预测可反复评估，互不影响。
