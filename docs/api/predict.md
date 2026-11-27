# 模型预测 API（predict）

设计状态：目标契约。Web 页面只做训练产物上的批量预测；判定阈值默认 `0.5`；预测结果二维表必须写入 `prediction` 表；结果文件区只展示一个核心「预测结果」，XLSX 在下载时按需生成。

预测文件 schema 见训练测试集与模型文件契约、predictions 列契约；数据库落库见 [`../database/prediction.md`](../database/prediction.md)；功能点见 [`../function_point/predict.md`](../function_point/predict.md)；页面见 [`../web_page/predict.md`](../web_page/predict.md)。

## 1. 职责与不负责范围

- 负责单条预测与批量预测：输出风险分数、预测标签、风险等级、版本信息与失败原因。
- 负责把批量预测成功的全部结果行写入 `prediction` 表，并发布核心结果文件。
- Web 页面只使用训练阶段已保存的模型和训练成功产出的测试集；不提供手动上传、公开数据集或任意数据集入口。
- 不负责训练、特征工程实现、解释、定位、评估；不生成训练 / 测试切分。
- 不设默认模型：模型必须显式指定；判定阈值默认 `0.5`。

## 2. 端点契约

### POST /api/predict

单条预测，JSON body（`extra="forbid"`）。

| 字段 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 40 位十六进制 |
| `model_name` | 是 | 必须显式指定，无默认模型 |
| `decision_threshold` | 否 | `[0.05,0.95]`，默认 `0.5` |
| `force_recompute` | 否 | bool，默认 false |

响应 `data`：

```text
commit_hash, model_name, risk_score(5 位小数), predicted_label, decision_threshold,
risk_level(high|mid|low), model_version, feature_version,
result_source(stored|computed), stale, predicted_at, features(expert 14 维 / semantic 768 维), summary
```

模型未加载返回 `40001`；库中无特征且无法现算返回 `40400`。

### POST /api/predict/run

`multipart/form-data`。

`config` JSON part（必填）：

| 字段 | 必填 | 契约 |
|---|---|---|
| `model_name` | 条件 | 已登记且可用模型；Web 页面必填并从模型下拉选择；API / CLI 与 `files[]` 模型文件二选一 |
| `testset_ref` | 条件 | 训练成功任务产出的 `train_testset` 引用；Web 页面必填 |
| `dataset_id` | 否 | API / CLI 兼容入口；Web 页面不使用 |
| `decision_threshold` | 否 | `[0.05,0.95]`，默认 `0.5` |
| `batch_size` | 否 | 正整数，默认按配置中心 |
| `force_recompute` | 否 | bool，默认 false |
| `output_name` | 否 | 预测结果 / 导出文件名称，允许中文，1–64 字符；禁止 `/ \ : * ? " < > \|`、控制字符，且不能以点开头或结尾；默认 `<model_name>_预测结果` |
| `save_to_db` | 否 | bool，默认 true；Web 页面固定 true，必须落库 |
| `format` | 否 | 已废弃；不再在任务配置中指定格式 |

文件 part（可选，仅 API / CLI）：

| part | 必填 | 契约 |
|---|---|---|
| `files[]` | 否 | 特征表、`predictions` 表或模型文件（`.pkl` / `.zip`），合计 ≤64MiB；Web 页面不上传 |

Web 页面提交时必须满足：

- `model_name` 来自已登记可用模型；
- `testset_ref` 来自 `kind=train` 且 `status=success` 的任务产物 `train_testset`；
- 模型特征线与测试集 schema 必须匹配；
- `save_to_db=true`，不可关闭。

响应：同步（≤2000 行）返回 `{job_id,status,outputs,summary,error_log}`；异步返回 `{job_id,status}`。

`summary`：

```text
input_rows, success_count, failed_count, model_name, model_version, feature_version,
decision_threshold, output_name, saved_rows, failed_samples[≤100]
```

### GET /api/predict/preview/{job_id}

成功批量任务提供分页预览；优先读 `prediction` 表，缺失时回退核心 CSV。

| 参数 | 必填 | 契约 |
|---|---|---|
| `page` | 否 | 页码，默认 1 |
| `size` | 否 | 每页行数，默认 20，范围 1–100 |

响应：

```json
{
  "columns": [],
  "preview": [],
  "total": 0,
  "page": 1,
  "size": 20
}
```

约束：

- 数据来自 `prediction` 表中该 `job_id` 的结果行；无 `job_id` 时兼容从核心 CSV 读取。
- 列严格采用 predictions 列契约全部列，不展示 `features` 等内部特征列。
- 支持分页浏览全量预测结果。
- preview 模式不存在；预测任务成功后即可预览。

### GET /api/predict/outputs/{job_id}/{name}

下载核心预测结果文件。

| 参数 | 必填 | 契约 |
|---|---|---|
| `name` | 是 | 必须为核心产物名，禁止路径分隔符与 `..` |
| `format` | 否 | `csv`（默认）/ `xlsx`；只影响本次下载响应 |

- `format=csv`：直接返回规范主表 `predict_predictions_<job_id>.csv` 或 `<output_name>.csv`。
- `format=xlsx`：从同一 CSV 即时生成单 sheet XLSX 并返回；不写入产物目录、不登记为新产物。
- 响应 `Content-Disposition` 文件名为 `<output_name>_<job_id>.<ext>`，对 `output_name` 做安全清洗。
- `predict_summary`、manifest、failed_samples 属于内部记录，不作为结果文件下载项。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 参数非法、阈值越界、batch_size 非正、输出名非法、模型未加载、模型与测试集特征线不匹配、数据库保存失败 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | commit / 特征 / 模型 / 训练测试集 / 输出批次不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 单条预测：`commit_hash` + `model_name`，可选阈值与 `force_recompute`。
- Web 批量预测：已登记模型 + 训练成功任务产出的 `train_testset`，不允许任意数据集和手动上传。
- API / CLI 批量预测：仍可上传特征表（collected_commits 列契约 / clean_dataset 列契约 列）或 `predictions` 表（predictions 列契约），保持模块独立运行能力。
- 特征维度由模型线决定：expert 14 维、semantic 768 维；不一致返回 `40001`。
- `train_testset` 每行真标签必须非空；预测结果必须透传 `is_bug_inducing`。

## 4. 输出契约

### 4.1 核心结果文件

用户可见核心产物只有一份：

```text
predict_predictions_<job_id>.csv
```

填写 `output_name` 时：

```text
<output_name>.csv
```

列严格采用 predictions 列契约：

```text
commit_hash, model_name, risk_score, predicted_label, decision_threshold,
model_version, feature_version, predicted_at, is_bug_inducing
```

不输出：

```text
features
raw_feature_vector
explanation
localization
```

CSV 使用 UTF-8 BOM；XLSX 只在下载时按需生成。

### 4.2 判定与风险等级

- `predicted_label = risk_score >= decision_threshold`，输出 1 / 0。
- `risk_level` 由配置 `risk_high_threshold` / `risk_mid_threshold` 判定。
- 阈值变化只改变 `predicted_label`，不改变 `risk_score`。
- 判定阈值默认 `0.5`；Web 页面仅在 `02` 用滑杆调整，不展示说明文字。

### 4.3 内部记录

```text
predict_summary_<job_id>.json
<stem>.manifest.json
```

内部记录不进入结果文件区，不提供页面下载入口。

### 4.4 数据库保存

批量预测成功后 MUST 把全部成功行写入 `prediction` 表：

- 落库列与 predictions 列契约对齐；
- 以 `(commit_hash, model_name)` 幂等 upsert；
- 同提交同模型重复预测时更新最新 `risk_score`、`decision_threshold`、`predicted_label`、`model_version`、`feature_version`、`predicted_at`、`is_bug_inducing` 与 `job_id`；
- `summary.saved_rows` 记录本次入库行数；
- 数据库保存失败时任务失败，文件产物保留，可重试；
- 失败行不入库，仅进入 `failed_samples`（≤100）。

## 5. 可配置项

- `batch_size`、`risk_high_threshold`、`risk_mid_threshold` 来自配置中心。
- `decision_threshold` 页面默认 `0.5`，本次运行显式传入并写入 summary / DB。
- 模型每次显式选择，不设默认模型。

## 6. 状态持久化

- 批量任务 `kind=predict_batch`，同步阈值 2000 行，`job.total = 行数 + 1`。
- 进度文案按逐条提交计数：“已完成 X / Y 条提交”；发布产物前补一次收尾进度。
- `params_json` 记录 `model_name`、`testset_ref`、`decision_threshold`、`output_name`、`save_to_db`、`batch_size`。
- `output_ref_json.outputs` 登记本批次全部产物（核心 CSV、summary、manifest）；页面结果文件区只展示核心 CSV。
- 输入快照落 `temp/predict_inputs/<hash>/request.json`，重试校验 checksum。
- 单条预测与批量预测都写 `prediction` 表。

## 7. 验收

- Web 页面只能选择训练阶段产出的 `train_testset`，不能选择任意数据集或手动上传。
- 模型与测试集特征线 / schema 不匹配时拒绝运行。
- 判定阈值默认 `0.5`，范围 `[0.05,0.95]`。
- `risk_score >= threshold` 生成 `predicted_label`；阈值变化不改 `risk_score`。
- 批量预测成功后，`prediction` 表保存全部成功行的 predictions 列契约二维表。
- 数据库保存失败时任务失败且可重试，文件产物保留。
- 分页预览返回 predictions 列契约全部列，不返回内部特征列。
- 结果文件区只有一个逻辑文件；下载 CSV 直接返回规范主表，下载 Excel 按需生成且不落盘。
- 单条与批量同模型、同阈值、同特征结果一致。
- 模型版本或特征版本变化后 `stale=true`。

## 8. 边界

预测是独立工具：文件与模型齐备即可运行，不要求库里有提交、清洗或训练记录；Web 页面则固定使用训练产物，便于页面验收与结果回溯。评估、解释、定位不在本模块完成。



