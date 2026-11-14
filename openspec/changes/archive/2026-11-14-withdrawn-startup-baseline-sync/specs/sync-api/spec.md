## ADDED Requirements

### Requirement: 启动自动同步（首启分级）

系统 SHALL 在应用启动且 `SYNC_ON_STARTUP=1` 时，于后台 daemon 线程触发一次同步，MUST NOT 阻塞应用启动，失败仅记日志、MUST NOT 使启动返回 50000。同步 SHALL 复用既有单条预测链路并 **MUST 对每条 commit 落全部注册模型的 `prediction` 行**（与 `sync-prs` 一致）。同步 SHALL 区分两种模式：**首启**（空库）取 git 历史最近 `SYNC_INITIAL_LIMIT`（默认 10）条建基线；**日常增量**（库非空）补齐 DB 最新到 git HEAD 之间所有「git 有而 DB 无 prediction」的 commit，**不设小限额、直接追到最新**，仅受 `SYNC_CATCHUP_LIMIT`（默认 500）安全上限约束。

#### Scenario: 首启基线建立

- **WHEN** 干净环境首次启动且 `SYNC_ON_STARTUP=1`
- **THEN** 后台线程取 git 历史最近 `SYNC_INITIAL_LIMIT` 条、过滤已预测、逐条现算并落全部模型行；查询端点随后返回非空列表，`MUST NOT` 预先批量灌库

#### Scenario: 日常增量追到最新

- **WHEN** 库非空且启动/触发增量同步
- **THEN** 补齐 DB 最新到 HEAD 之间所有未预测 commit，`MUST NOT` 仅取固定 `SYNC_INITIAL_LIMIT` 条；仅当缺口超出 `SYNC_CATCHUP_LIMIT` 时截断并提示，已预测的提交 `MUST NOT` 重复进入预测流程

#### Scenario: 全模型落库

- **WHEN** 同步处理一条可现算的 commit
- **THEN** `prediction` 表中该 commit 在每一个注册模型下各有一行，前端按 `model_name` 取数即可，MUST NOT 仅落默认模型

### Requirement: 同步状态查询

`GET /api/sync/status` SHALL 返回统一包络 `data` 中的同步状态快照：`running`（bool）、`mode`（"startup" | "manual" | "catchup" | null）、`scope`（描述，如 "baseline" / "catchup-to-head"）、`total`（计划预测数）、`done`（已完成数）、`current_hash`（正在处理的提交）、`started_at`、`last_error`。手动触发若已在运行中 SHALL 直接返回当前状态而非 50000。

#### Scenario: 空闲状态

- **WHEN** 无同步进行
- **THEN** 返回 `running=false`，其余字段为 null / 0

#### Scenario: 运行中查询

- **WHEN** 同步进行中调用
- **THEN** 返回 `running=true` 与实时 `total` / `done` / `current_hash`

### Requirement: 同步进度 SSE 推送

`GET /api/sync/stream` SHALL 以 `text/event-stream` 持续推送 `_sync_state` 变化：每行 `data: {json}` 一个 JSON 快照，至少包含 `running` / `total` / `done` / `current_hash`。连接 SHALL 在同步结束后发送最终快照并关闭，或客户端断开时清理资源。

#### Scenario: 进度实时到达

- **WHEN** 前端以 `EventSource` 订阅且同步进行
- **THEN** 每完成一条提交收到一次 `done` 递增的快照，无需前端轮询

### Requirement: 补齐到最新（catchup，非日期区间预测）

系统 SHALL 提供 `POST /api/sync/catchup`，扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并预测（幂等、全模型），**MUST NOT 接受任何日期参数让用户指定历史区间**。该端点语义与日常增量一致（补齐缺口至 HEAD），仅作手动显式触发入口；缺口超出 `SYNC_CATCHUP_LIMIT`（默认 500）时截断并提示。

#### Scenario: 手动补齐缺口

- **WHEN** 用户点击「补齐到最新」或运维手动调用 catchup
- **THEN** 仅 DB 缺失、git 已有的 commit 被预测，MUST NOT 让用户以日期圈定范围

#### Scenario: 无日期参数

- **WHEN** 调用 catchup
- **THEN** 端点签名不含 `since`/`until`，MUST NOT 提供任意历史区间的按需预测入口
