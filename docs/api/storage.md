# 存储登记与导出 API（storage）

一句话：把模块产物文件（提交表、清洗表、预测表、模型文件、图）按 schema 自动登记进关系库供展示（内部能力），按数据链路汇总历史产物并支持整链删除，或把库中表导出为 CSV/XLSX 文件。

前端入口：`/storage` 产物中心（见 [`../web_page/storage.md`](../web_page/storage.md)）；历史产物查看、选择、下载、删除与数据集成员在此页，**页面不提供文件导入**。`POST /api/storage/import` 仅作内部自动登记，见第 2 节。`/api/storage/export` 仅由数据集 CSV 下载复用，页面不提供按表导出入口。

表结构见 [`../database/`](../database/)；数据集读写见 [datasets.md](datasets.md)。

## 1. 职责与不负责范围

- 负责内部自动登记：清洗成功后按 schema 识别产物文件、校验列/行/manifest/checksum、幂等 upsert、刷新数据集统计；该入口不对页面开放。
- 负责按 `job.chain_id` / `parent_job_ids` 汇总数据链路，并提供整链删除。
- 负责按表白名单导出 CSV/XLSX：每次导出按 `format` 只生成一份文件，manifest 作为内部校验记录随批次生成，不与核心文件混排。
- 不负责解析业务语义（不做 SZZ、清洗、训练）；不修改模块产物本身；不把内部登记当作模块运行前置。

## 2. 端点契约

### POST /api/storage/import

内部自动登记接口：由数据清洗服务在清洗成功后调用，用于把清洗产物登记为数据集。**页面不提供文件上传入口，也不向用户暴露此端点。**

`multipart/form-data`：

| part | 必填 | 契约 |
|---|---|---|
| `files[]` | 是 | ≤100 个；单文件 ≤64MiB，批次合计 ≤64MiB |
| `config` | 否 | JSON 文本，默认 `{}` |

`config` 只允许 `dataset_id`、`create_dataset`、`model_artifact_status`、`register_figures`；`dataset_id` 与 `create_dataset` 互斥。

识别四类文件：

| 类型 | 扩展名 | 要求 |
|---|---|---|
| 提交表 | `.csv` / `.xlsx` | 列匹配 `collected_commits` 或 `clean_dataset`（取缺列最少者），必填 `commit_hash,repo_name,is_bug_inducing,label_source,source_type` |
| 预测表 | `.csv` / `.xlsx` | 列严格等于 `predictions`，且 `model_version` / `feature_version` 与库中模型一致 |
| 模型文件 | `.pkl` / `.zip` | 训练产物为单个 `.pkl` + 侧车 `train_<algo>_meta_<job_id>.json`；外部交付 ZIP 含 `model_meta.json`、`feature_order.txt`、`checksum.sha256` 与至少一个非空 `.pkl`；`line` 与特征维度匹配 |
| 图 | `.png` | `figure_type ∈ roc/pr/confusion/calibration/effort_unaware/effort_aware/feat_importance`，需同名已验证 manifest，模型须已登记；历史 `effort` 别名写入时归一为 `effort_unaware` |

配对的 `<stem>.manifest.json` 必须存在且 `outputs` 中同名条目的 sha256 与上传内容一致。

`create_dataset` 字段：`name`（≤128，必填）、`source_type`（固定 `git_repo`，必填）、`source_url`、`repo_name`、`repo_source`、`branch`、`head_hash`。公开数据集只能由 collect 任务创建，storage 不接受 `public_dataset`。

响应：

```json
{"items": [{"name": "a.csv", "schema": "collected_commits", "target_tables": ["commit"], "status": "imported", "inserted": 1, "updated": 0, "unchanged": 0, "rejected": 0, "errors": []}], "summary": {"inserted": 1, "updated": 0, "unchanged": 0, "rejected": 0}}
```

单个文件失败不影响其他文件；全部 rejected 才整体 40001。

### GET /api/storage/export

| 参数 | 必填 | 契约 |
|---|---|---|
| `table` | 是 | 必须是 ORM 中的表名（`Base.metadata.tables`） |
| `format` | 否 | `csv`（默认）/ `xlsx` |
| `dataset_id` / `model_name` | 否 | 仅对含对应列/关联的表生效 |
| `start_time` / `end_time` | 否 | 按表映射的时间列过滤 |
| `limit` | 否 | 1..100000 |

超过 100000 行且未给 `limit` → 40001。响应：

```json
{"job_id": "...", "module": "storage", "outputs": [{"name": "...", "sha256": "...", "size_bytes": 1}], "manifest_name": "...", "format": "csv", "filters": {}, "columns": [], "preview": [], "row_count": 0, "total": 0}
```

`job` / `user_config` 的 JSON 列会 scrub，命中 traceback/SQL 关键字替换为 `[redacted]`。

### GET /api/storage/tables

返回表目录：

```json
{"items": [{"name": "commit", "columns": ["..."], "filters": ["limit", "dataset_id", "start_time", "end_time"]}]}
```

### GET /api/storage/lineage

按数据链路汇总历史产物；链路关系只来自 `job.chain_id` 与 `job.parent_job_ids`，不按文件名猜测。

| 参数 | 必填 | 契约 |
|---|---|---|
| `kind` | 否 | `collect` / `clean` / `train` / `predict_batch` / `evaluate` / `explain`，过滤链内节点类型 |
| `status` | 否 | 五态之一 |
| `search` | 否 | 名称 / 任务编号关键字 |
| `start_time` / `end_time` | 否 | 按链内任务创建时间过滤 |
| `page` / `size` | 否 | 默认 1 / 20，`size` 上限 100 |

响应：

```json
{"items": [{
  "chain_id": "j-collect01",
  "title": "repo-A · 2026-11-26",
  "created_at": "2026-11-26T08:00:00Z",
  "node_count": 5,
  "kinds": {"collect": 1, "clean": 1, "train": 1, "predict_batch": 1, "evaluate": 1},
  "nodes": [{
    "job_id": "j-train01", "kind": "train", "status": "success",
    "parent_job_ids": [{"kind": "clean", "job_id": "j-clean01"}],
    "model_names": ["lr_21513c90_v1"], "dataset_id": null,
    "created_at": "2026-11-26T08:10:00Z", "finished_at": "2026-11-26T08:12:00Z",
    "artifacts": [{"name": "train_lr_model_j-train01.pkl", "size_bytes": 4096}]
  }]
}], "total": 1, "page": 1}
```

- 训练多算法或同清洗结果训练多模型时，`nodes` 保留分叉，不做线性化。
- 缺少 `parent_job_ids` 的孤立任务单独成链，`title` 标注“未关联”，不伪造上下游。

### DELETE /api/storage/chains/{chain_id}

整链删除，必须带 `?confirm=true`，否则 40001。

删除范围：`chain_id` 命中的全部 `job` 行与其已发布产物、`model_artifact.train_job_id` 命中的模型（含 `model` 行与 `.pkl`）、`dataset.job_id` 命中的数据集（含 `dataset_commit`）。

共享保护：

- 链内模型被链外 `prediction` / `model_figure` 引用，或链内数据集被链外任务引用时，返回 40001，`data.references` 列出引用方，不执行任何删除。
- 链内资产只被链内任务引用时正常删除。

响应：

```json
{"chain_id": "j-collect01", "jobs": 5, "artifacts": 12, "models": 1, "datasets": 1}
```

### GET /api/storage/outputs/{job_id}/{name}

下载已发布产物；跨模块、未登记、checksum 不符均 40400。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 文件数/大小/列/行/manifest/checksum/公式注入/ZIP 结构非法、schema 歧义、自然键重复、版本不一致、导出参数非法、缺 `confirm=true`、链路资产被外部引用 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 模型/数据集/批次/文件不存在或不可用 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- CSV 必须 UTF-8/BOM；XLSX 单 sheet、禁宏与外部链接、禁公式。
- 列名 `[a-z][a-z0-9_]*` 且唯一，≤100 列、≤100000 行。
- 同名模型文件 checksum 不同且模型已加载时返回 40001，要求换 `model_name`。

## 4. 输出契约

- 内部登记结果按文件逐条返回计数：`inserted/updated/unchanged/rejected`。
- 导出产物命名 `{module}_{artifact}_{job_id}.{format}`；每次请求只生成所选 `format` 的一份文件，manifest 作为内部校验记录随附，`.index.json` 不可下载。
- 幂等：同一 `create_dataset` 得到同一 `dataset_id`（uuid5）；重复登记不产生重复数据集。

## 5. 可配置项

`collect.allow_roots` 限制本地路径；`model_artifact_status` 默认 `available`（另一值 `retired`）；`register_figures` 默认 true。

## 6. 状态持久化

- 内部登记写 `dataset`、`dataset_commit`、`commit`、`commit_feature`、`prediction`、`model`、`model_artifact`、`model_figure`；登记不写 `job`。因此登记资产没有 `chain_id`，不进入链路视图；只能在数据集 / 模型查询中查看。
- 整链删除会删除链内 `job` 行及其产物，并联动删除链内模型与数据集；共享引用检查通过后才提交，失败整体回滚。
- 每个文件独立事务；失败回滚并清理已发布资产。
- 登记后回填数据集 `sample_count/pos_count/neg_count/time_start/time_end`。

## 7. 验收

- 内部自动登记可识别四类文件；列不符、缺 manifest、checksum 不符被拒。
- 重复登记幂等，计数正确（unchanged）。
- 导出列与库表一致，时间与过滤条件正确，超限被拒。
- 下载跨模块或篡改文件失败。
- 依次跑收集 → 清洗 → 训练 → 预测 → 评估后，`GET /api/storage/lineage` 返回同一条链且父子关系逐级正确；训练多算法时分叉仍属同一链。
- `DELETE /api/storage/chains/{chain_id}` 缺 `confirm=true` 返回 40001；链内资产被外部引用时返回 40001 并列出引用方；确认后链内任务、产物、模型与数据集一并清除。

## 8. 边界

storage 是可选展示层：模块之间只交换文件，数据库为空不影响任何模块独立运行；内部登记失败也不改变已发布产物。

