# 预测评估 API（evaluate）

一句话：消费一份系统已保存的预测结果（单一模型、单一测试集），按用户勾选的指标计算指标值与图，交付评估图集 zip 与评估指标表（CSV / Excel）；不重新训练、不重算预测、不重新判定标签。

predictions 列契约见 [`../api/predict.md`](predict.md)；effort 来源见训练测试集 / 清洗数据集列契约；指标公式单源为 `data_model/evaluation/metrics.py`；功能点职责见 [`../function_point/evaluate.md`](../function_point/evaluate.md)。

## 1. 职责与不负责范围

- 负责从已保存的预测结果读取 `predicted_label` 与 `decision_threshold`，按勾选指标计算指标值与图。
- 负责校验预测结果的列契约、真标签完整性与单模型单测试集约束。
- 负责为图集内每张图按标准命名单独保存，并登记到 `model_figure`，支持按批次与模型查找。
- 不负责训练、预测、解释；不重算概率，不提供或接受新的判定阈值。

## 2. 端点契约

### GET /api/evaluate/metrics

无参数（任何 query → 40001）。响应：

```json
{
  "metrics": [{"key": "auc", "name": "...", "description": "...", "formula": "...", "threshold_dependent": false, "effort_aware": false}],
  "defaults": {"metrics_selected": ["..."], "primary_metric": "f1", "effort_enabled": false}
}
```

指标键固定 10 个：`auc, ap, f1, precision, recall, accuracy, recall_at_20, recall_at_50, p_norm, popt`。

`description` 与 `formula` 供页面逐项展示指标含义（`GET /api/evaluate/metrics` 是含义的唯一数据源）。

### POST /api/evaluate/run

`multipart/form-data`：

| part | 必填 | 契约 |
|---|---|---|
| `prediction_job_id` | 是 | 已保存的批量预测任务 id（对应 `predict_batch` 成功任务），指向单一预测结果文件；也可由前端传 `files[]` 直接给一份 predictions Excel |
| `config` | 是 | JSON 文本 |

`config` 字段：

| 字段 | 必填 | 契约 |
|---|---|---|
| `metrics` | 否 | 非空、去重、必须在指标注册表内 |
| `primary_metric` | 否 | 必须属于 `metrics` |
| `effort_enabled` | 否 | bool |
| `figure_zip_name` | 否 | 图集 zip 名称，用户可改，有默认值；不含扩展名时自动补 `.zip` |
| `metrics_name` | 否 | 指标表基名，用户可改，有默认值；导出时补 `.csv` / `.xlsx` |
| `output_format` | 否 | `csv` / `xlsx`，仅控制指标表导出格式，默认 `csv` |

**不属于本接口的字段**：`threshold`（评估沿用预测结果中的 `decision_threshold`，不接受新阈值）、`model_names`（一次评估固定单一模型）、`report_format` / `format`（评估不生成报告与比较产物）。传入这些字段一律 40001。

`labels.csv` 不是有效输入，上传会被拒绝；`dataset_id` 会被忽略。

响应：同步（≤5000 行）返回 `{job_id,status,outputs,summary,error_log}`；异步返回 `{job_id,status}`。

`summary`：`model_name`、`testset_ref`、`rows`、`unavailable[]`、`primary_metric`、`decision_threshold`（沿用值）、`label_stats`、`config{metrics,primary_metric,effort_enabled,figure_zip_name,metrics_name,output_format,dataset_version}`。

### GET /api/evaluate/outputs/{job_id}/{name}

用户可见产物只有两类：

```text
<figure_zip_name>.zip                # 评估图集，内含逐张标准命名的图片
<metrics_name>.csv / .xlsx           # 评估指标表，按 output_format 导出
```

zip 内每张图由后端标准命名，形如 `evaluate_<job_id>_<figure_type>.png`（`figure_type` 取 `roc` / `pr` / `confusion` / `calibration` / `effort_unaware` / `effort_aware`），逐张单独保存并登记到 `model_figure`。

内部记录（不进入结果文件区、不作为用户可见下载入口）：

```text
evaluate_metrics_<job_id>.csv        # 长表指标明细
evaluate_confusion_<job_id>.csv
<stem>.manifest.json
```

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未选预测结果、预测结果 schema 非法、缺真标签、非单模型单测试集、labels.csv 非法、指标/主指标非法、传入不属于本接口的字段（threshold / model_names / report_format / format）、预测结果与模型版本不一致、`predicted_label` 与 `decision_threshold` 不一致 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 预测结果或输出批次不存在、重试时输入已不可用 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 输入来源：系统已保存的预测结果（`predict_batch` 成功任务），底层为 predictions Excel；一次评估固定单一模型、单一测试集。
- `predicted_label` 与 `decision_threshold` 来自预测结果，MUST 非空且互相一致；评估不重新判定标签。
- effort 来源：train_testset 或 clean_dataset schema，用于 effort-aware 指标；缺省时只算 unaware。
- `labels.csv` 不是有效输入；真值只能随 predictions 透传。

## 4. 输出契约

- 指标值来自 `metrics.py` 单源公式；退化场景（空集/单类）置 null 并给警告，不编造 0。
- 指标表为用户可见 CSV / Excel；图按后端标准命名打包为 zip，逐图登记 `model_figure` 并按 `job_id` 可追溯。
- 内部指标长表与混淆矩阵不进入结果文件区；用户只看到图集 zip 与指标表。
- 报告与图只覆盖本次运行，不随配置变化自动重算。

## 5. 可配置项

`metrics_selected`、`primary_metric`、`effort_enabled` 来自配置中心；请求可覆盖指标、主指标与 effort。图集 zip 名称与指标表名称由用户在 05 步确认（有默认值）；`decision_threshold` 不由评估配置提供，始终沿用预测结果。

## 6. 状态持久化

- 任务 `kind=evaluate`，同步阈值 5000 行，`job.total = 行数 + 1`。
- 输入快照落 `temp/evaluate_inputs/<hash>/request.json`。
- `params_json` 记录 `prediction_job_id`、`metrics`、`primary_metric`、`effort_enabled`、`figure_zip_name`、`metrics_name`、`output_format`。
- 产物不可覆盖；成功写 `output_ref_json.outputs`（zip、指标表、逐图 PNG 与内部记录）与 `summary`；逐图同时登记到 `model_figure`，页面只展示 zip 与指标表。

## 7. 验收

- 默认指标集合下指标与历史 `model_metrics.csv` 逐值一致，阈值沿用预测结果，不单独配置。
- 单模型单测试集结果正确；传入 `threshold` / `model_names` 被拒绝。
- 缺真标签、非单模型单测试集、标签与阈值冲突被前置拒绝。
- effort 缺失时 unaware 指标正常、aware 指标标记 unavailable。
- 图集 zip 可下载、内含逐张标准命名图片；指标表可导出 CSV / Excel。
- 每张图登记到 `model_figure` 且可按 `job_id` 与 `model_name` 查询。

## 8. 边界

评估是独立工具，输入是已保存的预测结果文件而不是「某次训练的运行状态」；同一预测结果可反复评估，结果永远对应显式运行，不产生隐式更新。
