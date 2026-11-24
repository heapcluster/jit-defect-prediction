# 数据清洗与预处理（功能 3）

实现状态：目标契约　期次：一期

> 旧实现中存在 `szz_label`、`d5_exclude`、`time_split`、`is_test`、`feature_build`、Kamei 14 维默认图和训练侧变换；本文已废止。本轮只修改设计文档，代码后续按本文同步。

## 一句话概述

独立的数据清洗与预处理工具：上传板块 2 产出的 `collected_commits.csv/xlsx`，按用户选择的常用清洗操作和通用预处理操作生成清洗后数据集；每一步展示数据集变化和指定列/基础特征变化，结果可导出 CSV/XLSX。

## 1 职责与不负责范围

**负责**：

- 提供分组操作注册表：常用清洗操作、通用预处理操作。
- 支持用户选择、排序、启停、配置每个操作。
- 支持 `preview` / `apply` 两种模式：
  - `preview` 只产出每步统计和图表。
  - `apply` 额外产出清洗后数据集。
- 对每一步记录处理前后行数、删除/修改行数、标签分布、缺失值、重复数和排除原因。
- 对用户指定列/基础特征展示处理前后分布变化；若没有指定列，则至少展示数据集级变化。
- 产出 `clean_dataset_<job_id>.csv/xlsx`、统计、图表、manifest。
- 保证同输入、同处理链、同配置可复现。

**不负责**：

- Git 拉取、SZZ 打标、D5 回溯与修复候选判定。
- 训练/测试集切分、`is_test` 生成。
- Kamei 14 维、语义向量、融合特征、端到端文本特征等**模型特征**的生成、选择或锁定。
- 训练侧 `log_transform` / `standardize` / `categorical_encode` / `feature_select`。
- 模型训练、预测、评估、解释、定位。
- 把数据库或页面作为运行前提。
- 把清洗结果强制写入数据库。

模型特征与训练侧变换统一属于板块 4「模型训练」。

## 2 独立运行入口

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python -m preparation.clean run --input collected_commits.csv --chain chain.json --mode apply --out ./out` | 文件与处理链即可运行 |
| CLI | `python -m preparation.clean operations` | 查询操作注册表 |
| 注册表 API | `GET /api/clean/operations` | 返回清洗/通用预处理操作元数据 |
| 任务 API | `POST /api/clean/run` | multipart 上传 CSV/XLSX + `config`，返回 `job_id` |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 五态、进度、日志 |
| 预览 | `GET /api/clean/preview/{job_id}` | 仅 apply 成功后返回清洗后数据集前 20 行 |
| 下载 | `GET /api/clean/outputs/{job_id}/{name}` | 下载清洗后数据集、统计、图、manifest |

CLI 与 API 调用同一处理链实现。

## 3 输入契约

主输入是 [`../file-contracts.md`](../file-contracts.md) §3.1 的：

```text
collected_commits_<job_id>.csv / xlsx
```

可用列：

```text
commit_hash, repo_name, repo_url, author_name, author_email,
committed_at, message, parent_hash,
is_bug_inducing, label_method, label_source,
labeled_at, fix_commit_hash, source_type
```

可选输入只有同名 manifest，用于校验 checksum 与来源信息。

本模块不再接受：

```text
repo_source
feature_file
feature_plan
feature_set
```

这些字段若出现，返回 40001，并提示“模型特征配置请在训练阶段提供”。

输入约束：

- 文件名不再假定为 `commits.csv`。
- 不要求输入已有 Kamei 14 维。
- 不要求输入已有 `is_test`。
- 未打标 `is_bug_inducing` 必须保持空值。
- CSV 使用 UTF-8/UTF-8 BOM；XLSX 单 sheet；表头为 snake_case。

## 4 操作注册表

操作注册表必须由后端提供，前端不得硬编码。

### 4.1 常用清洗操作

| 操作 | 职责 | 默认参数 / 约束 |
|---|---|---|
| `schema_validate` | 校验列、类型、哈希格式、时间格式、标签值域 | 始终先执行，不可关闭 |
| `duplicate_drop` | 按 `commit_hash` 去重 | 默认保留首行，重复样本写入排除明细 |
| `merge_commit_filter` | 根据 `parent_hash` 中多个有效父哈希过滤合并提交 | 不从 message 猜测 |
| `missing_value_handle` | 处理作者、邮箱、时间、消息等缺失值 | 策略：`keep` / `fill` / `exclude`，默认 `keep` |
| `invalid_time_filter` | 过滤非法时间或超出范围的时间 | 默认排除非法时间 |
| `unlabeled_handle` | 处理未打标样本 | 策略：`keep` / `exclude` / `warn`，默认 `keep` |
| `outlier_filter` | 对已有数值列做异常检测 | 方法 `iqr` / `zscore`，默认 `iqr`；不生成模型特征 |
| `label_validate` | 校验标签只能是 1 / 0 / 空 | 默认开启；NULL 不填 0 |
| `text_clean` | 清洗 `message` 文本 | 去首尾空白、控制字符、多余换行 |

### 4.2 通用预处理操作

| 操作 | 职责 | 默认参数 / 约束 |
|---|---|---|
| `type_convert` | 把字符串时间/数字转为统一类型 | 由用户指定列；不产生模型特征集 |
| `date_normalize` | 统一时间为 UTC ISO 8601 | 作用于 `committed_at` / `labeled_at` |
| `text_normalize` | 统一文本空白和换行 | 作用于 `message` 等文本列 |
| `category_normalize` | 统一类别值写法，如大小写和空白 | 不做模型编码，只做值规范化 |
| `derive_basic_fields` | 派生基础展示列，如 `message_length`、`parent_count`、`commit_hour` | 默认关闭；不得生成 Kamei 14 维、语义向量或模型输入特征 |

`derive_basic_fields` 只是数据查看和变化图用的基础列，不是模型特征工程。模型训练需要哪些特征，由板块 4 决定。

### 4.3 已移除操作

以下操作不再属于板块 3：

| 旧操作 | 现归属 |
|---|---|
| `szz_label` | 板块 2，SZZ 打标 |
| `d5_exclude` | 板块 2，SZZ 质量控制 |
| `time_split` | 板块 4，训练配置 |
| `feature_build` | 板块 4，训练时按模型线生成模型特征 |
| `feature_align` | 板块 4，训练时锁定特征列 |
| `log_transform` | 板块 4，训练侧预处理 |
| `standardize` | 板块 4，训练侧预处理 |
| `categorical_encode` | 板块 4，训练侧预处理 |
| `feature_select` | 板块 4，训练时选择模型特征 |

### 4.4 顺序约束

- `schema_validate` 必须第一步。
- 清洗操作必须先于通用预处理操作。
- `date_normalize` 必须先于任何基于时间的基础派生。
- `derive_basic_fields` 只能派生基础列，不得生成模型特征。
- 不允许任何训练测试切分或模型特征选择操作。

## 5 输出契约

### 5.1 清洗后数据集

文件名：

```text
clean_dataset_<job_id>.csv
clean_dataset_<job_id>.xlsx
```

字段：

- 保留 §3.1 的原始列，按清洗结果更新。
- 可追加 `derive_basic_fields` 生成的基础列。
- 不生成 Kamei 14 维、语义向量、融合特征或模型输入特征。
- 不出现 `is_test`。
- 不出现训练/测试划分列。
- 未打标 `is_bug_inducing` 保持空。

导出要求：

- CSV 使用 UTF-8 BOM。
- XLSX 单 sheet。
- apply 模式才生成主表。
- preview 模式不生成主表。

### 5.2 每步数据集变化

```text
clean_steps_stats_<job_id>.json
```

每一步必须包含：

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

对应图：

```text
clean_dataset_change_<step>_<job_id>.png
```

图中至少展示：

- 行数前后对比。
- 标签分布前后对比。
- 缺失/重复变化。

### 5.3 指定列/基础特征变化

```text
clean_column_stats_<job_id>.json
clean_column_distribution_<step>_<column>_<job_id>.png
```

对每个指定列记录：

```text
mean
median
std
min
max
quantiles
missing_count
```

图表类型：

- 数值列：直方图、箱线图、密度图。
- 类别列：频数柱状图。

若没有指定列，数据集级图必须产出，列级图可为空并在 manifest 标记原因。

### 5.4 manifest

每个主产物同名 manifest，遵循 file-contracts §3.9，并记录：

```text
source_type = collected_commits
chain_config
chart_columns
derived_columns
column_schema
input_checksum
output_checksum
mode
```

不再记录 `feature_schema`；模型特征 schema 由板块 4 写入 `model_package.zip`。

## 6 可配置项

| 配置 | 来源 | 说明 |
|---|---|---|
| `clean.chain_templates` | `user_config` | 可复用处理链模板 |
| `steps[]` | 本次 run | 操作、启停、参数 |
| `chart_columns[]` | 本次 run | 需要画前后变化图的列/基础特征 |
| `mode` | 本次 run | `preview` / `apply` |
| `format` | 本次 run | `csv` / `xlsx` |

不再提供：

- `repo_source`
- `feature_file`
- `seed`
- `split_ratio`
- `feature_set`

## 7 状态持久化

- `job.kind=clean`，五态 `queued / running / success / failed / cancelled`。
- 任务保存模式、处理链、图表列、进度、错误日志、输入输出引用。
- preview 不产主表；apply 才产 `clean_dataset`。
- 输出落 `backend/var/outputs/<job_id>/`。
- 同输入、同链、同配置重跑，主表、统计和图表数值一致。
- 模板后续变化不影响历史任务，历史配置固化在 job 与 manifest。

## 8 与其他模块边界

- 与 collect 的关系仅为 §3.1 文件 schema 兼容。
- 不调用 collect 在线服务，不依赖数据库已有数据集。
- 不写 `dataset` / `dataset_commit`。
- 不重新执行 SZZ，不改变 `label_source`。
- train 后续消费本模块的 `clean_dataset` 文件，并在训练阶段选择模型特征、切分数据和拟合训练侧变换。
- storage 与本模块无关；清洗结果通过文件 handoff。

## 9 验收标准

- 空库且未运行 collect 时，CLI 和 API 均可仅凭上传的 `collected_commits.csv/xlsx` 完成 preview 与 apply。
- 操作注册表分组展示清洗/通用预处理操作，前端不硬编码。
- 用户可选择、排序、启停、配置操作；非法顺序、未知操作、参数越界前置拒绝。
- `feature_build` / 模型特征选择 / 训练测试切分请求被拒绝，并指向训练阶段。
- preview 产出每步数据集变化和指定列变化图，不产清洗后数据集。
- apply 额外产出 `clean_dataset_<job_id>.csv/xlsx`，支持 CSV/Excel 导出。
- 每一步都能看到行数、标签分布、缺失值、重复数和排除样本变化。
- 选择指定列后能看到该列处理前后分布图。
- 输出不含 `is_test`、训练/测试划分列和模型特征集。
- 未打标样本保持空值，不写 0。
- 相同输入和相同配置可复现。
- 输出 manifest、checksum、图表和统计文件完整。
