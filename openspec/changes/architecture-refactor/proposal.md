# 后端分层与重复代码收敛

## Why

`feedback-observability` 交付后，同一段逻辑在多个路由里各写了一份，新增字段时改一处漏一处：

1. **`iso_z`（UTC ISO 8601 带 Z）四份**：`commits.py` / `feedback.py` / `health.py` / `predict.py` 各写一遍。契约三要求时间字段统一 UTC，但只要有一处漏掉 Z 后缀，前端就会拿到两种时间格式，而这种 bug 只有联调时才暴露。
2. **commit_hash 校验三份且三个名字**：`predict.py` 的 `_normalize_hash`、`commits.py` 的 `_check_hash`、`feedback.py` 的 `normalize_hash`，规则相同（40 位十六进制、放行大写但查库用小写，D-09）却各写各的。
3. **查询组装逻辑散落在路由里**：默认模型口径（`default_model_in_table`）、特征 dict 组装、解释项生成、人工标签读取都写在 `commits.py` 内部，其它模块要用只能跨路由 import（`trends.py` 就 `from app.api.commits import default_model_in_table`）——路由之间互相 import 是分层被破坏的信号。
4. **路由既做校验又做 SQL**：`feedback.py` / `health.py` 里直接写 `with SessionLocal()` 与 SQL，单元测试要测业务只能走 HTTP，或者去 monkeypatch 路由模块的私有变量。

本 change 做纯重构：**对外行为一字不改**（字段、错误码、排序、分页、口径全部保持原样），只把重复收敛、把数据访问下沉到服务层。

## What Changes

- **新增 `app/timeutil.py`**：`iso_z(value)`（None 原样返回）+ `now_naive_utc()`；四处路由改用同一份。
- **新增 `app/validate.py`**：`normalize_commit_hash()`（非法 → 40001，返回小写）；`predict` / `commits` / `feedback` 三处路由改用同一份，删除各自的私有实现与 `HASH_HEX` 常量。
- **新增 `app/services/` 服务层**：
  - `services/commits.py`：默认模型口径 `default_model_in_table`、特征 dict `feature_dict`、解释项 `explanation_for`、人工标签 `label_for`、已确认哈希子查询 `labeled_hashes_stmt`。
  - `services/feedback.py`：人工标签写入/撤销。
  - `services/health.py`：运行状态聚合（DB / 模型 / 三条计数）。
- **路由变薄**：`api/feedback.py` 与 `api/health.py` 只剩入参校验 + `ok(...)`；`api/commits.py` 保留参数校验与区间语义（`_parse_time`），查询组装转调服务层。
- **修正跨路由 import**：`trends.py` 改为从 `app.services.commits` 导入 `default_model_in_table`，不再从路由模块取业务函数。

## Capabilities

### Modified Capabilities

- `query-api`：行为不变，仅内部实现下沉到服务层（列表 / 详情 / 覆盖的组装逻辑）。
- `feedback`：行为不变，业务下沉到 `app/services/feedback.py`。
- `observability`：行为不变，聚合下沉到 `app/services/health.py`。

（本 change 是纯重构，**不新增 capability、不改任何对外字段 / 路径 / 错误码**，故无 ADDED Requirements。）

## Impact

- 后端：新增 `app/timeutil.py`、`app/validate.py`、`app/services/{__init__,commits,feedback,health}.py`；`app/api/{commits,feedback,health,predict,prs,trends}.py` 改为调用共享模块。
- 测试：`test_health_api.py` 的 monkeypatch 目标从 `app.api.health.SessionLocal` 改为 `app.services.health.SessionLocal`；`test_commits_api.py` 的「查看过滤不触发预测」改为断言 `prediction` 行数不变（原用例 patch 了 `app.api.commits.config`，重构后该模块不再导入 config）。
- 数据库：无迁移、无结构变化。
- 契约：`docs/backend/api-spec.md` **无需改动**（对外行为完全一致）。

## 不做什么

- `MUST NOT` 改变任何对外行为：字段名、路径、错误码、排序与分页口径一律保持原样。
- `MUST NOT` 借重构顺手改功能（阈值、过滤语义、解释排序都不动）。
- **不做全量服务化**：`sync.py` / `prs.py` 的业务暂不下沉（链路长、风险高，留待后续 change）。
- **不做前端改动**（本 change 纯后端）。
- 不引入依赖注入框架或新第三方库。
