# default-model-resolution — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`、`specs/query-api/spec.md`
> 负责人：backend 吕建江｜ 创建：2026-10-28 ｜ 状态：进行中（本地全量回归通过，CI 与评审待完成）
> 关联需求：无（工程化：默认模型口径收口 + 同步判据修正）
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 后端实现（backend）

- [x] 1.1 新增 `backend/app/services/champion.py` 作为全站唯一解析入口 — 交付物：`resolve(session)`，候选**只限已加载模型**，三步顺序见 `specs/predict-api/spec.md`
- [x] 1.2 `services/commits.default_model_in_table()` 改为委托 1.1，删除本文件内的重复解析 — 交付物：读路径（列表/详情/趋势）不再自带规则
- [x] 1.3 `services/predict.resolve_model_name(None)` 改为调 1.1，空结果时按注册表冠军兜底、注册表为空抛 50000 — 交付物：写路径与读路径同源
- [x] 1.4 `api/sync._unpredicted()` 增加 `model_name` 过滤（`_AUTO` 哨兵 → 每批解析一次；显式传 `None` 保留“任意模型有行即完成”旧语义） — 交付物：默认模型缺行的提交不再被永久跳过

## 2. 规格与契约（openspec / docs）

- [x] 2.1 `specs/predict-api/spec.md`：ADDED「有效默认模型解析」「同步候选按有效默认模型判断缺行」 — 不用 MODIFIED「在线预测入口」，原因见 design D5（与进行中的 `on-demand-commit-prediction` 撞同名 Requirement 会被 `deltas` 门禁判红）
- [x] 2.2 `specs/query-api/spec.md`：MODIFIED「风险列表查询」「趋势聚合查询」，文本由 `main` 活规格整块复制后定点替换（脚本生成，避免手抄丢字）；顺带订正趋势阈值句（活规格仍写“固定常量 0.5”，实现自 #172 起读运行时配置）
- [x] 2.3 回退首版对活规格 `openspec/specs/query-api/spec.md` 的直接编辑 — 交付物：`git diff main -- openspec/specs/query-api/spec.md` 为空（见 design D6）
- [x] 2.4 契约三 [历史版 `docs/backend/api-spec.md`](https://github.com/heapcluster/jit-defect-prediction/blob/100008e787c8902c35760c9cef6d61d279d921b7/docs/backend/api-spec.md)：§5 行为句改为「有效默认模型尚无 `prediction` 行」；§17 补降级规则（候选限已加载、空库读写一致、注册表空 → 50000）；变更日志记 2.3；头部版本号补到 v2.3
- [x] 2.5 门禁自检：`infra/check_spec_references.py deltas` 与 `links` 均 passed；`openspec validate default-model-resolution --strict` valid；`openspec validate --specs --strict` 12 passed

## 3. 测试（backend）

- [x] 3.1 新增 `backend/tests/test_champion_single_source.py` 10 条（临时 SQLite 文件，不依赖 MySQL 测试库） — 覆盖冠军有行/无行降级/历史未加载模型不被选中/注册表空 50000/显式名 40001/同步判据模型感知/`None` 旧语义/`limit` 截断
- [x] 3.2 夹具与既有断言对齐“已加载模型”语义 — `conftest.py` 预置行改用注册表内的 `fixture_v2`；`test_commits_api.py` 的高版本历史模型改为临时注册项；`test_ops_api.py`/`test_prs_api.py` 的预置行改 upsert，避免与夹具行撞唯一键
- [x] 3.3 本机全量回归：`pytest -q` → **344 passed**（隔离 MySQL 实例，`--no-defaults --port=13317`，不触碰 `jit_demo`/`jit_defect`）

## 4. 交付（PR #186）

- [ ] 4.1 推送并由 CI 复核全量 pytest（本机 `jit` 账号无 `jit_test` 建库权限，全量回归靠隔离实例 + CI 双证）
- [ ] 4.2 评审：sober-hub（格式与 openspec 把关）、jolly326（冠军降级口径拍板，见 design「Open Questions」）
- [ ] 4.3 合入后按 `openspec` 流程归档本 change（归档时须把 `on-demand-commit-prediction` 里「在线预测入口」的旧缺省模型句一并对齐）

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、
> **集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**

### 1. 单元测试（本 change 新增/改动代码的作者负责）

| 项 | 内容 |
|---|---|
| 覆盖对象 | `services/champion.resolve`、`services/commits.default_model_in_table`、`services/predict.resolve_model_name`、`api/sync._unpredicted` |
| 测试文件 | `backend/tests/test_champion_single_source.py`（新增 10 条）；受影响既有：`test_champion_model.py`、`test_commits_api.py`、`test_predict_api.py`、`test_trends_api.py`、`test_ops_api.py`、`test_prs_api.py`、`test_quality_api.py` |
| 用例数与结果 | 10 条新增 ｜ passed；全量 344 条 ｜ passed |
| 复现命令 | `cd backend && python -m pytest tests/test_champion_single_source.py -q`（全量：`python -m pytest -q`，需 MySQL 测试库） |
| 正向用例 | 冠军 `fixture_v2` 有行 → `resolve` 返回 `fixture_v2`，列表与缺省 predict 同名同分 |
| 异常 / 边界用例 | 库中只有未加载的 `xgb_v1` 历史行、注册表为 `fixture_v1/v2` → 缺省 predict 不得 40001，须用注册表冠军；注册表清空 → 50000 且 message 为 `internal error` |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 缺省模型口径贯穿 `GET /api/commits`、`GET /api/commits/{hash}`、`GET /api/trends`、`POST /api/predict`、`POST /api/sync`、`GET /api/prs*`；阈值运行时配置与趋势计数 |
| 测试文件 | `backend/tests/`（`client` 夹具走真实 MySQL `jit_test` + TestClient） |
| 用例数与结果 | 344 条 ｜ passed（隔离 MySQL 实例，端口 13317，独立 datadir） |
| 复现命令 | `cd backend && python -m pytest -q`（前置：`infra/setup_mysql.py` 建好 `jit_test`） |
| 关键断言 | 同一提交在列表/详情/predict 三处 `model_name` 与 `risk_score` 一致；`(commit_hash, model_name)` 幂等单行；错误码只用 0/40001/40100/40400/50000 |

### 3. 验收测试（交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/predict-api/spec.md`「有效默认模型解析」5 个 Scenario +「同步候选按有效默认模型判断缺行」3 个；`specs/query-api/spec.md` 两个 MODIFIED Requirement 的新增边界 Scenario |
| 用例数与结果 | 8 个 Scenario 已由 §1 的 10 条用例逐条覆盖 ｜ passed |
| 复现命令 / 步骤 | `cd backend && python -m pytest tests/test_champion_single_source.py tests/test_champion_model.py -q` |
| 证据归档 | 本机全量日志 `D:\TeamWork\Temp\pr186-full2.log`（344 passed）；**待补**：合入后把 CI 运行链接写回本行 |

### 4. 非功能验证（本 change 触及则必填，否则写「本 change 不触及」）

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否（解析每请求多一次 `model` 表小查询，量级十几行；未做压测） | 无 |
| 安全 | 是（注册表为空时不得回显模型路径） | `test_empty_registry_reports_internal_error_even_with_historical_predictions`：断言 message 为 `internal error` |
| 可靠 | 是（空库、历史模型卸载、显式 `None` 旧语义、`limit` 截断） | 同上文件 4 条边界用例 |
| 易用 | 否（前端回显由 #183 承载，本 change 不改前端） | 无 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 本机无法跑官方 `jit_test` 全量回归 | `jit` 账号只有 `jit_defect`/`jit_demo` 权限，建库需 root；已用独立 datadir 的隔离实例代替 | infra 苏哲勋（`infra/setup_mysql.py` 的 root 步骤） | 待排期 |
| 「冠军无行时降级」尚未获评审确认 | 属产品口径，design「Open Questions」已列；PR 里请 jolly326 拍板 | backend 吕建江 → jolly326 | PR #186 评审 |
| `on-demand-commit-prediction` 里「在线预测入口」的旧缺省模型句未更新 | 该 change 进行中（2 项未勾），不能为消解冲突提前归档；本 change 用 ADDED 承载并在 delta 内点名 | backend 吕建江 | 该 change 归档时 |
| 归档动作未做 | 需先合入 + 评审通过 | backend 吕建江 | 合入后 |
