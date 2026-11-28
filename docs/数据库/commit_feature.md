# commit_feature

## 用途

全系统共享的 Kamei 14 维特征与缺陷标签，一行对应「一个提交 × 一个特征版本」。用于跨数据集的提交特征复用与去重；训练与预测读取数据集快照 `dataset_commit.feature_json`，不直接读本表。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `commit_id` | CHAR(36) | 否 | — | 提交内部标识，主键之一 |
| `feature_version` | VARCHAR(32) | 否 | — | 特征版本，取值见 `约束/enums.md`，主键之一 |
| `ns` | DECIMAL(20, 10) | 否 | — | 修改子系统数 |
| `nd` | DECIMAL(20, 10) | 否 | — | 修改目录数 |
| `nf` | DECIMAL(20, 10) | 否 | — | 修改文件数 |
| `entropy` | DECIMAL(20, 10) | 否 | — | 修改分布熵 |
| `la` | DECIMAL(20, 10) | 否 | — | 新增代码行数 |
| `ld` | DECIMAL(20, 10) | 否 | — | 删除代码行数 |
| `lt` | DECIMAL(20, 10) | 否 | — | 修改前文件总行数 |
| `fix` | TINYINT(1) | 否 | — | 是否为缺陷修复提交 |
| `ndev` | DECIMAL(20, 10) | 否 | — | 历史修改该文件的开发者数 |
| `age` | DECIMAL(20, 10) | 否 | — | 文件最后一次修改距今时长 |
| `nuc` | DECIMAL(20, 10) | 否 | — | 此前修改该文件的次数 |
| `exp` | DECIMAL(20, 10) | 否 | — | 开发者经验，全历史 |
| `rexp` | DECIMAL(20, 10) | 否 | — | 近期开发者经验，最近 90 天 |
| `sexp` | DECIMAL(20, 10) | 否 | — | 子系统开发者经验，按子系统全历史 |
| `is_bug_inducing` | TINYINT(1) | 是 | NULL | 标签，1 / 0 |
| `labeled_at` | DATETIME | 是 | NULL | 打标时间 |

## 约束与索引

- 主键 `(commit_id, feature_version)`；外键 `commit_id` → `commit.commit_id`。
- 特征按仓库历史计算，因此主键落到 `commit_id` 而不是 `commit_hash`。
- 不归属任何用户，不按用户隔离。
- 同一 `commit_id` 可保留多个特征版本；写入新版本时新增行，不覆盖旧版本。
- 语义线的 768 维向量存于 `dataset_commit.feature_json`，不在本表。

## 读写方

- 写入：收集与保存专家线数据集时写入特征与标签；`(commit_id, feature_version)` 已存在则不重复写入。
- 读取：跨数据集复用提交特征时按 `commit_id + feature_version` 查询；训练与预测不直接读取，改用 `dataset_commit.feature_json` 快照。
- 删除：**永不删除**。删除数据集、模型或预测结果都不清理本表。

## 共享规则

- 与 `commit` 同为系统级共享数据，只增不删。
