# dataset / dataset_commit

> 旧口径把公开数据集排除在库外、把 14 维特征和 `is_test` 作为收集交付；本文已按最新板块 2 重写，`infra/schema.sql` 与 ORM 已按本文同步。

**一句话**：数据集元数据表 + 数据集成员二维表；板块 2 收集完成后默认把带缺陷标签的提交二维表写入这两张表，供页面展示、查询和导出。

## 1 职责

- `dataset`：记录一次收集任务产出的数据集元信息，包括来源类型、来源地址、许可证、标签来源、统计信息与任务关联。
- `dataset_commit`：保存该数据集的二维表成员行，即板块 2 对外导出的 `collected_commits.csv` 的逐行落库结果；XLSX 仅按下载请求从这些行即时生成。
- 这里保存的是**已打标二维表**，不是特征表；Kamei 14 维、`is_test` 和训练/测试切分不属于板块 2，`commit_feature` 不在本模块写入路径中。

## 2 dataset 字段（当前契约）

| 字段 | 类型 | 空值/默认 | 含义 |
|---|---|---|---|
| `dataset_id` | VARCHAR(36) | NOT NULL，主键 | 数据集标识 |
| `name` | VARCHAR(128) | NOT NULL | 数据集显示名 |
| `source_type` | VARCHAR(16) | NOT NULL | `git_repo` / `public_dataset` |
| `source_url` | VARCHAR(512) | 可空 | 仓库 URL 或公开数据集 URL/来源 |
| `repo_name` | VARCHAR(128) | 可空 | Git 仓库名；公开数据集可填数据集名 |
| `branch` | VARCHAR(128) | 可空 | Git 分支/ref |
| `head_hash` | CHAR(40) | 可空 | Git 采集 HEAD |
| `time_start` | DATETIME | 可空 | 采集时间范围起 |
| `time_end` | DATETIME | 可空 | 采集时间范围止 |
| `mode` | VARCHAR(16) | NOT NULL DEFAULT `full` | `full` / `incremental` |
| `label_source` | VARCHAR(32) | NOT NULL | `git_szz` / `public_dataset` |
| `szz_method` | VARCHAR(32) | 可空 | `szz_v1` / `szz_lite`；公开数据集可空或 `third_party` |
| `license` | VARCHAR(128) | 可空 | 公开数据集许可证，Git 模式可空 |
| `source_note` | TEXT | 可空 | 公开数据集来源说明 |
| `sample_count` | INT | NOT NULL DEFAULT 0 | 二维表总行数 |
| `pos_count` | INT | NOT NULL DEFAULT 0 | 正样本数 |
| `neg_count` | INT | NOT NULL DEFAULT 0 | 负样本数 |
| `unlabeled_count` | INT | NOT NULL DEFAULT 0 | 未打标数 |
| `status` | VARCHAR(16) | NOT NULL DEFAULT `collecting` | `collecting` / `ready` / `failed` / `archived` |
| `job_id` | VARCHAR(36) | 可空，外键 → `job.job_id` | 产出该数据集的收集任务 |
| `summary_path` | VARCHAR(512) | 可空 | `collect_summary_<job_id>.json` 路径 |
| `manifest_path` | VARCHAR(512) | 可空 | 主二维表 manifest 路径 |
| `quality_report_path` | VARCHAR(512) | 可空 | 公开数据集质量报告路径 |
| `created_at` | DATETIME | NOT NULL | 创建时间 |

口径：

- `dataset_id` 每次收集任务生成一个；同一配置重复运行可生成新版本，不在本轮强制覆盖。
- `job_id` 是数据链路的链根依据：选择 `dataset_id` 启动清洗 / 训练时，父任务取该字段；产物库按链路展示与整链删除依赖它。
- `pos_count + neg_count + unlabeled_count = sample_count`。
- 未打标 `is_bug_inducing=null` 只计入 `unlabeled_count`，MUST NOT 计入负样本。
- 数据来源由 `source_type + source_url + repo_name` 表达，不使用 `repo_source`。

## 3 dataset_commit 字段（当前契约）

`dataset_commit` 从“成员关联表”升级为“二维表成员表”。

| 字段 | 类型 | 空值/默认 | 含义 |
|---|---|---|---|
| `dataset_id` | VARCHAR(36) | NOT NULL，联合主键、外键 → `dataset.dataset_id` | 所属数据集 |
| `commit_hash` | CHAR(40) | NOT NULL，联合主键 | 提交标识 |
| `repo_name` | VARCHAR(128) | 可空 | 仓库名或数据集名 |
| `repo_url` | VARCHAR(512) | 可空 | 仓库/数据集来源 URL |
| `author_name` | VARCHAR(128) | 可空 | 作者 |
| `author_email` | VARCHAR(128) | 可空 | 作者邮箱 |
| `committed_at` | DATETIME | 可空 | 提交时间 |
| `message` | TEXT | 可空 | 提交信息 |
| `parent_hash` | CHAR(40) | 可空 | 父提交 |
| `is_bug_inducing` | TINYINT(1) | 可空 | 标签 1/0/null |
| `label_method` | VARCHAR(32) | 可空 | `szz_v1` / `szz_lite` / `third_party` |
| `label_source` | VARCHAR(32) | NOT NULL | `git_szz` / `public_dataset` |
| `labeled_at` | DATETIME | 可空 | 打标时间或来源时间 |
| `fix_commit_hash` | CHAR(40) | 可空 | SZZ 回溯修复提交 |
| `source_type` | VARCHAR(16) | NOT NULL | `git_repo` / `public_dataset` |
| `row_no` | INT | NOT NULL DEFAULT 0 | 导出行序，保证展示稳定 |
| `created_at` | DATETIME | NOT NULL | 入库时间 |

主键建议：

```text
(dataset_id, commit_hash)
```

同一数据集内同一 `commit_hash` 只允许一行。公开数据集出现重复提交时：

- 标签一致：保留一行，重复计数写 summary。
- 标签冲突：导入失败或生成质量报告后拒绝入库，MUST NOT 静默保留一个。

**范式取舍（有意偏离 BCNF）**：`dataset_commit` 冗余了 `commit` 表的 `repo_name` / `author_name` / `author_email` / `committed_at` / `message` / `parent_hash`，以及 `dataset` 表的 `source_type`。这些不是规范化缺陷，而是**采集时点快照**语义：数据集成员必须能独立还原当时的提交信息，不受 `commit` 表后续刷新影响；导出 `collected_commits.csv` 也直接读这些列而不跨表 join。同理 `dataset` 的 `pos_count + neg_count + unlabeled_count = sample_count` 是可重算的派生统计，为列表查询性能保留。上述冗余由写入侧保证一致，不建跨表触发器。

## 4 与文件契约的关系

板块 2 对外核心文件只有一份：

```text
collected_commits_<job_id>.csv
```

XLSX 仅由下载 / 导出端点按请求从同一数据源即时生成，不作为 collect 预生成产物。数据库保存内容必须与该二维表逐行一致。

字段映射：

| CSV 列 | 数据库字段 |
|---|---|
| `commit_hash` | `dataset_commit.commit_hash` |
| `repo_name` | `dataset_commit.repo_name` |
| `repo_url` | `dataset_commit.repo_url` |
| `author_name` | `dataset_commit.author_name` |
| `author_email` | `dataset_commit.author_email` |
| `committed_at` | `dataset_commit.committed_at` |
| `message` | `dataset_commit.message` |
| `parent_hash` | `dataset_commit.parent_hash` |
| `is_bug_inducing` | `dataset_commit.is_bug_inducing` |
| `label_method` | `dataset_commit.label_method` |
| `label_source` | `dataset_commit.label_source` |
| `labeled_at` | `dataset_commit.labeled_at` |
| `fix_commit_hash` | `dataset_commit.fix_commit_hash` |
| `source_type` | `dataset_commit.source_type` |

## 5 默认保存与失败语义

- `save_to_db=true` 为默认值。
- 文件生成成功且数据库保存成功：`job.status=success`，`dataset.status=ready`，`output_ref_json` 含 `dataset_id`。
- 文件生成成功但保存失败：`job.status=failed`，文件仍可下载，提供 `POST /api/collect/resave/{job_id}` 重新保存。
- `save_to_db=false`：只交付文件，不新增 `dataset` 行。
- 重新保存不得重复插入相同 `(dataset_id, commit_hash)`。

## 6 谁写入 / 谁读取

| 方向 | 角色 | 说明 |
|---|---|---|
| 写入 | collect 服务 | 板块 2 默认保存二维表 |
| 写入 | collect resave | 保存失败后按已保留文件重试 |
| 读取 | `GET /api/datasets` | 数据集列表 |
| 读取 | `GET /api/datasets/{id}/commits` | 二维表成员分页展示 |
| 读取 | `GET /api/datasets/{id}/export` | 导出 CSV/XLSX |
| 读取 | `/storage` 产物库 | 查看数据集、成员并按需删除 |

## 7 不写入的内容

板块 2 不写：

- `commit_feature`
- Kamei 14 维
- `is_test`
- 训练/测试切分结果
- 预测结果
- 解释结果
- 定位结果

这些字段和表属于后续板块。

## 8 验收

- Git 仓库采集完成后，`dataset` 与 `dataset_commit` 可查询到二维表内容。
- 公开数据集经 collect 任务 URL 拉取后入库，并记录 `source_type=public_dataset`、`label_source=public_dataset`、许可证和来源说明；storage 不创建公开数据集。
- 数据库行内容与导出的 `collected_commits.csv/xlsx` 逐列一致。
- 未打标样本入库为 NULL，导出为空，不显示为 0。
- 同数据集重复提交不产生重复成员；标签冲突不静默覆盖。
- 保存失败时文件保留，重新保存成功后数据集状态变为 ready。
