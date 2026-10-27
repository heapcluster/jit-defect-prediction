# feedback-observability — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/feedback/spec.md`、`specs/observability/spec.md`、`specs/query-api/spec.md`
> 创建：2026-10-27 ｜ 状态：进行中

## 1. 解释因子中文名集中（query-api）

- [x] 1.1 新增 `backend/app/explain.py`：`FEATURE_LABELS`（14 项特征中文名）+ `explain_label(feature)`（未知回退原名）— `backend/app/explain.py`
- [x] 1.2 `schemas.ExplanationItem` 增加 `label: str` — `backend/app/schemas.py`
- [x] 1.3 `predict.py` / `commits.py`（详情）/ `prs.py` 统一改用 `app.explain.FEATURE_LABELS`，删除 `prs.py` 内重复字典 — `backend/app/api/*.py`

## 2. 人工反馈闭环（feedback）

- [x] 2.1 新增 `app/api/feedback.py`：`PUT /api/commits/{commit_hash}/label`（`is_defect` 三态：`true`/`false` upsert、`null` 撤销删行），`label_method="manual"`；commit 不存在返回 40400，参数非法返回 40001 — `backend/app/api/feedback.py`
- [x] 2.2 `commits.py` 详情 `data.label` 返回 manual 标签（无则 `null`）— `backend/app/api/commits.py`
- [x] 2.3 `commits.py` 列表支持 `has_label=true` 过滤（仅查看、不触发预测）— `backend/app/api/commits.py`
- [x] 2.4 `main.py` 注册 feedback 路由 — `backend/app/main.py`

## 3. 健康检查（observability）

- [x] 3.1 新增 `app/api/health.py`：`GET /api/health` 返回 status / db / models_loaded / model_names / 三条计数 / last_sync_at / server_time；DB 异常降级为 degraded 且不回显细节 — `backend/app/api/health.py`
- [x] 3.2 `main.py` 注册 health 路由 — `backend/app/main.py`

## 4. 前端改造

- [x] 4.1 `api/index.js` 新增 `putCommitLabel` / `getHealth` — `frontend/src/api/index.js`
- [x] 4.2 `CommitDetail.vue`：标记 / 撤销缺陷操作 + SHAP 横向条形图（中文因子名）— `frontend/src/views/CommitDetail.vue`
- [x] 4.3 `RiskList.vue`：顶部健康状态条 + 「仅看已确认」筛选 — `frontend/src/views/RiskList.vue`

## 5. 契约与测试同步

- [x] 5.1 `tests/test_mirror.py`：路径集加入 `/api/health` 与 `/api/commits/{commit_hash}/label`；详情字段集加入 `label` — `backend/tests/test_mirror.py`
- [x] 5.2 新增 `tests/test_feedback_api.py`（标记 / 撤销 / 404 / 参数非法）与 `tests/test_health_api.py`（ok / degraded / 无模型）— `backend/tests/`
- [x] 5.3 `docs/backend/api-spec.md` 登记两个新端点 — `docs/backend/api-spec.md`

## 测试与验证

### 单元测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/test_feedback_api.py tests/test_health_api.py tests/test_mirror.py -o addopts="" -q`
- 证据：终端输出 `N passed`；覆盖标记 / 撤销、commit 不存在 40400、参数非法 40001、health 的 ok / degraded / 无模型三种分支、解释项中文名与未知因子回退

### 集成测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：全量套件全绿（MySQL 测试库 `jit_test`；标签行真实落库，详情与列表联读一致）

### 验收测试

- 按 `specs/feedback/spec.md`、`specs/observability/spec.md`、`specs/query-api/spec.md` 的 Scenario 逐条走：标记 → 详情可见 → 列表 `has_label=true` 过滤 → 撤销；health 三种状态；解释项中文名与未知因子回退
- 证据：每个 Scenario 在集成测试中均有对应用例（见 `test_feedback_api.py` / `test_health_api.py` 的用例名）

### 非功能验证

- 前端构建：`cd frontend; npm run build`
- 证据：终端输出 `✓ built in Xs`，无编译错误
- 安全：health 的 degraded 分支断言响应体不含 `mysql+pymysql`、口令或堆栈字串

### 已知缺口

- 人工标签暂不触发再训练（本 change 只落地回流入库）
- `/api/health` 的 `last_sync_at` 依赖内存态 `_sync_state`，进程重启后为 `null`
- 条形图为静态渲染，未做点击下钻到具体文件（需 diff 数据，后置）
