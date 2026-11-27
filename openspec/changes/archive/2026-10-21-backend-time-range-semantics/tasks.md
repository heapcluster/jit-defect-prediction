# backend-time-range-semantics — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/query-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-10 ｜ 状态：**已归档**（2026-10-21，`openspec archive`；余 3.2 一项跨线待办随归档留档，未伪勾）
> 用户故事：A 组第 1 条「查看风险提交列表」＋第 5 / 6 条「缺陷趋势看板」「趋势按周/月切换」（时间范围筛选是这三条的过滤条件，映射见 `docs/repo/user-story-traceability.md`）；触发缺陷 Issue #61
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 后端实现与单元测试（A1 · Issue #61）

- [x] 1.1 `_parse_time` 增加 `role` 参数：end 侧纯日期串按当天 `23:59:59.999999` 收尾，start 侧保持 `00:00:00`；紧凑基本格式（头 8 位数字后接 `T` 或结束，含 `Z`/偏移变体）拒收 40001；`commits` 与 `trends` 两调用点同步 —— 交付物：`backend/app/api/commits.py`（函数定义 + 调用点）、`backend/app/api/trends.py`（调用点）
      —— 完成判据：代码合入且本文件「测试与验证」§1 的 6 条新增用例全绿。完成：提交 `2b366ac`
- [x] 1.2 回归测试 6 条：列表 end 纯日期含全天、end 带时间分量不变、start 纯日期仍午夜、趋势 end 纯日期含全天、列表/趋势紧凑基本格式（含 `20260803T090000Z`、`20260803T090000+08:00` 变体）拒收 40001 —— 交付物：`backend/tests/test_commits_api.py`（4 条）、`backend/tests/test_trends_api.py`（2 条）
      —— 完成判据：cwd=`backend`，`python -m pytest tests/ -q` 全绿且新用例覆盖上述输入。完成：45 passed / 45（提交 `2b366ac`；苏哲勋 2026-10-16 在隔离 Python 3.12.13 环境独立复跑亦 45 passed）

## 2. 契约与引用同步（A1 / A5 · 跨线口径）

- [x] 2.1 `docs/backend/api-spec.md` 升 **1.5**：§一 新增「时间范围语义」表行（闭区间 + 纯日期串解释 + 紧凑格式拒收 + 前端 MUST NOT 调用侧补丁及理由）、文件头版本、新增「变更日志」节（1.5 前历史指向旧 `docs/contracts/api-format.md` 的 git 历史）—— 交付物：`docs/backend/api-spec.md`
      —— 完成判据：契约行可判定（每条能写成断言）、变更日志含「改了什么 / 为什么」。完成：提交 `2b366ac`
- [x] 2.2 引用点 1.4 → 1.5 与路径重定向：backend docstring 7 处、`backend/README.md` 的 `docs/contracts/*` 路径 4 处（10-11 12:41 归属裁定：后端线仅此一文件）、`docs/backend/README.md` 两处「契约三 v1.4」现行口径引用 → v1.5、`backend/tests/test_commits_api.py` 一处 docstring 误写「契约三 2.0」→ 1.5 —— 交付物：上述四份文件
      —— 完成判据：`grep -rn "docs/contracts" backend/` 零残留；后端线文件中「现行契约版本」引用一律 1.5（历史台账行除外）。完成：提交 `2b366ac` + 本轮格式补齐提交
- [x] 2.3 本 change 的 `design.md` Context 标明「本 change 前契约为 v1.4」，避免与 2.1 的 1.5 读成同一版本 —— 交付物：`openspec/changes/backend-time-range-semantics/design.md`
      —— 完成判据：Context 段版本指向明确。完成：本轮格式补齐提交

## 3. 跨线待办（不在本 PR，写明交付给谁、以什么形式）

- [x] 3.1 前端月粒度 `periodToRange` 的 end 改送当月最后一日；`toEndTime` 兜底与 `docs/frontend/pages.md` 过渡句移除 —— 交付给：frontend 刘帅华；形式：PR #60 内 `frontend/src/` 代码改动
      —— 完成判据：main 上 `periodToRange` 周粒度送「周一..周日」、月粒度送「1 日..月末」，且不存在调用侧补 `T23:59:59` 的兜底。完成：**PR #60 已于 2026-10-16 07:29 合入 main**；核对 `frontend/src/views/TrendBoard.vue:253`（`periodToRange`：week → `monday..monday+6d`；month → `Date.UTC(year, month, 0)` 即当月最后一日），`git grep -n "toEndTime" main -- frontend/` **零命中**，`git grep -nE "23:59" main -- frontend/src` 零命中
- [ ] 3.2 前端线文档的契约版本引用同步：`docs/frontend/pages.md` 第 88 行、`docs/frontend/README.md` 第 5 行仍写「契约三 v1.4」（现行版本已是 **v1.5**）—— 交付给：frontend 刘帅华；形式：**另开新 PR**（#60 已合入，按 sober-hub 2026-10-16 复审意见「不再往已合并 #60 追加」）；本 PR 不动前端线文件
      —— 归档时复核（2026-10-21，main `e46624b`，命令 `grep -rn "契约三 v1\\.4" docs/frontend/ docs/common/`）：两处仍在，行号未变（`docs/frontend/pages.md:88`、`docs/frontend/README.md:5`）；另扫出同类第三处 `docs/common/test-plan.md:5`（「依据：…（契约三 v1.4）」），属公共文档、蒋励统稿范围，一并在归档后向两位交接人点出。本条保持未勾。
- [x] 3.3 归档本 change：delta 落 `openspec/specs/query-api/spec.md`，并同步该文件首段「契约三 1.4」→ 1.5 —— 交付给：backend 吕建江（自己）；形式：归档 PR（`openspec archive backend-time-range-semantics`）。前置已满足：#62 于 2026-10-16 07:49 由 sober-hub 合入 main（`7844f8e`）；待本 PR（集成证据）合入后紧接着提
      —— 完成判据：归档目录 `openspec/changes/archive/2026-10-21-backend-time-range-semantics/` 存在、`openspec/specs/query-api/spec.md` 含本 change 的两条 MODIFIED requirement 与 4 条新增 Scenario、首段版本为 1.5。完成：2026-10-21 在本归档 PR 内执行（前置 #75 已由 sober-hub 合入 main `07f4309`）。cwd=仓库根 `openspec archive backend-time-range-semantics -y` 输出 `Applying changes to openspec/specs/query-api/spec.md: ~ 2 modified` + `archived as '2026-10-21-backend-time-range-semantics'`（CLI 同时提示 `Warning: 2 incomplete task(s)`，即本条 3.3 与 3.2 前端线待办，见下）。落地核对：`grep -n "契约三 1.5" openspec/specs/query-api/spec.md`（首段第 4 行，本 PR 手工同步，delta 结构承载不到 Purpose 段）；新增 Scenario 可点回 `grep -c "Scenario: 纯日期串 end 含结束日全天\\|Scenario: 周下钻纯日期串不丢结束日" openspec/specs/query-api/spec.md` → 2

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、**集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**
> 统一复现口径 —— **cwd：仓库根下的 `backend/`**；解释器：仓库 `.venv`（Windows `..\.venv\Scripts\python.exe`，Linux/macOS `../.venv/bin/python`）；环境：Windows 11 / Python 3.12.7 / fastapi 0.141.1 / sqlalchemy 2.0.54 / pytest 9.1.1 / SQLite 夹具（`backend/tests/conftest.py`）；被测提交：单元 45/45 与集成 11/11 均在 head `9073cea` 上执行 —— 该 head 随 **PR #62 于 2026-10-16 07:49 由 sober-hub 合入 main（`7844f8e`）**，源分支已按仓库设置自动删除；证据文件与本次回写由后续 PR 承接，**不含任何应用代码改动**。

### 1. 单元测试（本 change 新增/改动代码的作者负责 · 吕建江）

| 项 | 内容 |
|---|---|
| 覆盖对象 | `backend/app/api/commits.py::_parse_time`（`role="end"` 纯日期收尾 / `role="start"` 保持午夜 / 紧凑基本格式拒收 / 带时间分量原样 / 带时区先转 UTC）、`backend/app/api/commits.py::list_commits` 与 `backend/app/api/trends.py::trends` 的 end 侧调用点 |
| 测试文件 | `backend/tests/test_commits_api.py`、`backend/tests/test_trends_api.py` |
| 用例数与结果 | 本 change 新增 **6** 条 ｜ passed；后端全套 **45** 条 ｜ passed（0 failed，2 条依赖弃用 warning） |
| 复现命令 | cwd=`backend`：`python -m pytest tests/ -q`（只跑本 change 新增 6 条：`python -m pytest tests/test_commits_api.py tests/test_trends_api.py -q -k "end_pure_date or time_component or start_pure_date or compact_basic"`） |
| 正向用例 | `GET /api/commits?start_time=2026-08-03&end_time=2026-08-03`（夹具提交 `committed_at=2026-08-03T09:00:00`）→ `code=0`、`data.total=1`、命中该提交（结束日全天被含，不再丢当天） |
| 异常 / 边界用例 | `end_time=20260803` / `20260803T090000Z` / `20260803T090000+08:00`、`start_time=20260803` → HTTP 400 + `code=40001`，`message` 含参数名与合法写法；`end_time=2026-08-03T08:59:59` → 当天 09:00 的提交**不**被包含（显式时间分量不被收尾规则改写）；`start_time=2026-08-03` → 仍按当天 `00:00:00`（不一刀切） |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 本 change 的区间语义 ↔ **真起服务**（uvicorn，不用 TestClient）↔ SQLite 种子库 ↔ 列表 / 趋势 / 详情三接口的跨口径一致性；前端三页面端到端另计（见 §5） |
| 测试文件 | `backend/scripts/evidence/integration-time-range-2026-10-16.md`（本轮新增：11 条真 HTTP 断言 + 原始响应 verbatim + 复现步骤；**其中 4 条跨接口一致性对账 —— 列表 `total` == 周桶之和 == 月桶 == 周下钻 —— 见该文件 §2 的专表**，非仅文件名罗列）；前端侧联调记录为 `docs/frontend/integration-log.md`（刘帅华，随 #60 已进 main） |
| 用例数与结果 | 后端侧 **11** 条 ｜ 全部符合预期（其中 4 条为跨接口一致性断言）；前端三页面端到端 **0** 条 ｜ **未执行**（前置：#62 合入 + F4 联调窗口，不写成已完成） |
| 复现命令 | cwd=`backend`：`python -m scripts.seed_dev_data` → `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010` → 按证据文件 §4 的 curl 逐条打（`DATABASE_URL` 指仓库外的 SQLite 文件、`API_TOKEN` 走环境变量，均不入库）。执行记录：分支 head `9073cea`，2026-10-16，Windows 11 / Python 3.12.7 |
| 关键断言 | ① 同区间 列表 `total=3` == 趋势周桶 `2026-W31:2 + 2026-W32:1`；② **周下钻** `start=2026-07-27&end=2026-08-02` 得 2 条 == 同区间周桶 `W31:2`（修复前只返回 1 条，即 #61 原现象）；③ 月桶 `2026-08:3` == 列表 3 条；④ 紧凑格式 `20260803` / `20260803T090000Z` → 400 + `40001`，message 只含参数名与合法写法（无堆栈 / SQL）；⑤ 无 `X-API-Key` → 401 + `40100`；⑥ `end=2026-08-02` 与 `end=2026-08-03T08:59:59` 均返回 2 条 —— 证明收尾规则没有外溢成「多给一天」 |

### 3. 验收测试（交付时，按 `specs/query-api/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | `openspec/changes/backend-time-range-semantics/specs/query-api/spec.md`：MODIFIED「风险列表查询」「趋势聚合查询」两条 requirement 的时间过滤 SHALL/MUST（闭区间、纯日期串解释、紧凑格式拒收）+ 本 change 新增的 4 条 Scenario |
| 用例数与结果 | spec 共 **9 条 Scenario**（本 change 新增 4 条 + 既有 5 条），下表 9 行逐条对回、全部有测试可点回 ｜ 已由单元测试走通 PASS；另有 **2 行 requirement 级补充测试**（趋势侧紧凑格式拒收、start 侧护栏 —— 出自 requirement 正文的 MUST/SHALL，**不是独立 Scenario**，计数上与 9 条分开算）；其中 4 条新增 Scenario 另有**真服务端到端**复核（§2 的 11 条断言，A/D/E/F/G/H/I 对应）｜ 三页面 + 录屏的课上验收 0 条 ｜ **未执行**（10/23 演示） |
| 复现命令 / 步骤 | ① cwd=`backend`：`python -m pytest tests/test_commits_api.py tests/test_trends_api.py -q`；② cwd=仓库根：`openspec validate --all --strict` → 本 change `✓ change/backend-time-range-semantics`，全量 **14 passed / 0 failed**（2026-10-16 复测；此前 `frontend-integration` 空 delta 的失败项已随 #60 合入修好）；③ 真服务复核按 `backend/scripts/evidence/integration-time-range-2026-10-16.md` §4；④ 三页面端到端按 `docs/repo/demo-script-sprint1.md` 的「时间范围筛选」正向 + 异常用例走（蒋励收口） |
| 证据归档 | 本文件 §1 / §3 两表 + `backend/scripts/evidence/integration-time-range-2026-10-16.md` + PR #62 复审记录（sober-hub 2026-10-13 通过功能判断、2026-10-16 独立环境 45 passed）；端到端录屏待 10/23 归档至 `docs/repo/` |

Scenario → 测试定位（9 条 Scenario + 2 条 requirement 级补充测试；仓库相对路径，逐条可点回）：

| # | Scenario（spec 原文标题） | 输入 | 预期 | 测试定位 | 结果 |
|---|---|---|---|---|---|
| 1 | 纯日期串 end 含结束日全天（**新增**·列表侧） | `start_time=2026-08-03&end_time=2026-08-03` | 含当天 09:00 提交，`total=1` | `backend/tests/test_commits_api.py::test_end_pure_date_includes_whole_end_day` | PASS |
| 2 | 带时间分量的 end 按原样（**新增**·列表侧） | `end_time=2026-08-03T08:59:59` 与 `T09:00:00` | 前者 `total=1`（不含 09:00）、后者 `total=2` | `backend/tests/test_commits_api.py::test_end_with_time_component_unchanged` | PASS |
| 3 | 紧凑基本格式日期被拒（**新增**·列表侧） | `start_time/end_time=20260803`、`20260803T090000Z`、`20260803T090000+08:00` | 400 + `40001`，message 指参数名 | `backend/tests/test_commits_api.py::test_compact_basic_format_rejected` | PASS |
| 4 | 周下钻纯日期串不丢结束日（**新增**·趋势侧） | `/api/trends?start_time=2026-08-03&end_time=2026-08-03` | 单周桶 `period=2026-W32`、`commit_count=1` | `backend/tests/test_trends_api.py::test_end_pure_date_includes_whole_end_day` | PASS |
| 5 | 默认排序与分页（既有，不回归） | 不带参数 | 按 `risk_score` 降序、第 1 页 20 条 | `backend/tests/test_commits_api.py::test_list_sorted_and_paged` | PASS |
| 6 | 筛选结果为空（既有，不回归） | `min_risk` 过滤到空 | `code=0`、`items` 空、`total=0` | `backend/tests/test_commits_api.py::test_min_risk_filter_empty_is_not_error` | PASS |
| 7 | 周粒度聚合（既有，不回归） | 默认参数 | `series` 按周升序、`period` 形如 `2026-W30` | `backend/tests/test_trends_api.py::test_week_aggregation` | PASS |
| 8 | 粒度取值非法（既有，不回归） | `granularity=day` | 400 + `40001` | `backend/tests/test_trends_api.py::test_invalid_granularity` | PASS |
| 9 | 时间范围内无数据（既有，不回归） | 2030 年区间 | `code=0`、`series` 空 | `backend/tests/test_trends_api.py::test_empty_range_is_not_error` | PASS |
| 补1 | **非独立 Scenario** —— 趋势侧紧凑格式拒收，出自 requirement「趋势聚合查询」正文的「紧凑基本格式拒收 40001」，与 Scenario 3 同口径 | `/api/trends?end_time=20260803`（含 `Z` / `+08:00` 变体） | 400 + `40001` | `backend/tests/test_trends_api.py::test_compact_basic_format_rejected` | PASS |
| 补2 | **非独立 Scenario** —— start 侧护栏，出自 requirement 正文的 SHALL「start 纯日期串 = 当天 `00:00:00`」 | `start_time=2026-08-03` | 含当天全部提交，不随 end 收尾规则变 | `backend/tests/test_commits_api.py::test_start_pure_date_still_midnight` | PASS |

### 4. 非功能验证（本 change 触及则必填）

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否（只改参数解析，未新增查询/循环） | 沿用 `backend/scripts/evidence/perf-real-2026-09-20.md`（p95 21.6ms < 500ms）；本 change 未重跑压测，见 §5 缺口 |
| 安全 | 是（畸形/紧凑时间串必须拒收且不泄露内部信息） | 单元层：`backend/tests/test_commits_api.py::test_compact_basic_format_rejected`、`backend/tests/test_trends_api.py::test_compact_basic_format_rejected`；真服务层：`backend/scripts/evidence/integration-time-range-2026-10-16.md` 的 E / F（400 + `40001`，message 只含参数名与合法写法，无堆栈 / SQL）与 K（无令牌 401 + `40100`）；既有 `backend/scripts/evidence/security-2026-09-20.md` |
| 可靠 | 是（空区间不报错、start 语义与既有查询不受影响、跨接口口径一致） | `backend/tests/test_trends_api.py::test_empty_range_is_not_error`、`backend/tests/test_commits_api.py::test_min_risk_filter_empty_is_not_error`、`backend/tests/test_commits_api.py::test_start_pure_date_still_midnight`（全套 45 条无回归）；真服务层：证据文件 §2 的 4 条一致性断言（列表 == 周桶之和 == 月桶 == 下钻结果） |
| 易用 | 否（三态与提示文案属前端线） | 由 `docs/frontend/integration-log.md`（刘帅华，随 #60 已进 main）覆盖 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| **三页面端到端 + 录屏未执行**（后端侧集成已于 2026-10-16 执行完毕，见 §2） | 前置已解除：**#62 于 07:49、#60 于 07:29 均已合入 main（`7844f8e`）**；本轮的 11 条断言是在 PR 分支 head `9073cea`（= 合入内容）上起真服务 + SQLite 种子做的，剩「三页面在 main 上点击走一遍 + 录屏」与前端侧 `docs/frontend/integration-log.md` 里标 ⏳ 的「日期末秒」项复核改判 | backend 吕建江 + frontend 刘帅华 + 蒋励（录屏） | 2026-10-23 前 |
| 真 MySQL 下的联调未跑（`prediction` 唯一索引并发双插回落） | 本轮集成用 SQLite 种子库；Issue #73 的两处零覆盖缺口**已于 2026-10-21 随 #79 合入 main（`62f6a18`）关闭**：月粒度 3 条 + 周下钻保周日 1 条（`backend/tests/test_trends_api.py::test_month_aggregation_buckets_by_calendar_month` 等）、建表索引自检 3 条（`backend/tests/test_db.py`，含 SQLite 方言坑：`get_unique_constraints()` 无 `unique` 键）；后端全套现为 **100 条**。仍缺的是可起 MySQL 的集成夹具与并发双插实测 | backend 吕建江 | Sprint 2 W1（缺口剩余部分另立，不重开 #73） |
| 端到端验收未执行（演示脚本「时间范围筛选」正向 + 异常） | 10/23 课上验收统一演示，录屏由 SM 收口 | 蒋励（脚本/录屏）+ 吕建江（后端） | 2026-10-23 |
| 压测未按新解析层重跑 | 改动仅在参数解析，无新增 I/O；课程只要求 p95 达标且已有真模型证据 | backend 吕建江 | Sprint 2（若 CI 门禁 PR #72 要求则提前） |
| 行覆盖率门禁未纳入本 change | 覆盖率测量与门禁是独立工程化事项，不夹带进缺陷修复 PR。已入仓的测量：`backend/scripts/evidence/coverage-2026-10-16.md`（39 / 45 条 → **84%**，随 #74 合入）、`backend/scripts/evidence/coverage-2026-10-17.md`（93 条 → **85%**，随 #78 合入 `da2a366`）。#79 合入后基线已是 **100 passed / TOTAL 87%**（600 stmts / 80 miss，2026-10-21 在 main `e46624b` 实测），该数值**另出一份测量文件**，不改动上述两份历史证据；门禁入口仍在 PR #72 讨论 | backend 吕建江 | 复测文件随归档后的小 PR 入仓；看板「覆盖率测量 pytest-cov ≥60%」行 |
| 仓库其余「契约三 v1.4」引用**分两类**：① 历史记录（`docs/repo/catchup-ledger.md` L3 行、`docs/backend/README.md:31` 的 L3 行、`docs/design/diagrams.md:15` 的提示词原文）；② 现行口径引用（`docs/frontend/pages.md:88`、`docs/frontend/README.md:5`、`docs/common/test-plan.md:5`） | ① 记的是当时口径，不在缺陷修复 PR 里改写；② 归各自线（见 3.2，归档时复核仍在）。`docs/design/README.md` 复核已无 v1.4 残留。规格首段 `openspec/specs/query-api/spec.md:4` **已随本归档 PR 同步为 1.5** | 台账/历史行归 蒋励（统稿）；②类归 刘帅华 + 蒋励 | ①无计划（保持历史原样）；②随 3.2 |
| Issue #65 登记的失效 `docs/contracts/` 引用未在本 PR 收口 | 10-11 12:41 归属裁定：后端线只负责 `backend/README.md`（已在 2.2 完成）。归档时进度：现行规格的旧路径**已各自立 change**（后端线 `backend-spec-path-references` = PR #82 审阅中；模型线 `path-references-alignment` 已在 main），剩 `archive/` 12 份历史记录改不改仍待 PO 在 Issue #65 裁决 | 苏哲勋（#65 裁决）+ 吕建江 / 蒋励（按线执行） | 见 Issue #65；本 change 不阻塞 |

> 落地结论：代码与契约同改、同 PR 落地，区间语义自 1.5 起可判定；结束日丢数据与紧凑格式二义性在**单元层闭环**（6 条新增用例 + 45/45 无回归）、在**集成层已由真服务 11 条断言闭环**（含列表 / 趋势 / 周下钻 / 月桶四口径互相对账，`backend/scripts/evidence/integration-time-range-2026-10-16.md`）；只剩**三页面端到端 + 10/23 课上验收**两个明确下游，未执行的一律留在上表，不倒填。
> 归档记录（2026-10-21）：`openspec archive backend-time-range-semantics -y` 于本归档 PR 执行，delta 落 `openspec/specs/query-api/spec.md`（`~ 2 modified` + 4 条新增 Scenario），同 PR 手工同步首段版本号；归档时 `openspec validate --all --strict` 全绿（项数见本 PR 描述）。上表 §1–§4 的执行记录是**当时的运行事实**（被测提交 `b7ac417`、45 条基线、13 passed / 1 failed 的全量校验），按模板「不倒填」原样保留；只有 §5 缺口的**归属与现状**按 10-21 的 main 刷新（应审阅人在 #75 的非阻塞意见）。
