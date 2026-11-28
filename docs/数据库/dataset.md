# dataset

## 用途

数据集定义：收集产出、清洗产出、导入后清洗产出、训练测试集，以及预测结果集。所有数据集归属具体用户。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `dataset_id` | CHAR(36) | 否 | — | 主键 |
| `owner_user_id` | CHAR(36) | 否 | — | 归属用户 |
| `name` | VARCHAR(128) | 否 | — | 数据集名称 |
| `line` | VARCHAR(16) | 否 | `expert` | `expert` / `semantic` |
| `source_type` | VARCHAR(16) | 否 | `git_repo` | `git_repo` / `upload` / `clean` / `split` / `prediction` |
| `parent_dataset_id` | CHAR(36) | 是 | NULL | 来源数据集（清洗、测试集、预测结果） |
| `repo_url` | VARCHAR(512) | 是 | NULL | 来源仓库地址 |
| `repo_name` | VARCHAR(128) | 是 | NULL | 仓库名 |
| `platform` | VARCHAR(16) | 是 | NULL | `github` / `gitee` |
| `branch` | VARCHAR(128) | 是 | NULL | 分支 |
| `head_hash` | CHAR(40) | 是 | NULL | 采集时分支 HEAD |
| `time_start` | DATETIME | 是 | NULL | 样本最早提交时间 |
| `time_end` | DATETIME | 是 | NULL | 样本最晚提交时间 |
| `sample_count` | INT | 否 | 0 | 样本总数 |
| `pos_count` | INT | 否 | 0 | 正样本数 |
| `neg_count` | INT | 否 | 0 | 负样本数 |
| `feature_version` | VARCHAR(32) | 是 | NULL | 特征版本，取值见 `约束/enums.md` |
| `dedupe_key` | CHAR(64) | 是 | NULL | 覆盖键；同用户同键时覆盖，`split` / `prediction` 为空 |
| `status` | VARCHAR(16) | 否 | `ready` | `ready` / `failed` |
| `job_id` | CHAR(36) | 是 | NULL | 产出该数据集的任务 |
| `manifest_path` | VARCHAR(512) | 是 | NULL | 产物清单相对仓库根目录的路径（如 `temp/datasets/<dataset_id>/manifest.json`） |
| `created_at` | DATETIME | 否 | — | 创建时间 |

## 约束与索引

- 主键 `dataset_id`。
- 外键 `owner_user_id` → `user.user_id`；`parent_dataset_id` → `dataset.dataset_id`；`job_id` → `job.job_id`。
- 索引：`ix_dataset_owner (owner_user_id, created_at)`、`ix_dataset_parent (parent_dataset_id)`。
- 唯一键 `uk_dataset_dedupe (owner_user_id, dedupe_key)`；MySQL 允许多个 `NULL`，因此 `split` / `prediction` 可多条。

## 覆盖键

- `dedupe_key = SHA-256(规范化来源串)`，64 位小写十六进制；同用户同键表示同一来源，保存时覆盖。
- `git_repo`：`collect|{repo_name 小写}|{branch}|{line}`。
- `clean`：`clean|{parent_dataset_id}|{ops_hash}`。
- `upload`：`upload|{file_sha256}|{ops_hash}`。
- `ops_hash` 为清洗操作列表按操作名排序、补齐默认参数后的规范 JSON（键名升序、无多余空格）的 SHA-256，64 位小写十六进制；默认参数见 `功能点/03-数据清洗.md` 第 4.1 节。
- `split` / `prediction` 不设覆盖键，每次保存独立成条。
- 覆盖时保留原 `dataset_id` 与 `created_at`，更新名称、仓库与时间范围、`head_hash`、样本统计、`status`（置 `ready`）、`job_id`、`manifest_path`、`feature_version`；先删除原数据集的 `dataset_commit` 成员，再写入新成员。
- 覆盖在单事务内完成；删除旧成员或写入新成员任一步失败时回滚，旧成员与旧统计保留。
- 保存要求同一数据集内 `commit_hash` 唯一；存在重复行时拒绝保存，由调用方先去重。

## 来源类型

| `source_type` | 含义 | `parent_dataset_id` |
|---|---|---|
| `git_repo` | 收集任务保存的数据集 | 空 |
| `upload` | 导入文件清洗后保存的结果 | 空 |
| `clean` | 由本人已保存数据集清洗得到 | 必填 |
| `split` | 训练切分出的测试集 | 必填 |
| `prediction` | 预测结果集 | 可选 |

- 由其他数据集派生的 `clean` / `split` / `prediction` 复制 `repo_url`、`repo_name`、`platform`、`branch`、`head_hash`。
- 非仓库来源（`upload` / `clean` / `split`）行内缺少 `project` 时，保存按父数据集 `repo_name`、父数据集名称、`unknown` 依次兜底；预测结果集同样按来源 `repo_name` 兜底。仍无法确定时返回 `40901 结果缺少 project`。
- 同一数据集只允许一个 `project`；成员提交哈希必须唯一，重复时拒绝保存。
- `source_type=prediction` 时：`sample_count` 为结果行数，`pos_count` 为预测为缺陷的条数，`neg_count` 为预测为正常的条数；不使用 `dataset_commit`。
- 收集、导入清洗、清洗与测试集结果的正样本为 0 时不可保存；预测结果集不受此限制。

## 统计与版本口径

- `sample_count` / `pos_count` / `neg_count` 按成员重新统计；`source_type=prediction` 时按预测结果统计。
- `time_start` / `time_end` 取成员提交时间的最小值与最大值；成员无提交时间时为 NULL。
- `feature_version`：collect / upload 写当前模型线版本；clean / split 继承父数据集；prediction 取输入数据集或模型的特征版本。
- 覆盖时用新产物覆盖 `temp/datasets/<dataset_id>/`。

## 删除语义

- 独立删除；派生数据集的 `parent_dataset_id` 置空，模型的 `train_dataset_id` / `test_dataset_id` 置空。
- 删除时移除数据集记录、成员关系与 `temp/datasets/<dataset_id>/` 目录。
- 不删除共享仓库缓存、全局共享表 `commit` / `commit_feature`、已保存模型与评估历史。
- 删除 `source_type=prediction` 的数据集时，同事务删除 `prediction` 行。

## 读写方

- 写入：`POST /api/datasets`（收集或清洗任务保存）、`POST /api/train/save`（测试集保存）、`POST /api/predict/save`（预测结果保存）。
- 读取：`GET /api/datasets`、`GET /api/datasets/{id}`、`GET /api/storage/files`；`source_type=prediction` 时成员由 `prediction` 表提供，其余来源由 `dataset_commit` 提供。
- 删除：`DELETE /api/datasets/{id}`。
