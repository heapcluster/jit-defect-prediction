## ADDED Requirements

### Requirement: 健康检查与运行状态

`GET /api/health` SHALL 返回 `status`（`ok` / `degraded`）、`db`（`up` / `down`）、`models_loaded`（数量）与 `model_names`（名称列表）、`commit_count` / `prediction_count` / `labeled_count`、`last_sync_at`（来自同步状态快照，未同步过为 `null`）、`server_time`（当前 UTC，ISO 8601 带 Z）。当 DB 不可达或已加载模型数为 0 时 `status` SHALL 为 `degraded`。响应 `MUST NOT` 回显连接串、口令、堆栈或文件路径。

#### Scenario: 健康

- **WHEN** DB 可达且已加载至少一个模型
- **THEN** 返回 `status="ok"`、`db="up"`、`models_loaded>=1` 及各项计数，`server_time` 为 ISO 8601 带 Z 后缀

#### Scenario: DB 不可达（异常）

- **WHEN** 查询 DB 时抛出连接异常
- **THEN** 返回 `status="degraded"`、`db="down"`，计数字段为 0；HTTP 仍为 200（`MUST NOT` 借健康检查抛 50000），且响应体不含连接串、口令或堆栈

#### Scenario: 无模型（边界）

- **WHEN** DB 可达但模型目录为空、未加载到任何模型
- **THEN** `models_loaded=0`、`model_names=[]`、`status="degraded"`，其余字段照常返回
