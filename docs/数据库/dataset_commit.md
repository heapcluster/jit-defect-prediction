# dataset_commit

## 用途

数据集成员，一行代表一个提交级样本。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `dataset_id` | CHAR(36) | 否 | — | 所属数据集 |
| `commit_id` | CHAR(36) | 否 | — | 对应 `commit.commit_id` |
| `commit_hash` | CHAR(40) | 否 | — | 提交哈希，导出与展示用 |
| `repo_url` | VARCHAR(512) | 是 | NULL | 来源仓库 |
| `branch` | VARCHAR(128) | 是 | NULL | 来源分支 |
| `author_name` | VARCHAR(128) | 是 | NULL | 作者 |
| `author_email` | VARCHAR(128) | 是 | NULL | 作者邮箱 |
| `committed_at` | DATETIME | 是 | NULL | 提交时间 |
| `message` | TEXT | 是 | NULL | 提交说明 |
| `parent_hash` | CHAR(40) | 是 | NULL | 父提交 |
| `is_bug_inducing` | TINYINT(1) | 是 | NULL | 标签，1 / 0 |
| `label_method` | VARCHAR(32) | 是 | NULL | 打标方式 |
| `fix_commit_hash` | CHAR(40) | 是 | NULL | 关闭缺陷的修复提交 |
| `feature_json` | JSON | 是 | NULL | 特征快照；专家线为按契约顺序排列的 14 个数值数组，语义线为 768 维数组 |
| `row_no` | INT | 否 | 0 | 数据集内行序号，从 0 开始，按结果顺序写入 |

## 约束与索引

- 主键 `(dataset_id, commit_hash)`；同一数据集内 `commit_hash` 必须唯一，保存前由调用方保证已去重。
- 外键 `dataset_id` → `dataset.dataset_id`（`ON DELETE CASCADE`）；`commit_id` → `commit.commit_id`。
- 元数据列（`repo_url`、`author_name`、`committed_at`、`message` 等）是保存时的快照，属于受控冗余：导出、预览与追溯直接读本表，不回查 `commit`。
- 标签与 `label_method`、`fix_commit_hash` 只存库，不进入导出文件。
- `feature_json` 是特征唯一落点：专家线为按 `功能点/02-数据收集.md` 第 4.1 节顺序排列的 14 个数值数组；语义线为 768 维数组，下标 0–767 依次对应导出列 `f_0001`–`f_0768`。导出时展开为 14 列或 768 列，不建宽表。

## 读写方

- 写入：收集或清洗保存数据集时批量写入；写入前按 `(repo_name, commit_hash)` 幂等补齐 `commit` 行并取 `commit_id`，保证外键成立。`repo_name` 取样本的 `project`（`owner/repo`）；同一数据集只允许一个 `project`。
- 读取：数据集成员分页、训练与评估取样本。
- 删除：随数据集删除；不单独删除成员。
