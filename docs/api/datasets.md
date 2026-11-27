# 数据集查询与导出 API（datasets）

> 旧口径把数据集成员视为 commit + commit_feature + 14 维特征视图；本文按板块 2 新定义重写。数据集成员是带标签二维表，不含 14 维特征和 `is_test`。本轮只修改设计文档。

collected_commits 列契约、predictions 列契约、manifest 契约；收集与默认保存见 [collect.md](collect.md)。

## 1 职责与不负责范围

- 负责查询板块 2 默认保存的数据集元数据与二维表成员。
- 负责把数据集成员按 `collected_commits.csv` 规范表导出，并可导出已有 predictions 结果；CSV / XLSX 按下载请求即时生成，不预生成双份文件。
- 负责列表、详情、成员分页、统计展示和导出批次。
- 不触发采集、SZZ 打标、清洗、训练、预测、评估、解释或定位。
- 不创建新的标签、不补 14 维特征、不生成 `is_test`。

## 2 端点契约

### GET /api/datasets

参数：`page=1`、`size=20`（1≤size≤100）、`status`、`source_type`、`label_source`、`q`。

响应 `{total,page,size,items[]}`。每项字段：

```text
dataset_id,name,source_type,source_url,repo_name,branch,head_hash,
time_start,time_end,mode,label_source,szz_method,license,
sample_count,pos_count,neg_count,unlabeled_count,status,job_id,created_at
```

### GET /api/datasets/{dataset_id}

返回数据集详情，字段同列表项，另含：

```text
pos_rate,summary_path,manifest_path,quality_report_path
```

`pos_rate = pos_count / (pos_count + neg_count)`；未打标不计入分母。

### GET /api/datasets/{dataset_id}/commits

参数：`page`、`size`、`label=1|0|null|all`、`start_time`、`end_time`、`q`。

响应 `{total,page,size,items[]}`。成员字段：

```text
commit_hash,repo_name,repo_url,author_name,author_email,committed_at,
message,parent_hash,is_bug_inducing,label_method,label_source,
labeled_at,fix_commit_hash,source_type,row_no
```

不返回 Kamei 14 维特征、`is_test` 或特征开关。

### GET /api/datasets/{dataset_id}/export

按所选格式生成一次导出批次；同一请求只生成 `format` 指定的一份文件，不同时落 CSV 与 XLSX。

| 参数 | 必填 | 契约 |
|---|---|---|
| `format` | 否 | `csv` / `xlsx`，默认 `csv`；只影响本次导出 |
| `artifact` | 否 | `commits`（默认）/ `predictions` |
| `model_name` | predictions 时是 | 选择已有预测结果 |
| `label` | 否 | `1` / `0` / `null` / `all` |
| `start_time` / `end_time` | 否 | 提交时间闭区间 |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "j-456",
    "dataset_id": "...",
    "artifact": "commits",
    "format": "csv",
    "outputs": []
  }
}
```

`job_id` 仅为导出批次标识，不新增 job kind。

### GET /api/datasets/outputs/{job_id}/{name}

下载导出主表或 manifest。`name` 必须来自 manifest `outputs[]`，禁止路径穿越。

### DELETE /api/datasets/{dataset_id}

删除数据集登记：清除 `dataset_commit` 关联行并删除 `dataset` 行，不删除模块产物文件与产物批次。

响应：

```json
{"dataset_id": "...", "deleted": true}
```

数据集不存在返回 40400。该接口是数据集单删入口；`/storage` 产物库默认按数据链路整体删除（`DELETE /api/storage/chains/{chain_id}`），数据集被链路外任务引用时单删返回 40001。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 分页、筛选、时间、format、artifact 非法，下载名非法 |
| 40100 | 401 | 缺失或错误 `X-API-Key`，包括下载 |
| 40400 | 404 | dataset、模型、导出批次或输出不存在 |
| 50000 | 500 | 未预期读取或导出错误 |

## 3 输出契约

### 3.1 commits 导出

文件名按本次导出的 `format` 生成一份：

```text
datasets_commits_<job_id>.csv
datasets_commits_<job_id>.xlsx   # 仅 format=xlsx 时生成
```

列严格采用 `collected_commits` 列契约（字段定义见 [`../database/commit.md`](../database/commit.md)），即：

```text
commit_hash,repo_name,repo_url,author_name,author_email,committed_at,
message,parent_hash,is_bug_inducing,label_method,label_source,
labeled_at,fix_commit_hash,source_type
```

不出现：

```text
ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp,is_test
```

未打标导出为空；CSV 使用 UTF-8 BOM；XLSX 单 sheet。

### 3.2 predictions 导出

文件名按本次导出的 `format` 生成一份：

```text
datasets_predictions_<job_id>.csv
datasets_predictions_<job_id>.xlsx   # 仅 format=xlsx 时生成
```

列严格采用 predictions 列契约。`is_bug_inducing` 从 `dataset_commit` 透传，不从 `commit_feature` 读取。

### 3.3 manifest

导出主文件必伴同名 manifest，遵循 [`storage.md`](storage.md) 的 manifest 契约，并记录：

```text
dataset_id,artifact,format,filters,source_type,label_source
```

列表、详情和成员查询只返回 JSON，不创建文件。

## 4 可配置项

- `default_dataset`：选择器默认值，显式 id 优先；空库不影响独立运行。
- 查询分页、状态、来源类型、标签来源、标签值、时间关键字和导出格式可用。
- 页面页大小等偏好存 `page_prefs`，重启恢复。
- `.env` 仅提供出厂默认，不指定唯一可用数据集。

## 5 状态持久化

- `dataset` / `dataset_commit` 由 collect 默认保存写入，服务重启后查询一致。
- 归档只改变 `dataset.status`，不删除成员。
- export 同步执行，不新增 job kind；`job_id` 仅用于输出目录与下载。
- 查询和导出不修改收集结果、不补标签、不生成特征、不覆盖原数据集。

## 6 验收

- 数据集列表显示来源类型和标签来源；Git 与公开数据集均可查询。
- 成员视图与 commits 导出字段一致，不含 14 维特征和 `is_test`。
- 未打标样本在页面和导出中为空，不显示为 0。
- 标签筛选、时间筛选、分页、关键字查询无漏行/重行。
- predictions 导出从 `dataset_commit` 透传真标签，不依赖 `commit_feature`。
- manifest/checksum/BOM/XLSX 单 sheet 均通过。
- 空库查询不触发采集或其他计算。

## 7 边界

datasets 是板块 2 默认保存结果的查询与导出面，不是模块间运行前置。模块间仍以文件契约为 handoff；数据库提供展示、筛选和便利选择。

