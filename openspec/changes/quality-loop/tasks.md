# quality-loop — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/quality/spec.md`
> 创建：2026-10-27 ｜ 状态：进行中

## 1. 运行时配置底座

- [x] 1.1 `models.py` 新增 `RuntimeSetting`（`key` PK / `value` / `updated_at`）— `backend/app/models.py`
- [x] 1.2 新增 `app/services/settings.py`：`thresholds` / `high_threshold` / `mid_threshold` / `set_thresholds` / `refresh` / `reset_cache`（DB 持久化 + 内存缓存 + 降级回退）— `backend/app/services/settings.py`
- [x] 1.3 `_parse_time` 上移为 `app/timeutil.parse_time_param`，`commits.py` / `trends.py` 改用 — `backend/app/timeutil.py`
- [x] 1.4 `prs.get_pr_risk_level` 与 `trends` 高风险计数改读运行时阈值 — `backend/app/api/{prs,trends}.py`

## 2. 质量度量与回流

- [x] 2.1 新增 `app/services/quality.py`：混淆矩阵、指标派生、阈值扫描、样本导出 — `backend/app/services/quality.py`
- [x] 2.2 新增 `app/api/quality.py`：`GET /api/quality`、`GET /api/quality/dataset`、`POST /api/quality/calibrate` — `backend/app/api/quality.py`
- [x] 2.3 `schemas.py` 增加质量/数据集/校准三组响应模型 — `backend/app/schemas.py`
- [x] 2.4 `main.py` 注册 quality 路由并在 lifespan 预热阈值缓存 — `backend/app/main.py`

## 3. 数据库与契约

- [x] 3.1 `infra/schema.sql` 重新生成（5 → 6 表）— `infra/schema.sql`
- [x] 3.2 `test_schema_sql.py` 表集合断言加入 `runtime_setting` — `backend/tests/test_schema_sql.py`
- [x] 3.3 `test_mirror.py` 路径集加入三条新端点，字段集逐字断言 — `backend/tests/test_mirror.py`
- [x] 3.4 `docs/backend/api-spec.md` 登记三条新端点与阈值来源变更 — `docs/backend/api-spec.md`

## 4. 测试

- [x] 4.1 `conftest.py` 清空 `runtime_setting` 并 `reset_cache()`，避免阈值串味 — `backend/tests/conftest.py`
- [x] 4.2 新增 `tests/test_quality_api.py`：指标、无标签、标签无预测、导出、校准落库、样本不足、阈值即时生效 — `backend/tests/test_quality_api.py`

## 测试与验证

### 单元测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/test_quality_api.py tests/test_schema_sql.py tests/test_mirror.py -o addopts="" -q`
- 证据：终端 `N passed`；覆盖混淆矩阵、派生指标为 null、导出、校准成功与样本不足两条分支

### 集成测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：全量套件全绿（MySQL `jit_test`；`runtime_setting` 真实落库，校准后 `GET /api/prs` 等级变化）

### 验收测试

- 按 `specs/quality/spec.md` 逐条走：指标 → 无标签边界 → 标签无预测边界 → 导出 → 校准 → 样本不足 → 等级即时生效
- 证据：`test_quality_api.py` 用例名与 Scenario 一一对应

### 非功能验证

- 前端构建：`cd frontend; npm run build`（本 change 不改前端，用于确认无回归）
- 安全：`GET /api/quality/dataset` 与其它查询端点一样要求 `X-API-Key`，未带令牌 → 40100
- 性能：`GET /api/quality` 为单条聚合 SQL，标签量级（百级）下 < 100ms

### 已知缺口

- 不做离线再训练（本 change 只产出回流样本）
- 校准只调阈值，不动模型权重
- 未做标签冲突仲裁（只认 `label_method="manual"`）
