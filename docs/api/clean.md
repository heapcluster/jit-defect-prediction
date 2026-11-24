# 数据清洗与预处理 API（clean）

实现状态：目标契约　期次：一期

> 旧 API 口径包含 `commits.csv`、`szz_label`、`d5_exclude`、`time_split`、`is_test`、`feature_build`、Kamei 14 维模型特征；本文已废止。本轮只修改设计文档。

文件契约唯一权威：[`../file-contracts.md`](../file-contracts.md) §3.1、§3.2、§3.9；公共口径见 [README.md](README.md)。

## 1 职责与不负责范围

- 负责操作注册表、处理链校验、preview/apply、每步数据集变化统计、指定列变化统计、图表和清洗后数据集文件交付。
- 输入为板块 2 的 `collected_commits.csv/xlsx`。
- 不执行 SZZ、D5、Git 拉取。
- 不生成 `is_test`，不做训练/测试切分。
- 不生成或选择模型特征；Kamei 14 维、语义向量、融合特征、端到端文本特征均在训练阶段处理。
- 不做训练侧 `log_transform` / `standardize` / `categorical_encode` / `feature_select`。
- 不训练模型、不评估、不解释、不定位。
- 不要求数据库有上游数据；不写 `dataset` / `dataset_commit`。

## 2 端点契约

### GET /api/clean/operations

无请求参数。响应 `data.operations[]`，每个操作包含：

```text
op
group = cleaning | preprocessing
name
description
input_schema
output_schema
params_schema[]
order_constraints[]
supports_preview
```

一期操作：

清洗：

```text
schema_validate
duplicate_drop
merge_commit_filter
missing_value_handle
invalid_time_filter
unlabeled_handle
outlier_filter
label_validate
text_clean
```

通用预处理：

```text
type_convert
date_normalize
text_normalize
category_normalize
derive_basic_fields
```

### POST /api/clean/run

`multipart/form-data`。

文件：

| part | 必填 | 说明 |
|---|---|---|
| `files[]` | 是 | `collected_commits.csv/xlsx` |
| 同名 manifest | 否 | 提供时校验 checksum 与来源 |

`config` JSON part：

| 字段 | 必填 | 契约 |
|---|---|---|
| `mode` | 是 | `preview` / `apply` |
| `steps[]` | 是 | 有序数组：`{op,enabled,params}` |
| `chart_columns[]` | 否 | 需要前后变化图的列/基础特征；可为空 |
| `format` | 否 | `csv` / `xlsx`，默认 `csv` |

禁止字段：

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

收到禁止字段返回 40001，并提示模型特征与训练切分属于训练阶段。

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

小文件可同步完成；大文件走异步 job。同 kind 同时最多一个 running。

### GET /api/clean/preview/{job_id}

仅 apply 成功提供：

```json
{
  "columns": [],
  "preview": []
}
```

最多前 20 行；空标签返回 `null`。preview 模式没有主表，返回 40001。

### GET /api/clean/outputs/{job_id}/{name}

下载已登记产物。允许名称：

```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
clean_steps_stats_<job_id>.json
clean_column_stats_<job_id>.json
clean_dataset_change_<step>_<job_id>.png
clean_column_distribution_<step>_<column>_<job_id>.png
clean_dataset_<job_id>.manifest.json
```

`name` 必须出现在 manifest `outputs[]`，禁止路径分隔符和 `..`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知操作、顺序冲突、禁止字段、非法 schema、公式注入 |
| 40100 | 401 | 缺失或错误 `X-API-Key` |
| 40400 | 404 | job 或输出不存在 |
| 50000 | 500 | 未预期错误；运行期失败写脱敏日志 |

## 3 输入契约

主表严格引用 [`../file-contracts.md`](../file-contracts.md) §3.1：

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
- CSV UTF-8/UTF-8 BOM；XLSX 单 sheet。
- 不允许公式注入单元格。
- 不要求 14 维特征列。
- 不允许 `is_test` 列进入；若输入包含 `is_test`，忽略并在 manifest 记录来源警告。

## 4 处理链规则

- `schema_validate` 必须第一步且不可关闭。
- 清洗操作必须先于通用预处理操作。
- `date_normalize` 必须先于任何基于时间的基础派生。
- `derive_basic_fields` 只能派生基础列，不得生成模型特征。
- 不允许 SZZ、D5、时间切分、模型特征生成或训练侧变换作为本模块操作。

## 5 输出契约

### 5.1 清洗后数据集

apply 模式产出：

```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
```

列：

- 保留 §3.1 原始列，按清洗结果更新。
- 可追加 `derive_basic_fields` 生成的基础列。
- 不生成 Kamei 14 维、语义向量、融合特征或模型输入特征。
- 不写 `is_test`。
- 不写任何训练/测试标记。

### 5.2 每步统计

```text
clean_steps_stats_<job_id>.json
```

每步包含：

```text
step
rows_before
rows_after
removed_rows
modified_rows
label_dist_before
label_dist_after
missing_before
missing_after
duplicate_before
duplicate_after
elapsed_ms
excluded_samples
```

### 5.3 数据集变化图

```text
clean_dataset_change_<step>_<job_id>.png
```

展示行数、标签分布、缺失/重复变化。

### 5.4 指定列变化

```text
clean_column_stats_<job_id>.json
clean_column_distribution_<step>_<column>_<job_id>.png
```

`chart_columns[]` 为空时只产数据集级变化和 stats，不伪造列级图。

### 5.5 manifest

遵循 §3.9，并记录：

```text
mode
chain_config
chart_columns
derived_columns
column_schema
input_checksum
output_checksum
warnings
```

不记录 `feature_schema`；模型特征 schema 由训练阶段写入模型包。

## 6 状态持久化

- `job.kind=clean`，五态。
- 任务记录模式、处理链、图表列、输入输出引用、错误日志。
- preview 不产主表；apply 才产清洗后数据集。
- 输出落 `backend/var/outputs/<job_id>/`。
- 同输入、同配置主表、统计和图表数值一致。
- `elapsed_ms`、执行时间和 job_id 不作为跨运行一致项。

## 7 验收

- 上传标准 `collected_commits.csv`，preview 得到逐步统计和图表，无清洗后主表。
- apply 得到 `clean_dataset.csv/xlsx`、统计、图表、manifest。
- CSV UTF-8 BOM、XLSX 单 sheet、中文不乱码。
- 操作注册表分组正确，顺序约束可校验。
- 无 `szz_label`、`d5_exclude`、`time_split`、`feature_build`、模型特征选择。
- 输出不含 `is_test` 和模型特征集。
- 未打标保持空值。
- 指定列后有前后分布图；无列时有数据集变化图。
- 缺列、错类型、公式注入、未知操作、顺序冲突、禁止字段均返回 40001。
- CLI/API 同参数等价。
