# 缺陷数据收集 API（collect）

实现状态：目标契约　期次：一期

> 旧接口口径包含 14 维特征、70/30 切分和“可选导入库”；本文已废止。新接口只负责收集 Git 仓库或导入公开标注数据集，产出带标签二维表，默认保存数据库，并提供预览和下载。本轮只修改设计文档。

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.9；公共鉴权、包络和任务口径见 [README.md](README.md)。

## 1 职责与不负责范围

- 负责 Git 仓库拉取/读取、提交采集、SZZ 打标，或公开标注数据集导入、字段映射、标签归一化和质量校验。
- 负责生成 `collected_commits.csv/xlsx`、summary、manifest 和公开数据集质量报告。
- 负责默认保存数据集到 `dataset` / `dataset_commit`。
- 不负责 14 维特征、训练/测试切分、清洗、训练、预测、评估、解释、定位和修复。
- 不把数据库或环境变量中的固定仓库当作运行前提。

## 2 端点契约

### POST /api/collect/run

`multipart/form-data`。请求包含 `config` JSON part，公开数据集或提交清单可放 `files[]`。

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

创建 `job.kind=collect`。同 kind 同时最多一个 running，冲突返回 40001。

#### 2.1 `config` 公共字段

| 字段 | 必填 | 类型 | 契约 |
|---|---|---|---|
| `source_type` | 是 | string | `git_repo` / `public_dataset` |
| `dataset_name` | 是 | string | 数据集显示名 |
| `save_to_db` | 否 | bool | 默认 `true` |
| `format` | 否 | string | `csv` / `xlsx`，默认 `csv`；API 可同批交付双格式 |

#### 2.2 Git 仓库模式 `source_type=git_repo`

| 字段 | 必填 | 类型 | 契约 |
|---|---|---|---|
| `repo_source` | 是 | string | 本地路径须在允许根目录内；URL 协议须在白名单内 |
| `branch` | 否 | string | 分支/ref，默认 HEAD |
| `start_time` / `end_time` | 否 | datetime | ISO 8601 UTC 闭区间 |
| `start_commit` / `end_commit` | 否 | string(40 hex) | 可检出提交范围 |
| `mode` | 否 | string | `full` / `incremental`，默认 `incremental` |
| `fetch_remote` | 否 | bool | 默认 `true` |
| `head_expect` | 否 | string(40 hex) | HEAD 不符则拒绝 |
| `dedup` | 否 | string | 当前仅 `commit_hash` |
| `szz_method` | 否 | string | `szz_v1` / `szz_lite`，默认 `szz_v1` |
| `commit_list` | 否 | file | 仅含 `commit_hash` 的 CSV/XLSX，用于圈定范围 |

Git 模式禁止传入 `split_ratio`、`feature_version`、`is_test` 等字段；收到即返回 40001。

#### 2.3 公开数据集模式 `source_type=public_dataset`

| 字段 | 必填 | 类型 | 契约 |
|---|---|---|---|
| `source_url` | 否 | string | 与上传文件二选一；URL 协议须在白名单内 |
| `license` | 是 | string | SPDX 或原始许可证说明 |
| `source_note` | 是 | string | 论文、项目主页、下载地址等来源说明 |
| `field_mapping` | 是 | object | `commit_hash`、`committed_at`、`is_bug_inducing` 的源字段映射 |
| `label_mapping` | 是 | object | 原始标签值到 `1/0/null` 的映射 |
| `dataset_format` | 否 | string | `csv` / `json` / `zip`，按上传文件自动识别时可省略 |
| `files[]` | 否 | file | CSV/JSON/ZIP 数据集文件；与 `source_url` 二选一 |

`field_mapping` 示例：

```json
{
  "commit_hash": "sha",
  "committed_at": "date",
  "is_bug_inducing": "bug"
}
```

`label_mapping` 示例：

```json
{
  "1": 1,
  "true": 1,
  "bug": 1,
  "0": 0,
  "false": 0,
  "clean": 0
}
```

公开数据集模式不执行 SZZ；标签来源记为 `public_dataset`。

### GET /api/collect/preview/{job_id}

返回 `{columns, preview}`。

- `columns` 必须与 file-contracts §3.1 逐字一致。
- `preview` 最多前 20 行。
- 未打标字段返回 `null`。
- 只允许预览已登记、checksum 校验通过的 CSV。

### GET /api/collect/outputs/{job_id}/{name}

下载本次任务登记的产物文件。

允许的基础名称：

```text
collected_commits_<job_id>.csv
collected_commits_<job_id>.xlsx
collect_summary_<job_id>.json
collect_quality_<job_id>.json
collect_quality_<job_id>.md
collected_commits_<job_id>.manifest.json
```

`name` 必须出现在 manifest `outputs[]`，禁止路径分隔符和 `..`。

### POST /api/collect/resave/{job_id}

当文件已生成但数据库保存失败时，用已保留产物重新写入 `dataset` 和 `dataset_commit`。

- 成功返回 `{job_id, dataset_id, status:"success"}`。
- 输入产物 checksum 不符返回 40001。
- 不重新执行仓库拉取或 SZZ。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 参数、路径、协议、HEAD、字段映射、标签映射、文件格式、同 kind 冲突 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括下载 |
| 40400 | 404 | job 或登记输出不存在 |
| 50000 | 500 | 未预期服务错误；运行期失败写脱敏 error_log |

## 3 输出契约

### 3.1 二维表

`collected_commits_<job_id>.csv/xlsx`，字段严格遵循 file-contracts §3.1。

关键约束：

- 不含 Kamei 14 维。
- 不含 `is_test`。
- `is_bug_inducing` 未打标保持空。
- `label_source` 必填：`git_szz` / `public_dataset`。
- `source_type` 必填：`git_repo` / `public_dataset`。

### 3.2 统计信息

`collect_summary_<job_id>.json` 至少包含：

```text
source_type, source_url, dataset_name, label_source,
total_rows, positive_rows, negative_rows, unlabeled_rows,
duplicate_rows, skipped_rows, save_db_status, dataset_id
```

Git 模式额外含 `repo`、`branch`、`head_hash`、`time_start`、`time_end`、`szz_method`。

公开数据集模式额外含 `license`、`source_note`、`field_mapping`、`label_mapping`。

### 3.3 质量报告

公开数据集模式必产：

```text
collect_quality_<job_id>.json
collect_quality_<job_id>.md
```

内容见 function_point/collect.md §4.3。

### 3.4 manifest

主产物同名 manifest，遵循 file-contracts §3.9，并记录：

```text
source_type, label_source, license, source_url,
save_db_status, dataset_id
```

## 4 数据库保存语义

- `save_to_db=true` 时，文件生成后写入 `dataset` 和 `dataset_commit`。
- 成功后响应或 job 的 `output_ref_json` 必须含 `dataset_id`。
- 文件生成成功但保存失败：
  - job 状态为 `failed`；
  - `error_log` 写明保存失败原因；
  - 文件产物仍可下载；
  - 可调用 `POST /api/collect/resave/{job_id}`。
- `save_to_db=false` 时，job 成功仅表示文件交付成功，数据集列表不新增记录。

## 5 可配置项

- `collect.allow_roots`：本地仓库和公开数据文件允许根目录。
- `collect.protocol_whitelist`：允许的 URL 协议。
- `default_dataset`：仅作展示和便利选择，不是运行前提。
- 单次运行配置：来源类型、仓库/数据集来源、范围、SZZ 方法、字段映射、标签映射、保存开关、输出格式。
- 所有单次配置完整写入 `job.params_json` 与 manifest；凭证不得写入。

## 6 状态持久化

- `job.kind=collect`，五态 `queued / running / success / failed / cancelled`。
- 阶段：拉取/导入、采集/映射、SZZ 或标签归一化、生成二维表、保存数据库、生成导出文件。
- 同 kind 互斥；重启遗留 running 置 failed；失败可重试，运行中可取消。
- 输出落 `backend/var/outputs/<job_id>/`。
- 保存数据库失败不删除文件产物。

## 7 验收

- Git 仓库模式：本地仓库或合法 URL 可产出 §3.1 二维表、summary、manifest；未打标为空；无 14 维和 `is_test`。
- 公开数据集模式：通过字段/标签映射产出同 schema 二维表；不执行 SZZ；质量报告与 manifest 完整。
- 默认保存数据库成功时，`GET /api/datasets` 可查询到新数据集。
- 保存失败时文件仍可下载，`resave` 可恢复入库。
- CSV/XLSX 中文不乱码，checksum 与 manifest 一致。
- 非法路径、协议、字段映射、标签映射、HEAD、文件格式均返回 40001 且不产半成品。
