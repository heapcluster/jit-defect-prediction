# 数据库索引

一篇一张表，文件名与表名一致。建表真源为 `infra/schema.sql`；文档与建表语句不一致时以建表语句为准并同步修正文档。

## 表清单

| 表 | 职责 |
|---|---|
| `user` | 账号、口令、状态 |
| `user_session` | 登录会话（令牌摘要、过期时间） |
| `user_config` | 按用户存储的个人配置 |
| `user_page_state` | 按用户与页面存储的流程进度 |
| `job` | 任务状态、进度、参数与产物引用 |
| `dataset` | 数据集定义、归属、来源与统计 |
| `dataset_commit` | 数据集成员（提交级样本） |
| `commit` | 提交元数据 |
| `commit_feature` | Kamei 14 维特征与标签 |
| `model` | 模型登记 |
| `model_artifact` | 模型文件与训练任务关联 |
| `prediction` | 预测数据集明细（提交 × 模型，按预测任务保留） |
| `evaluation` | 评估历史（指标、阈值、来源与样本统计） |
| `evaluation_figure` | 评估图表文件登记 |
| `algorithm` | 固定算法清单与超参（只读） |

## 共享表

- `commit` 与 `commit_feature` 为系统级共享数据，不归属用户、不按用户隔离。
- 两张表只增不删；删除数据集、模型、预测结果或评估历史都不清理它们。
- `commit` 以内部 `commit_id` 为主键，`(repo_name, commit_hash)` 唯一：同一提交哈希出现在不同仓库时是两行，因为 `exp` / `rexp` / `sexp` / `ndev` 等历史特征按仓库计算。

## 受控冗余

- 不追求严格 BCNF。`dataset_commit` 保存提交元数据与特征快照，`evaluation` 保存 `source_label` / `model_label`，`prediction` 保存 `model_label` 与 `actual_label`。
- 冗余字段只服务历史可读性与来源追溯，写入时由创建方一次性填好；查询不得在冗余字段与源表之间自行推断新的真源。
- 新增字段时优先复用已有冗余，不为了消除冗余而拆表。

## 关系

- `dataset.owner_user_id` → `user.user_id`；`dataset.parent_dataset_id` → `dataset.dataset_id`。
- `dataset_commit.dataset_id` → `dataset.dataset_id`；`dataset_commit.commit_id` → `commit.commit_id`。
- `prediction.dataset_id` → `dataset.dataset_id`；`prediction.commit_id` → `commit.commit_id`（可空）；`prediction.model_name` → `model.model_name`（可空）。
- `evaluation.owner_user_id` → `user.user_id`；`evaluation.dataset_id` → `dataset.dataset_id`（可空）；`evaluation.model_name` → `model.model_name`（可空）。
- `evaluation_figure.evaluation_id` → `evaluation.evaluation_id`。
- `job.owner_user_id` → `user.user_id`。
- `user_session.user_id`、`user_config.user_id`、`user_page_state.user_id` → `user.user_id`。

## 命名与约束

- 主键使用「类型前缀 + 32 位小写十六进制」字符串，总长不超过 36（如 `ds_...`、`job_...`）；其余主键按建表语句定义，如 `user_session.session_id` 为 64 位摘要。
- 所有归属列必须有索引；用户维度的查询必须带归属条件。
- 删除语义在单表文档中写明，不允许实现时自行决定。
