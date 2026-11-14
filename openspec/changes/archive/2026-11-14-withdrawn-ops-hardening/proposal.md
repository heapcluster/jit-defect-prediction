# 运维加固：配置热更新、探针拆分、事件驱动、风险门禁

## Why

`quality-loop` 让阈值能校准了，但运维侧还有四处硬伤：

1. **触发仍是「拉」**：每次都要人去点「同步」，CI 或 push 发生时系统毫无反应。工业级 JIT 是事件驱动的——代码一合入就开始算。
2. **阈值改了要重启**：`quality-loop` 已把阈值落进 `runtime_setting`，但没有对外的读写端点，看板校准完只能靠代码调。
3. **探针不分**：只有一个 `/api/health`，既查 DB 又查模型。K8s 用它做 liveness 会导致「DB 抖一下 → pod 被重启」；做 readiness 又缺独立语义。
4. **风险结果没法进 CI**：风险分只在页面上，无法作为 merge 门禁执行，"高风险 PR 拦下来"仍靠人肉看页面。

本 change 把 P1 四件事补齐：**webhook 事件驱动 → 配置热更新 → 探针拆分 → CI 门禁**。

## What Changes

- **新增 `POST /api/webhook/github`**：`X-Hub-Signature-256`（HMAC-SHA256 + `WEBHOOK_SECRET`）验签；`push` 触发增量同步，`pull_request`（opened/synchronize/reopened）触发 PR 同步；立即返回、后台派发。`WEBHOOK_SECRET` 未配置时 fail closed。
- **新增 `GET /api/config` / `PUT /api/config`**：读写运行时阈值（`high_risk_threshold` / `mid_risk_threshold`），约束 `0 <= mid <= high <= 1`，写入即生效。
- **新增 `GET /api/health/live` / `GET /api/health/ready`**：liveness 不查 DB（DB 故障不该重启进程），readiness 查 DB + 模型数。
- **新增 `GET /api/prs/{number}/gate`**：以运行时高风险阈值为界返回 `blocked` / `risk_level` / `reason`，供 CI 作 required check。
- **`services/health.py` 补 `liveness()` / `readiness()`**，`services/settings.py` 补 `updated_at()`（审计展示）。
- **`config.py` / `.env.example` 补 `WEBHOOK_SECRET` / `WEBHOOK_SYNC_LIMIT`**。

## Capabilities

### Added Capabilities

- `ops`：事件驱动接入、运行时配置、探针拆分、CI 风险门禁。

### Modified Capabilities

- `observability`：新增 live / ready 两个探针端点（原 `/api/health` 语义不变）。
- `query-api`：新增 PR 门禁查询端点（只读，不改既有 PR 端点字段）。

## Impact

- 后端：新增 `app/api/{webhook,runtime_config}.py`；`app/api/{health,prs}.py`、`app/services/{health,settings}.py`、`app/config.py`、`app/schemas.py`、`app/main.py` 调整。
- 数据库：无迁移（复用 `quality-loop` 的 `runtime_setting`）。
- 契约：新增 §17~§20 四条（组）端点；§四安全行补记 webhook 的签名鉴权机制。
- 安全面：新增一个**不走 `X-API-Key`** 的入口，这是有意的——GitHub 发不出自定义令牌头。它由 HMAC 签名保护，未配置密钥时直接拒绝，因此契约「所有接口均需鉴权」仍然成立。
- 测试：新增 `test_ops_api.py`（8 条）与 `test_webhook_api.py`（8 条），并同步镜像契约。

## 不做什么

- `MUST NOT` 让 webhook 在无签名/错误签名下放行，也 `MUST NOT` 在 `WEBHOOK_SECRET` 为空时启用该端点。
- `MUST NOT` 让 webhook 同步阻塞请求：必须后台派发并立即返回。
- 不做 webhook 投递重试队列（GitHub 自带重投；本系统幂等，重复事件无害）。
- 不做多仓库/多租户路由（P2 backlog）。
- 不改既有 `/api/health` 的字段与语义（前端仍在用）。
