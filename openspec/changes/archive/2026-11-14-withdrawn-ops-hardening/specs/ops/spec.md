## ADDED Requirements

### Requirement: 运行时配置读写

`GET /api/config` SHALL 返回当前 `high_risk_threshold` / `mid_risk_threshold`、只读的 `sync_initial_limit` / `sync_catchup_limit`，以及最近一次写入时间 `updated_at`。`PUT /api/config` SHALL 接受两个阈值并写入 `runtime_setting`，约束 `0.0 <= mid_risk_threshold <= high_risk_threshold <= 1.0`；越界 SHALL 返回 `40001` 且 `MUST NOT` 写入任何配置。写入后 SHALL 立即生效（`risk_level`、趋势高风险计数、PR 门禁同步跟随），`MUST NOT` 要求重启。

#### Scenario: 热更新阈值

- **WHEN** `PUT /api/config` 提交 `{"high_risk_threshold": 0.3, "mid_risk_threshold": 0.1}`
- **THEN** 返回 `code=0` 且 `data.high_risk_threshold=0.3`；随后 `risk_score=0.35` 的 PR `risk_level` 为「高」

#### Scenario: 阈值倒挂（异常）

- **WHEN** 提交 `{"high_risk_threshold": 0.1, "mid_risk_threshold": 0.4}`
- **THEN** 返回 `code=40001`，`runtime_setting` 中阈值保持原值

### Requirement: 探针拆分

`GET /api/health/live` SHALL 只返回进程存活状态（`status` / `server_time`），`MUST NOT` 访问数据库。`GET /api/health/ready` SHALL 返回 `status` / `db` / `models_loaded` / `server_time`；DB 不可达或模型数为 0 时 `status="degraded"`，HTTP 仍为 200（`MUST NOT` 抛 50000）。

#### Scenario: 就绪检查

- **WHEN** DB 可连通且已加载至少一个模型
- **THEN** `ready` 返回 `status="ok"`、`db="up"`、`models_loaded>=1`

#### Scenario: 数据库不可达（异常）

- **WHEN** DB 连接失败
- **THEN** `ready` 返回 `status="degraded"`、`db="down"`，HTTP 200；而 `live` 仍为 `status="ok"`（不查 DB）

### Requirement: CI 风险门禁

`GET /api/prs/{number}/gate` SHALL 返回该 PR 在当前阈值下的 `risk_score` / `risk_level` / `threshold` / `blocked` / `reason`。`blocked` SHALL 为 `risk_score >= threshold`；无预测时 `risk_score=null` 且 `blocked=false`。该端点 `MUST NOT` 触发新的预测。

#### Scenario: 高风险拦截

- **WHEN** PR 最高提交风险为 0.91、运行时高风险阈值为 0.5
- **THEN** 返回 `blocked=true`、`risk_level="高"`、`threshold=0.5`

#### Scenario: 未预测（边界）

- **WHEN** 该 PR 的提交在库内均无 prediction
- **THEN** `risk_score=null`、`blocked=false`，`code=0`

### Requirement: GitHub 事件驱动

`POST /api/webhook/github` SHALL 用 `X-Hub-Signature-256` 对原始请求体验签（HMAC-SHA256，密钥 `WEBHOOK_SECRET`），`MUST NOT` 要求 `X-API-Key`。`WEBHOOK_SECRET` 未配置、签名缺失或签名错误时 SHALL 返回 `40100`。`push` 事件 SHALL 在后台触发增量同步；`pull_request` 且 action ∈ {`opened`,`synchronize`,`reopened`} SHALL 在后台触发 PR 同步；其余事件 SHALL 受理但不触发。接口 SHALL 立即返回（`MUST NOT` 在请求内完成同步）。

#### Scenario: push 触发同步

- **WHEN** 携带正确签名投递 `X-GitHub-Event: push`
- **THEN** 返回 `code=0`、`data.triggered=true`，后台以 `WEBHOOK_SYNC_LIMIT` 条为上限触发同步

#### Scenario: 签名错误（异常）

- **WHEN** 签名与请求体不匹配
- **THEN** 返回 `code=40100`，且不触发任何同步

#### Scenario: 未配置密钥（异常）

- **WHEN** `WEBHOOK_SECRET` 为空时投递任意事件
- **THEN** 返回 `code=40100`（fail closed），`MUST NOT` 因「无密钥」而放行

#### Scenario: 无关 PR 动作（边界）

- **WHEN** `pull_request` 事件的 action 为 `labeled`
- **THEN** 返回 `code=0` 且 `data.triggered=false`，不触发同步
