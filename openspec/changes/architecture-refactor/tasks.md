# architecture-refactor — 任务清单

> 提案：`proposal.md` ｜ 规格：无（纯重构，对外行为不变，故无 ADDED Requirements）
> 创建：2026-10-27 ｜ 状态：进行中

## 1. 共享工具模块

- [x] 1.1 新增 `app/timeutil.py`：`iso_z`（None 原样返回）+ `now_naive_utc` — `backend/app/timeutil.py`
- [x] 1.2 新增 `app/validate.py`：`normalize_commit_hash`（非法 → 40001，返回小写）— `backend/app/validate.py`
- [x] 1.3 `predict.py` / `commits.py` / `feedback.py` / `prs.py` 改用共享 `iso_z` 与 `normalize_commit_hash`，删除各自的私有实现与 `HASH_HEX` 常量 — `backend/app/api/*.py`

## 2. 服务层

- [x] 2.1 新增 `app/services/__init__.py`（说明分层目的与「不改行为」边界）— `backend/app/services/__init__.py`
- [x] 2.2 `services/commits.py`：`default_model_in_table` / `feature_dict` / `explanation_for` / `label_for` / `labeled_hashes_stmt` — `backend/app/services/commits.py`
- [x] 2.3 `services/feedback.py`：人工标签写入 / 撤销 — `backend/app/services/feedback.py`
- [x] 2.4 `services/health.py`：运行状态聚合（DB / 模型 / 三条计数 / last_sync_at / server_time）— `backend/app/services/health.py`

## 3. 路由变薄

- [x] 3.1 `api/feedback.py` 只剩入参校验 + `ok(...)` — `backend/app/api/feedback.py`
- [x] 3.2 `api/health.py` 只剩 `ok(health_service.snapshot())` — `backend/app/api/health.py`
- [x] 3.3 `api/commits.py` 保留参数校验与区间语义（`_parse_time`），查询组装转调服务层 — `backend/app/api/commits.py`
- [x] 3.4 `trends.py` 改为从 `app.services.commits` 导入 `default_model_in_table`，不再跨路由取业务函数 — `backend/app/api/trends.py`

## 4. 测试同步

- [x] 4.1 `test_health_api.py`：monkeypatch 目标改为 `app.services.health.SessionLocal` — `backend/tests/test_health_api.py`
- [x] 4.2 `test_commits_api.py`：「查看过滤不触发预测」改为断言 `prediction` 行数不变 — `backend/tests/test_commits_api.py`

## 测试与验证

### 单元测试

- 命令：`cd backend; $env:PYTHONPATH="."; python -m pytest tests/ -o addopts="" -q`
- 证据：281 passed（与重构前一致，证明行为未漂移）

### 集成测试

- 同上（同一套件含 MySQL `jit_test` 集成路径）；标签落库、详情/列表联读、health 三态在重构后仍全绿

### 验收测试

- 按 `feedback-observability` 的既有 Scenario 回归：标记 → 详情可见 → `has_label` 过滤 → 撤销；health ok / degraded / 无模型
- 证据：`tests/test_feedback_api.py`（9 条）、`tests/test_health_api.py`（4 条）全通过

### 非功能验证

- 契约镜像：`tests/test_mirror.py` 13 条通过（路径集与字段集与重构前完全一致，证明对外契约零漂移）
- 前端构建：`cd frontend; npm run build` 通过（本 change 未改前端，用于确认无回归）

### 已知缺口

- `sync.py` / `prs.py` 的业务仍未下沉到服务层（链路长、风险高，留待后续 change）
- 未引入依赖注入，服务层仍直接 `with SessionLocal()`；后续若要单测业务需改为注入 session
