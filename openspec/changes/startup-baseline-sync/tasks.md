# startup-baseline-sync — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/sync-api/spec.md`、`specs/db-schema/spec.md`、`specs/query-api/spec.md`
> 创建：2026-10-26 ｜ 状态：草稿（头脑风暴产出，含五项修正：全模型落库 / 取消前端日期预测 / BCNF / 增量追到 HEAD / 补齐到最新）

## 1. 启动分级基线

- [ ] 1.1 `config.py` 新增 `SYNC_ON_STARTUP`（默认 1）、`SYNC_INITIAL_LIMIT`（默认 10）、`SYNC_CATCHUP_LIMIT`（补齐到 HEAD 的安全上限，默认 500） — `backend/app/config.py`；`.env.example` 补注释。
- [ ] 1.2 `main.py` 启动默认开启后台同步；`prediction` 表为空判定首启（取 `SYNC_INITIAL_LIMIT=10` 建基线）、否则日常增量（补齐 DB 最新到 HEAD 的未预测 commit，受 `SYNC_CATCHUP_LIMIT=500` 安全上限）— `backend/app/main.py`、`backend/app/api/sync.py`；启动线程失败仅记日志、不阻塞。
- [ ] 1.3 首启/日常增量去重：沿用 `pick_hashes_to_predict`（全部模型已有 prediction 即跳过）— `backend/app/api/sync.py`。

## 2. 同步控制面（sync-api）

- [ ] 2.1 模块级 `_sync_state`（running / mode / scope / total / done / current_hash / started_at / last_error）+ 线程安全锁 — `backend/app/api/sync.py`。
- [ ] 2.2 `GET /api/sync/status` 返回快照 — `backend/app/api/sync.py`；复用统一包络 `ok(...)`。
- [ ] 2.3 `GET /api/sync/stream` SSE（`StreamingResponse`, `text/event-stream`），`_sync_state` 变化时 yield `data: {...}` — `backend/app/api/sync.py`。
- [ ] 2.4 `POST /api/sync/catchup` — 扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并预测（幂等、全模型）；**MUST NOT 接受日期参数**；缺口超 `SYNC_CATCHUP_LIMIT` 截断 — `backend/app/api/sync.py`。
- [ ] 2.5 并发：运行中再触发同步返回当前状态而非 50000。

## 3. PR 风险转译（query-api）

- [ ] 3.1 `get_pr_risk_level(risk_score)` 映射高/中/低（阈值可配）— `backend/app/api/prs.py`。
- [ ] 3.2 `build_pr_reason(pr)` 用 top 特征 / SHAP 因子模板生成一句话理由（无 LLM）— `backend/app/api/prs.py`。
- [ ] 3.3 `GET /api/prs` 响应附加 `risk_level` 与 `reason` — `backend/app/api/prs.py`；更新 `api-spec.md`。

## 4. 前端改造

- [ ] 4.1 `api/index.js` 新增 `getSyncStatus` / `subscribeSyncProgress`（EventSource）/ `postSyncCatchup` / `getCommitsByDate`（按 committed_at 查看过滤）— `frontend/src/api/index.js`。
- [ ] 4.2 `PrList.vue` 风险徽章 + 理由卡；接入 SSE 进度；新 PR/commit 自动出现 — `frontend/src/views/PrList.vue`。
- [ ] 4.3 `RiskList.vue` 日期范围仅作**查看过滤**（不触发预测）+ 「已预测覆盖」展示 + 「补齐到最新」按钮 + 接入 SSE 替代轮询 — `frontend/src/views/RiskList.vue`。

## 5. 同步统一落全部模型

- [ ] 5.1 `sync`（commit 主链路）改调 `predict_commit_all_models`，对每条 commit 落全部注册模型的 `prediction` 行（替换原默认模型单写），与 `sync-prs` 一致 — `backend/app/api/sync.py`。
- [ ] 5.2 前端按 `model_name` 查询；若该模型对某 commit 缺行，引导至「补齐到最新」补预测（幂等）— `frontend/src/api/index.js`、`frontend/src/views/*`。

## 6. 查看过滤与覆盖可视化

- [ ] 6.1 `GET /api/commits` 支持 `since`/`until` 仅作查看过滤（按 `committed_at`），MUST NOT 触发预测；空区间返回空 — `backend/app/api/commits.py`。
- [ ] 6.2 新增 `GET /api/commits/coverage` 返回已预测时间覆盖区间 `[min_committed_at, max_committed_at]`（含模型维度）— `backend/app/api/commits.py`。
- [ ] 6.3 前端 `RiskList` 显示"已预测覆盖：YYYY-MM-DD ~ YYYY-MM-DD"并提供「补齐到最新」入口 — `frontend/src/views/RiskList.vue`。

## 7. 数据库最小 BCNF 化

- [ ] 7.1 新增 `model` 表迁移（`model_name` PK、`version_key`、`trained_at`、`algo`、`feature_version`）— `backend/migrations/*`。
- [ ] 7.2 `prediction.model_name` 改 FK → `model.model_name`；四表加 `commit_hash` 外键；各表加 `updated_at` — 迁移脚本。
- [ ] 7.3 更新 `db-schema` spec 与迁移脚本；验证 14 项数值口径、幂等键不变。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 首启判定、增量去重、全模型落库、status 快照、SSE 推送、catchup 补齐到 HEAD、查看过滤（since/until 不触发预测）、等级映射、理由模板、覆盖区间、model 表 FK |
| 测试文件 | `backend/tests/test_sync_api.py`、`backend/tests/test_prs_api.py`、`backend/tests/test_db_schema.py` |
| 用例数与结果 | 待实现 |
| 复现命令 | `cd backend && python -m pytest -o addopts='' -q tests/test_sync_api.py tests/test_prs_api.py tests/test_db_schema.py` |
| 正向用例 | 空库首启跑基线并落全部模型；status 随进度更新；stream 收到 done 事件；catchup 补齐 DB→HEAD 缺口；coverage 返回区间；查看过滤不触发预测 |
| 异常 / 边界用例 | 运行中再触发返回状态；空区间返回空；等级阈值边界；model 外键约束；catchup 无日期参数 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 启动同步（全模型）→ status/stream → PR 聚合等级 → 前端徽章 → catchup 补齐 → 查看过滤 → coverage |
| 测试文件 | `backend/tests/test_sync_api.py`、前端组件测试 |
| 复现命令 | 同上 + `cd frontend && npx vitest run` |
| 关键断言 | 首启后 prediction 各模型非空；SSE 事件含 total/done；PR 响应含 risk_level；catchup 补齐 DB→HEAD；查看过滤不触发预测；model 表 FK 生效 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/sync-api/spec.md`、`specs/db-schema/spec.md`、`specs/query-api/spec.md` |
| 复现命令 | `openspec validate startup-baseline-sync --strict --no-interactive` |
| 证据归档 | 待实现后补 `backend/scripts/evidence/startup-baseline-*.md` |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是 | 首启耗时取决于窗口；SSE 替代轮询；全模型落库行数 ×N 但后台非阻塞 |
| 安全 | 是 | 端点沿用 X-API-Key 鉴权；理由模板无外部调用 |
| 可靠 | 是 | 启动同步失败仅日志；增量幂等；FK 约束不破坏既有口径 |
| 易用 | 是 | PR 徽章 + 理由；实时进度；日期仅查看过滤避免盲选 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| webhook 触发 | 本地需外网隧道验证 | backend | 后续增强 |
| 特征历史索引缓存（15s/条） | 需额外存储层 | backend/model | P1 |
| cost-effectiveness 曲线 | 属模型效果，本轮不做 | — | 后续 |
