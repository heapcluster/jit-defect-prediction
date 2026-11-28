# job

## 用途

异步任务的状态、进度、参数与产物引用。所有任务归属具体用户。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `job_id` | CHAR(36) | 否 | — | 主键 |
| `owner_user_id` | CHAR(36) | 否 | — | 归属用户 |
| `kind` | VARCHAR(16) | 否 | — | 任务类型 |
| `status` | VARCHAR(16) | 否 | `queued` | 任务状态 |
| `params_json` | TEXT | 是 | NULL | 启动参数 |
| `total` | INT | 否 | 0 | 总量 |
| `done` | INT | 否 | 0 | 已完成 |
| `current_stage` | VARCHAR(64) | 是 | NULL | 当前阶段说明 |
| `output_ref_json` | TEXT | 是 | NULL | 产物引用，不存文件内容 |
| `error_message` | TEXT | 是 | NULL | 失败原因 |
| `created_at` | DATETIME | 否 | — | 创建时间 |
| `started_at` | DATETIME | 是 | NULL | 开始时间 |
| `finished_at` | DATETIME | 是 | NULL | 结束时间 |

## 约束与索引

- 主键 `job_id`；外键 `owner_user_id` → `user.user_id`。
- 索引：`ix_job_owner_status (owner_user_id, status)`、`ix_job_kind_status (kind, status)`。
- `kind` 取值见 [../约束/enums.md](../约束/enums.md)，不在表上加枚举约束。
- 同一用户同一时刻最多 1 条 `running` 任务。

## 读写方

- 写入：各模块启动任务、更新进度与终态。
- 读取：`GET /api/jobs/{job_id}`、任务恢复。
- 保留：任务记录不随页面重置删除；其未入库产物按重置规则清理。
