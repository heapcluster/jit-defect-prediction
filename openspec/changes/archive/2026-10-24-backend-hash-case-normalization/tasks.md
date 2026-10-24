# backend-hash-case-normalization — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/query-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-24 ｜ 状态：**已归档**（`2026-10-24-backend-hash-case-normalization`；PR #101 合入 main `c011463` 后于 `0773a49` 上归档，query-api +1 ADDED requirement；3.4 已完成，3.3 的 PO 裁定仍开放且不阻塞归档）
> 用户故事：无（缺陷修复）；对应 `docs/repo/defect-records.md` §2 的 D-09（P3）
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 代码修复与规格 delta

- [x] 1.1 `_check_hash()` 由只校验改为「校验并返回小写哈希」，docstring 写明调用方必须使用返回值 — 交付物：`backend/app/api/commits.py`；拒收条件（长度 40、十六进制字符集）逐字未改。
- [x] 1.2 `commit_detail()` 用归一化后的同名局部变量查四处（`commit` / `commit_feature` / 默认模型 `prediction` / 兜底 `prediction`），响应仍回显库内 `commit.commit_hash` — 交付物：同上；采用同名覆盖而非新变量，避免漏改任一查询点。
- [x] 1.3 规格 delta 定为 **ADDED** 独立 requirement「提交哈希大小写归一化」（4 个 Scenario：GET 大写/混合命中、归一化后仍不存在、非法字符仍拒收、POST 大小写幂等），不改任何既有 requirement 文本 — 交付物：`specs/query-api/spec.md`。理由与撞车复查见 design D6：#97（`on-demand-commit-prediction`，已合入 `4dc50aa`、change 未归档）已 MODIFIED 同一条「提交详情查询」，两份 MODIFIED 并存时后归档者会把先归档者整段抹掉；本 change 初版正是那种写法，本轮改掉。

## 2. 测试

- [x] 2.1 把钉住旧行为的 `test_detail_uppercase_hash_passes_validation_but_not_found` 改写为 `test_detail_uppercase_hash_is_normalized_to_the_stored_commit`：大写与混合大小写（`.upper()` / `.title()`）均 200，且 `data` 与小写请求**逐字段相等**、`data.commit_hash` 为库内小写值 — 交付物：`backend/tests/test_security_boundaries.py`。
- [x] 2.2 新增 `test_detail_unknown_hash_stays_40400_after_normalization`（库内不存在的哈希大小写两种形式都仍 40400 + `commit not found`），并在既有 `test_detail_hash_boundaries_return_40001` 参数里补 `G`×40（大写非十六进制仍 40001）— 交付物：同上。
- [x] 2.3 扩充既有 `test_predict_uppercase_hash_uses_normalized_key`：大写与小写各 POST 一次，`prediction` 表内 `_rows_for(C1, "fixture_v2") == 1` 且 `_rows_for(C1.upper(), ...) == 0` — 交付物：`backend/tests/test_predict_api.py`；未重构 predict 的内联校验（design D4）。
- [x] 2.4 跑定向与后端全量测试 + ruff — 交付物：本文件 §5 的真实输出；计数取自 junitxml，不以终端回显为准。

## 3. 缺陷记录与审阅

- [x] 3.1 `docs/repo/defect-records.md` 的 D-09 行更新为「🔧 修复已实现，change/PR 待复审合入（合入后再迁入 §1）」，并修正该行原本错位的「关联提交/change」列（原来填的是测试路径）— 交付物：`docs/repo/defect-records.md`；未在合入前写成已闭环。
- [x] 3.2 `openspec validate --strict` 通过后提交独立 PR，交苏哲勋复审 — 交付物：PR #101（https://github.com/heapcluster/jit-defect-prediction/pull/101），实现提交 `6a153b5`，已请求 sober-hub 复审；未合入，D-09 行仍留在 §2。
- [ ] 3.3 Open Question 1（`docs/backend/api-spec.md` 第 2 节是否补大小写口径）由 PO/SM 裁定后落地 — 交付形式：PR #101 评论回执；裁定前不改冻结契约。**2026-10-24 归档时仍开放**：归档不等待该裁定（代码行为已按 change 的 ADDED requirement 落地并合入）；若 PO 裁定为「补口径」，另立 change 改冻结契约，不在本 change 内追溯。
- [x] 3.4 PR #101 合入后把 D-09 行从 `docs/repo/defect-records.md` §2 迁入 §1 已闭环 — 交付物：单独 docs 提交；未合入前不得迁。**2026-10-24 已执行**（#101 合入为 `c011463` 之后）：§2 原行删除，§1 新增闭环行（状态 ✅、关联 PR #101 与归档名、证据测试 4 条、全量 145 passed @ `0773a49`），并在该行保留 Open Question 1 的遗留说明。

## 测试与验证（强制板块）

> 命令使用按 `data_model/environment.yml` 建好的 Python 3.12 环境（实测解释器 3.12.15）。本机 CLI 会吞掉 pytest 末行汇总，因此计数一律取自 `--junitxml` 的 testsuite 属性。本 change 不连 MySQL，SQLite 结果不冒充 MySQL 验证。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | `_check_hash()` 的归一化返回值与 `commit_detail()` 四处查询的大小写一致性 |
| 测试文件 | `backend/tests/test_security_boundaries.py` |
| 用例数与结果 | 与 `test_predict_api.py` 合跑 62 passed / 0 failed；全量 132 passed / 0 failed |
| 复现命令 | cwd=backend：`python -m pytest tests/test_security_boundaries.py tests/test_predict_api.py -q --junitxml=…` |
| 正向 | 小写、全大写（`A`×40）、混合大小写（`.title()`）三种形式返回同一提交的逐字段相同 `data`，`data.commit_hash` 为库内小写值 |
| 异常/边界 | 库内不存在的哈希（小写与大写）仍 40400 + `commit not found`；`g`×40、`G`×40、39 位、41 位、含符号仍 40001；缺令牌仍 40100（既有用例未回归） |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | SQLite 夹具上 GET 详情与 POST 预测对同一提交的大小写一致性，以及 `prediction` 复合键幂等 |
| 测试文件 | `backend/tests/test_predict_api.py`（`test_predict_uppercase_hash_uses_normalized_key`） |
| 用例数与结果 | 全量 132 passed / 0 failed（含本条） |
| 复现命令 | cwd=backend：`python -m pytest tests/` |
| 关键断言 | 大写 POST 返回 200 且回显小写；再以小写 POST 一次后 `(C1, fixture_v2)` 只有一行；以大写键查库为 0 行（证明落库用的是归一化值） |
| MySQL | 不在本 change 范围。方言差异见 `design.md` D2：MySQL 8 默认 `utf8mb4_0900_ai_ci` 大小写不敏感，可能复现不到该缺陷；SQLite 与任何大小写敏感 collation 必现。因此「MySQL 上没问题」不能作为反证 |

### 3. 验收测试

| 场景（本 change ADDED 的 4 个 Scenario） | 测试定位 |
|---|---|
| 大写或混合大小写哈希命中同一提交 | `backend/tests/test_security_boundaries.py::test_detail_uppercase_hash_is_normalized_to_the_stored_commit` |
| 归一化后仍不存在 → 40400 | `backend/tests/test_security_boundaries.py::test_detail_unknown_hash_stays_40400_after_normalization` |
| 非法字符仍 40001（含大写形式 `G`×40） | `backend/tests/test_security_boundaries.py::test_detail_hash_boundaries_return_40001` |
| 预测接口的大小写幂等 | `backend/tests/test_predict_api.py::test_predict_uppercase_hash_uses_normalized_key` |
| 相邻既有 requirement 不回归（「提交详情查询」的文本由 #97 的 delta 负责，本 change 不改它） | `backend/tests/test_commits_api.py::test_detail_unknown_hash`、`::test_detail_without_prediction_returns_nulls`、`::test_detail_features_and_explanation`（该文件本 change 未改动） |

复现：cwd=backend `python -m pytest tests/`；cwd=仓库根 `openspec validate backend-hash-case-normalization --strict` → `Change 'backend-hash-case-normalization' is valid`；`openspec validate --all --strict` → `Totals: 24 passed, 0 failed (24 items)`。

### 4. 非功能验证

| 维度 | 是否触及 | 证据与命令 |
|---|---|---|
| 性能 | 否 | 只在既有查询前多一次 `lower()`；不新增查询、不加索引、不改库；未跑压测 |
| 安全 | 是 | 拒收条件逐字未改，并新增大写非十六进制 `G`×40 参数证明归一化没放宽校验；缺令牌/畸形参数既有用例全过 |
| 可靠 | 是 | GET 与 POST 对同一输入结论一致，消除误导性 40400；大小写两次 POST 只留一行 |
| 易用 | 是 | 评审员从别处复制到大写哈希也能查到提交，且响应回显库内小写值可直接复用 |
| 维护 | 是 | 归一化收敛到 `_check_hash()` 一处；cwd=仓库根 `python -m ruff check backend/app/api/commits.py backend/tests/test_security_boundaries.py backend/tests/test_predict_api.py` → `All checks passed!` |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| PR #101 未合入 | 已创建并请求 sober-hub 复审，等 CI 与非作者审阅 | backend 吕建江 + 苏哲勋 | 合入后执行 3.4：把 D-09 行迁入 §1 已闭环；未合入前不写「已修复闭环」 |
| `docs/backend/api-spec.md` 是否补大小写口径 | 契约已冻结 v1.5，不自行改 | 苏哲勋（PO）+ 蒋励（SM） | 见 `design.md` Open Questions 1，PR 内请裁定 |
| MySQL 实机复现 | `jit` 账号只有 `jit_defect`.* 权限、无 CREATE DATABASE，隔离空库未授权 | backend 吕建江 + 苏哲勋 | 与 #100 tasks 3.1/3.2 合并到同一次已授权实跑；本 change 不以 SQLite 结果冒充 |
| `predict.py` 内联校验与 `_check_hash` 重复 | 属重构，超出缺陷修复范围（AGENTS.md 第五节） | backend 吕建江 | 如需统一另开 change，本次只加回归测试锁住一致性 |

#### 2026-10-24 本轮执行证据

- 工作树 `D:/TeamWork/jit-backend-hash`，分支 `fix/backend/hash-normalization`，基线 main `f5ca61d`（已含 #96/#97/#100）。
- 解释器：`C:/Users/simple/anaconda3/envs/jit-defect-prediction/python.exe`，Python 3.12.15、pytest 9.1.1、SQLAlchemy 2.0.54、FastAPI 0.141.1、ruff 0.16.8。
- cwd=backend：`python -m pytest tests/test_security_boundaries.py tests/test_predict_api.py -q --junitxml=…` → exit 0，`tests=62 failures=0 errors=0 skipped=0 time=2.693`。
- cwd=backend：`python -m pytest tests/ -q --junitxml=…` → exit 0，`tests=132 failures=0 errors=0 skipped=0 time=3.365`。
- cwd=仓库根：`python -m ruff check` 三个改动文件 → `All checks passed!`；`openspec validate backend-hash-case-normalization --strict` → valid；`openspec validate --all --strict` → `Totals: 24 passed, 0 failed (24 items)`。
- 改动文件：`backend/app/api/commits.py`（2 处）、`backend/tests/test_security_boundaries.py`（改写 1 条 + 新增 1 条 + 参数 1 项）、`backend/tests/test_predict_api.py`（扩充 1 条）、`docs/repo/defect-records.md`（D-09 行）。未改数据库、未改契约文档、未改前端与模型线。
- 未连 MySQL、未写库、未提交/推送前本节数字即上述实测；合入与裁定结果留待 3.2/3.3 回填。

#### 2026-10-24 第二轮：delta 由 MODIFIED 改 ADDED（撞车复查）

- 触发：按「出 delta 前先扫同名 requirement」复查（`grep -rl "^## MODIFIED Requirements" openspec/changes/*/specs/ | grep -v archive`，再逐文件列 `### Requirement:`），发现 main `065c83a` 上 **#97 `on-demand-commit-prediction`（已合入 `4dc50aa`、change 未归档）也 MODIFIED 了「提交详情查询」**，其文本已含 `docs/model/feature-columns.md` 与「在线模型与历史默认模型不同 → 回退到该提交已有模型中版本序最新一条」语义（对应 `backend/app/api/commits.py:136-141`）。本 change 初版对同一条出了 MODIFIED，两份并存时后归档者会把先归档者整段抹掉（design D6）。
- 处置：delta 改为 **ADDED** 独立 requirement「提交哈希大小写归一化」，Scenario 由 3 个扩为 4 个（补 `POST /api/predict` 的大小写幂等，测试为 2.3 那条），既有 requirement 文本一律不动。改后上述 MODIFIED 扫描结果里不再有本 change，与 #97 的归档顺序互不影响。
- 代码与测试**本轮未改**（只动 `specs/query-api/spec.md`、`proposal.md`、`design.md`、`tasks.md`），故 §1–§4 的定向 62 / 全量 132 / ruff 结果继续有效；规格重跑：`openspec validate backend-hash-case-normalization --strict` → `Change 'backend-hash-case-normalization' is valid`；`openspec validate --all --strict` → `Totals: 24 passed, 0 failed (24 items)`。
- 同一轮复查在 PR #82 上发现两处同类撞车（与 #96「模型加载」、#97「提交详情查询」），已在该 PR 内撤出对应 requirement（head `40fd222`，其 design D6 有全量撞车表）。**这不是别人 PR 的问题、是我自己两个 PR 都犯了同一个错**，故把复查命令固化进两个 change 的归档前判据。
