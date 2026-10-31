# ops-hardening — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无独立 design.md ｜ 规格：`specs/ops/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-27 ｜ 状态：进行中（以任务勾选和证据为准）
> 关联需求：无（工程化）
> 统一格式见 `docs/common/openspec-task-template.md`；末尾「测试与验证」为强制板块。


## 1. 运行时配置

- [x] 1.1 `services/settings.py` 增加 `updated_at()`（审计展示）— `backend/app/services/settings.py`
- [x] 1.2 新增 `app/api/runtime_config.py`：`GET /api/config`、`PUT /api/config`（越界 40001）— `backend/app/api/runtime_config.py`

## 2. 探针拆分

- [x] 2.1 `services/health.py` 增加 `liveness()`（不查 DB）与 `readiness()`（DB + 模型）— `backend/app/services/health.py`
- [x] 2.2 `api/health.py` 增加 `/api/health/live`、`/api/health/ready`，保留原 `/api/health` 语义 — `backend/app/api/health.py`

## 3. CI 门禁

- [x] 3.1 `api/prs.py` 增加 `GET /api/prs/{number}/gate`（只读、不触发预测）— `backend/app/api/prs.py`

## 4. 事件驱动

- [x] 4.1 `config.py` 增加 `WEBHOOK_SECRET` / `WEBHOOK_SYNC_LIMIT`，`.env.example` 补注释 — `backend/app/config.py`
- [x] 4.2 新增 `app/api/webhook.py`：HMAC 验签、push / pull_request 后台派发、fail closed — `backend/app/api/webhook.py`
- [x] 4.3 `main.py` 注册 runtime_config 与 webhook 路由（webhook 不挂 API key 依赖）— `backend/app/main.py`

## 5. 契约与测试

- [x] 5.1 `schemas.py` 增加 config / live / ready / gate / webhook 响应模型 — `backend/app/schemas.py`
- [x] 5.2 `test_mirror.py` 路径集与字段集同步（5 条新路径）— `backend/tests/test_mirror.py`
- [x] 5.3 新增 `tests/test_ops_api.py`（配置热更新 / 探针 / 门禁 / 鉴权）— `backend/tests/test_ops_api.py`
- [x] 5.4 新增 `tests/test_webhook_api.py`（未配置 / 错签 / 缺签 / ping / push / PR / 无关动作）— `backend/tests/test_webhook_api.py`
- [x] 5.5 [历史版 `docs/backend/api-spec.md`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/docs/backend/api-spec.md) 登记 §17~§20 与 §四安全行 — [历史版 `docs/backend/api-spec.md`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/docs/backend/api-spec.md)

## 测试与验证（强制板块）

### 1. 单元测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/test_ops_api.py tests/test_webhook_api.py tests/test_mirror.py -o addopts="" -q`
- 证据：`37 passed`；覆盖阈值倒挂 40001、未配置密钥 40100、错签 40100、无关动作不触发

### 2. 集成测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：全量 `313 passed`（MySQL `jit_test`）；门禁读库内 prediction，配置落 `runtime_setting`

### 3. 验收测试

- 按 `specs/ops/spec.md` 逐条：热更新 → 探针就绪/降级 → 门禁拦截/放行 → webhook 四条分支
- 证据：`test_ops_api.py` / `test_webhook_api.py` 用例名与 Scenario 对应

### 4. 非功能验证

- 安全：webhook 无签名/错签/无密钥三路均 40100；其余端点不带 `X-API-Key` 仍 40100
- 响应性：webhook 立即返回，同步在守护线程内执行（测试用 `_spawn` 替换为同步执行以断言）
- 前端构建：`cd frontend; npm run build`（本 change 不改前端）

### 5. 已知缺口与后续计划

- webhook 未做投递重试队列（GitHub 自带重投 + 本系统幂等）
- 门禁未接入 CI 配置文件（需在仓库侧配置 required check，属于部署动作）
- webhook 只覆盖 `push` / `pull_request` 两类事件
