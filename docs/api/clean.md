# 数据清洗与预处理 API（clean）

collected_commits 列契约、clean_dataset 列契约、manifest 契约；页面设计见 [`../web_page/clean.md`](../web_page/clean.md)。

## 1 职责与不负责范围

- 负责操作注册表、处理链校验、preview/apply、每步数据变化统计、关键特征变化图与清洗后数据集文件交付。
- Web 页面输入为「数据收集保存的数据集」：`GET /api/datasets` 筛选 `status=ready`、schema 符合 `collected_commits`、来源为 Git 仓库收集结果的数据集后，传 `dataset_id` 给清洗任务。
- API / CLI 仍可上传 `collected_commits.csv` 主表与同名 manifest，保持模块独立运行能力。
- 不执行 SZZ、D5、Git 拉取；不生成 `is_test`、不做训练/测试切分。
- 不生成或选择模型特征；Kamei 14 维、语义向量、融合特征、端到端文本特征归训练阶段，训练侧变换（`log_transform` / `standardize` / `categorical_encode` / `feature_select`）不在本模块。
- 不训练模型、不评估、不解释、不定位；不写 `dataset` / `dataset_commit`，自动入库走 storage。

## 2 端点契约

### GET /api/clean/operations

无请求参数。响应 `data.operations[]` 与 `data.features[]`。

每个操作包含：

```text
op
group = clean | preprocess        # clean=常用清洗操作；preprocess=预处理操作
name
description
input_schema
output_schema
params_schema[]
order_constraints[]
supports_preview
default_enabled
```

`group=clean` 渲染为页面的“常用清洗操作”，`group=preprocess` 渲染为“预处理操作”。操作名与参数标签必须由前端中文化后展示，不暴露 `op` 与参数 key。

常用操作：

```text
常用清洗操作：
schema_validate
duplicate_drop
merge_commit_filter
missing_value_handle
invalid_time_filter
unlabeled_handle
outlier_filter
label_validate
text_clean

预处理操作：
type_convert
date_normalize
text_normalize
category_normalize
derive_basic_fields
```

### POST /api/clean/run

`multipart/form-data`。

`config` JSON part（必填）：

| 字段 | 必填 | 契约 |
|---|---|---|
| `mode` | 是 | `preview` / `apply`；Web 页面固定 `apply`，API / CLI 可继续使用 `preview` |
| `steps[]` | 是 | 有序数组：`{op, enabled, params}`；`schema_validate` 必须首项且启用 |
| `output_name` | 否 | 数据集 / 导出文件名称，1–64 字符，允许中文；禁止 `/ \ : * ? " < > \|`、控制字符，且不能以点开头或结尾；不填时沿用 `clean_dataset_<job_id>` |
| `dataset_id` | 否 | 数据收集保存的数据集 id；Web 页面必传；与上传文件二选一 |
| `template` | 否 | 处理链模板名，需已存在于 `user_config` 的 `clean.chain_templates`；命中后与显式 `steps` 合并，显式字段优先 |

`format` 不属于运行配置；清洗任务只落规范 CSV，XLSX 在下载端点按 `format=xlsx` 即时生成。`chart_columns` 不属于接口字段；后端只在 `steps_stats` 中记录前后差异，不生成 PNG 变化图。

文件 part（可选，最多 2 个）：

| part | 必填 | 说明 |
|---|---|---|
| `files[]` | 否 | `collected_commits.csv` 主表；与 `dataset_id` 二选一 |
| `files[]` | 否 | 与主表同名的 `.manifest.json`，提供时校验 checksum 与来源 |

禁止字段（出现即 `40001`）：

```text
repo_source
feature_file
feature_set
feature_plan
feature_build
feature_align
log_transform
standardize
categorical_encode
feature_select
split_ratio
seed
is_test
```

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "j-123",
    "status": "queued"
  }
}
```

小表（≤ 同步阈值）同步执行，直接返回终态并附带 `mode`、`outputs`、`summary`、`error_log`；大表走异步 job，只返回 `job_id` 与 `status`。同 kind 同时最多一个 running。

### GET /api/clean/preview/{job_id}

仅成功 apply 任务提供清洗后主表分页预览。

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

- 支持分页浏览全量清洗后数据；单页默认 20 行。
- 展示全部列，前端表格内部横向滚动，不压缩列。
- 空标签返回 `null`；预览文件按任务登记的 `.csv` 产物定位，兼容自定义 `output_name`。
- preview 模式没有清洗后主表，返回 `40001`。

### GET /api/clean/outputs/{job_id}/{name}

下载清洗后核心数据集。`name` 必须出现在 manifest `outputs[]` 的核心主表条目中，禁止路径分隔符与 `..`。

| 参数 | 必填 | 契约 |
|---|---|---|
| `format` | 否 | `csv`（默认）/ `xlsx`；只影响本次下载响应 |

- `format=csv`：直接返回规范主表 `clean_dataset_<job_id>.csv` 或 `<output_name>.csv`。
- `format=xlsx`：从同一规范 CSV 即时生成单 sheet XLSX 并返回；不写入产物目录、不登记为新产物。
- 响应 `Content-Disposition` 文件名为 `<output_name>_<job_id>.<ext>`；`output_name` 必须做文件名安全清洗。
- `clean_steps_stats`、manifest 属于内部记录，不作为结果文件下载项；结果区从 `steps_stats` 读取前后差异。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知操作、顺序冲突、禁止字段、非法 schema、公式注入、文件名非法、`format` 非法 |
| 40100 | 401 | 缺失或错误 `X-API-Key` |
| 40400 | 404 | job 或输出不存在、清洗模板不存在 |
| 50000 | 500 | 未预期异常；运行期失败写脱敏日志 |

## 3 输入契约

主表列严格引用 collected_commits 列契约：

```text
commit_hash, repo_name, repo_url, author_name, author_email,
committed_at, message, parent_hash,
is_bug_inducing, label_method, label_source,
labeled_at, fix_commit_hash, source_type
```

校验：

- `commit_hash` 40 位小写 hex。
- `is_bug_inducing` 只能 1 / 0 / 空。
- `label_source` 只能 `git_szz` / `public_dataset`。
- CSV UTF-8/UTF-8 BOM；上传 XLSX 单 sheet。
- 不允许公式注入单元格。
- 不要求 14 维特征列。
- 不允许 `is_test` 列进入；若输入包含 `is_test`，忽略并在 manifest 记录来源警告。

`dataset_id` 输入时，后端按数据集成员生成规范 CSV，再走同一解析与校验流程。Web 页面只传数据收集保存的数据集 id。

## 4 处理链约束

- `schema_validate` 必须第一步且不可关闭。
- 清洗操作必须先于通用预处理操作。
- `date_normalize` 必须先于任何基于时间的基础派生。
- `derive_basic_fields` 只能派生基础列，不得生成模型特征。
- 不允许 SZZ、D5、时间切分、模型特征生成或训练侧变换作为本模块操作。
- 页面不提供对比图配置；后端只记录每步前后差异与字段级变化，不生成 PNG 变化图。

## 5 输出契约

### 5.1 清洗后数据集

用户可见核心产物只有一份：

```text
clean_dataset_<job_id>.csv
```

填写 `output_name` 时：

```text
<output_name>.csv
```

- 保留 collected_commits 列契约 原始列，按清洗结果更新。
- 可追加 `derive_basic_fields` 生成的基础列：`message_length`、`parent_count`、`commit_hour`。
- 不生成 Kamei 14 维、语义向量、融合特征或模型输入特征。
- 不写 `is_test`，不写任何训练/测试标记。
- CSV UTF-8 BOM；XLSX 只在下载时按需生成，不预生成、不登记。

### 5.2 每步统计

内部记录：

```text
clean_steps_stats_<job_id>.json   # 或 <名称>_steps_stats.json
```

数组元素字段：

```text
step
enabled
rows_before
rows_after
removed_rows
modified_rows
modified_samples[]          # {commit_hash, changes{field: {before, after}}}
label_dist_before / label_dist_after   # {positive, negative, null}
missing_before / missing_after
duplicate_before / duplicate_after
elapsed_ms
excluded_samples[]
warnings[]
```

### 5.3 前后差异展示

Web 页面不传 `chart_columns`，API / CLI 同样不接受该字段。后端在 `clean_steps_stats` 中记录每步的行数、删除行数、修改行数、标签分布、缺失与重复变化，以及 `modified_samples[]` 的字段级前后值；页面据此渲染差异表，不生成 PNG 变化图。

### 5.4 manifest

由 `output_store` 统一生成，产物必伴同名 manifest 并登记 checksum：

```text
schema_version
module
job_id
inputs[]        # name / sha256 / rows
config          # 归一化后的处理链配置（含 output_name）
outputs[]       # 本批次全部产物：核心 CSV / steps_stats / manifest
code_version
created_at
```

manifest 与主产物同茎：未填名称时为 `clean_dataset_<job_id>.manifest.json`，填了名称为 `<名称>.manifest.json`。

任务 `output_ref_json` 另带 `mode`、`summary`、`columns`、`manifest_name`，供 jobs 接口与页面读取；`outputs` 中含统计、图与 manifest，页面结果文件区只展示核心 CSV：

```text
summary = {input_rows, output_rows, label_dist, enabled_steps, warnings}
```

训练页的时间切分滑杆依赖本产物登记提交时间范围与分布，目标契约追加：

```text
summary.time_range = {min, max}          # 最早、最晚提交时间（UTC）
summary.time_bins  = [{start, end, count}]  # 时间分桶与样本数，供滑杆实时计算两侧比例
```

这两项为清洗 summary 的必备字段；缺失时训练页时间滑杆不可用并退回手填边界，不影响比例切分。

### 5.5 自动入库

清洗成功后自动登记数据集：内部自动调用 `POST /api/storage/import`，把核心 CSV 与 manifest 登记为数据集，名称使用 `output_name`；页面不提供文件导入入口。该链路不属于 clean API 的契约，失败不影响结果文件下载；失败时页面提供手动重存入口。

## 6 状态持久化

- `job.kind=clean`，五态（queued / running / success / failed / cancelled）。
- 任务记录模式、处理链、默认变化图策略、输入输出引用、内部记录引用与错误日志。
- `output_ref_json.outputs` 登记本批次全部产物（核心 CSV、统计、图、manifest）；页面只展示核心 CSV。
- preview 不产主表；apply 才产清洗后数据集。
- 输出落 `temp/outputs/<job_id>/`，批次不可覆盖。
- 相同输入、相同配置下，主表与前后差异统计一致；`elapsed_ms`、执行时间和 `job_id` 不作为跨运行一致项。

## 7 验收

- Web 页面只传 `dataset_id`、`mode=apply`、`steps[]`、`output_name`；不传 `chart_columns` 与 `format`，API / CLI 同样不接受 `chart_columns`。
- 前端用 `steps_stats` 展示每步前后差异与字段级变化，不生成 PNG 变化图。
- 分页预览可浏览全量清洗后数据，默认每页 12 行，展示所有列。
- apply 只落一份规范 CSV；下载 CSV 直接返回该文件，下载 Excel 按请求即时生成且不落盘。
- 结果文件区只有一个「清洗后数据集」逻辑文件；内部记录不展示、不作为下载项。
- CSV UTF-8 BOM、XLSX 单 sheet、中文不乱码；中文 `output_name` 可下载。
- 操作注册表 `group=clean` / `group=preprocess` 分组正确，顺序约束可校验。
- 无 `szz_label`、`d5_exclude`、`time_split`、`feature_build`、模型特征选择。
- 输出不含 `is_test` 和模型特征集；未打标保持空值。
- 缺列、错类型、公式注入、未知操作、顺序冲突、禁止字段、非法 `output_name` 均返回 `40001`。
- CLI 与 API 同参数等价（CLI 额外支持 `--output-name` 与 `--chart-columns`）。

