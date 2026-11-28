# commit

## 用途

全系统共享的提交元数据。一行代表「某个仓库中的一次提交」。`commit_id` 是内部标识，`commit_hash` 是 Git 内容哈希。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `commit_id` | CHAR(36) | 否 | — | 内部主键，服务端生成，格式 `cmt_` + 32 位小写十六进制 |
| `commit_hash` | CHAR(40) | 否 | — | Git 提交哈希 |
| `repo_name` | VARCHAR(128) | 否 | — | 仓库名，格式 `owner/repo` |
| `author_name` | VARCHAR(128) | 否 | — | 作者 |
| `author_email` | VARCHAR(128) | 是 | NULL | 作者邮箱 |
| `committed_at` | DATETIME | 否 | — | 提交时间 |
| `message` | TEXT | 否 | — | 提交说明 |
| `parent_hash` | CHAR(40) | 是 | NULL | 父提交哈希，普通列，不建外键 |

## 约束与索引

- 主键 `commit_id`；唯一键 `uk_commit_repo_hash (repo_name, commit_hash)`；索引 `ix_commit_hash (commit_hash)`、`ix_commit_committed_at (committed_at)`。
- 同一哈希出现在不同仓库时保存为两行：`exp` / `rexp` / `sexp` / `ndev` 等历史特征依赖仓库历史，不能跨仓库复用。
- 不归属任何用户，不按用户隔离。
- 写入按 `(repo_name, commit_hash)` 幂等：已存在时复用原 `commit_id`，不更新已有元数据。

## 读写方

- 写入：收集、保存数据集、保存预测结果时补齐提交行，并回传 `commit_id` 给 `dataset_commit` 或 `prediction`。
- 读取：按 `commit_id` 关联特征、数据集成员与预测明细；服务端按 `commit_id` 取提交说明、作者与提交时间，接口只返回 `commit_hash`。
- 删除：**永不删除**。删除数据集、模型、预测结果或评估历史都不清理本表。

## 共享规则

- `commit` 与 `commit_feature` 是系统级共享数据，只增不删。
- 删除任何用户资产都不触发对共享表的清理。
