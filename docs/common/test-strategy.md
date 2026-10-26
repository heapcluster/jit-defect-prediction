# 测试策略与三层测试责任（2026-10-13 起执行）

> 起因：**2026-10-13 课堂反馈** —— ① 缺少测试，要参照**软件系统测试分析的标准做法**做开发过程中必要的测试；② **结项答辩占 50%，须能讲明白**；③ 每人写完代码给自己的程序写**单元测试**，合并后大版本写**集成测试**，最后交付做**验收测试**。
> 本文件是**策略与责任总纲**；单次变更的具体测试计划见 `openspec/changes/**/tasks.md` 的「测试与验证」板块；具体执行口径见 `docs/common/test-plan.md`。
> 关联：`docs/common/openspec-task-template.md`、`docs/common/test-report-sprint1.md`、`repo/defect-records.md`。

## 1. 分层模型（V 模型，课程「软件系统测试分析」标准做法）

```
需求规格（PRD / specs/*/spec.md）        ←── 验收测试（Acceptance）
概要设计（模块划分 / 接口契约 / 库表）    ←── 集成测试（Integration）
详细设计（函数 / 类 / 组件内部）          ←── 单元测试（Unit）
```

**左支是设计层次，右支是测试层次**：每一层设计对应一层测试，**测试不是写完代码才想的事，是设计的镜像**。

| 层 | 测试什么 | 谁写 | 什么时候 | 通过判据 |
|---|---|---|---|---|
| 单元测试 | 单个函数 / 类 / 纯口径函数的输入→输出 | **写该段代码的人**（谁动代码谁写） | **代码写完、提 PR 之前** | 新增/改动的函数有正向 + 异常/边界用例，全绿 |
| 集成测试 | 跨模块、跨线的契约：接口↔库表↔模型↔前端↔数据流 | 负责合入该大版本的一条线组织 | **大版本合并后**（PR 合入 main / Sprint 里程碑） | 契约级断言全绿，字段名/错误码/幂等/时序一致 |
| 验收测试 | 用户可见的完整流程，按 spec 的 Scenario 逐条走 | 全员 + 组长统稿 | **交付时**（Sprint 评审 / Final Release） | 每条 SHALL/MUST 有 Scenario 与证据 |
| 非功能验证 | 性能 / 安全 / 可靠 / 易用 | 触及该维度的一条线 | 与对应层级并行 | 有实测数字与证据文件，不写口号 |

## 2. 三条硬规则（可直接引用到答辩）

1. **谁写的代码谁写单测**。不写单测 = 代码没写完，PR 不得合入。
2. **勾了 `tasks.md` ≠ 功能合格**。必须有可复现命令与证据路径；「已实现」与「已验收」是两个状态，不得混用。
3. **每个 change 必须有「测试与验证」板块**（模板见 `docs/common/openspec-task-template.md`）。板块缺失 = 提案不完整，不得进入 apply。

## 3. 现状覆盖矩阵（2026-10-13 实测，数字可复现）

| 线 | 单元测试 | 集成测试 | 验收测试 | 非功能 | 状态 |
|---|---|---|---|---|---|
| 后端 `backend/` | **253 条**（`ingest` 随 2026-10-25 裁定移除后重测；`test_prs_api.py` 8 条为 PR 三端点新增） | `test_mirror.py` 8 + `test_model_registry.py` 5 = 13 条 | `docs/repo/demo-script-sprint1.md` API-01~04 | 性能 + 安全两阶段证据齐 | ✅ 最完整 |
| 前端 `frontend/` | **26 个 it**（7 个测试文件：`tests/api.spec.js` / `request.spec.js` / `RiskList.spec.js` / `CommitDetail.spec.js` / `models.spec.js` / `risk.spec.js` / `features.spec.js`） | **0**（未联调） | **0**（未跑演示） | 易用（三态）待联调 | 🟡 已写未跑 |
| 数据/模型 `data_model/` | **59 条**（`test_feature_contract.py` 8 + `test_szz_labeling.py` 34 + `test_split_dataset.py` 17） | 以九份统计报告代替，**无自动化** | `data_model/reports/` 九份 | 可靠（版本固定 + 可复现） | 🟡 单测已补，集成待建 |
| 工程化 `infra/` | **0**（CI 未落地） | —— | —— | —— | 🔴 缺口 |

**复现命令**（环境：conda `jit-defect`）：
```bash
cd backend    && python -m pytest -q     # 87 passed
cd data_model && python -m pytest -q     # 59 passed（2026-10-13 由 8 补到 59）
cd frontend   && npm ci && npm run test:unit   # 13 it（尚未执行，node_modules 未装）
```

## 3.1 数据线补齐记录（2026-10-13，蒋励）

课堂反馈后由**数据线负责人蒋励**按「谁写代码谁写单测」补齐，只覆盖纯函数、不依赖 git 与仓库数据：

| 文件 | 条数 | 覆盖 |
|---|---|---|
| `data_model/tests/test_feature_contract.py` | 8 | 特征契约（14 项列名与顺序） |
| `data_model/tests/test_szz_labeling.py` | 34 | 打标判据词首边界、diff 解析、区间合并、blame 缓存键 |
| `data_model/tests/test_split_dataset.py` | 17 | 切分下标、排序稳定性、守恒与时间序断言 |

**过程中测试抓到了自己的两个错误预期**（已修正，证明断言有效）：
① 把「`CAMEL-102 fix the message dispatch handling`」误列为应拒案例 —— 该消息 `fix` 在词首，本就应判为修复提交；
② `merge_ranges` 默认阈值预期算错 —— 合并条件是 `start - 上段止行 - 1 <= gap`，间隔 20 仍合并、21 才不合并。

## 4. 缺口清单与责任人（按优先级）

| # | 缺口 | 影响 | 归属 | 计划 |
|---|---|---|---|---|
| 1 | **数据线 01–05 无单元测试**（SZZ 判据、特征计算、切分边界全靠重跑全链路肉眼比对） | 改一处判据无法证明没改坏别的，答辩讲不清 | 蒋励 | Sprint 2 |
| 2 | **前端 13 条单测未执行**、未过 lint/build、未联调 | Sprint 1 验收直接卡住 | 刘帅华 | Sprint 1 收口前 |
| 3 | **无集成测试套件**（跨线契约只在各线单测里间接覆盖） | 「合并后大版本写集成测试」未落实 | 吕建江（后端线牵头） | Sprint 2 |
| 4 | **CI 未落地**（`.github/workflows` 为空），测试全靠手动 | 回归无门禁 | 苏哲勋 | Sprint 2 |
| 5 | **覆盖率未测量**（无 `pytest-cov` / vitest coverage 配置与阈值） | 无法量化「测了多少」 | 各线 | Sprint 2 |
| 6 | **组件层测试为零**（三态、错误码分发、字段映射无自动化） | 前端最易回归的部分没保护 | 刘帅华 | Sprint 2 |
| 7 | **G1-1~G1-4 无任何测试** | 附加功能未开始 | 蒋励 / 刘帅华 | Sprint 3 |

## 5. 测试配置基线（2026-10-13 补齐）

| 文件 | 作用 |
|---|---|
| `backend/pytest.ini` | pytest 测试路径、命名约定、报告输出 |
| `data_model/pytest.ini` | 同上（数据线） |
| `frontend/vite.config.js` | vitest 环境（jsdom）与 `frontend/tests/**` 匹配（`setupFiles: ./tests/setup.js`） |
| `frontend/package.json` `scripts` | `test:unit` / `test:coverage` 统一入口 |

> 命名约定：后端 `tests/test_<模块>.py`，用例 `test_<行为>_<期望结果>`；前端 `tests/<对象>.spec.js`。
> 每个用例必须能**独立复现**：不依赖执行顺序、不依赖上一次运行的残留数据。

## 6. 证据归档位置（一处集中，答辩直接取）

| 类型 | 位置 |
|---|---|
| 单测 / 集成测试结果 | 命令输出贴进 `docs/common/test-report-sprint1.md`（每 Sprint 一份） |
| 性能 / 安全证据 | `backend/scripts/evidence/*.md` |
| 数据 / 模型统计 | `data_model/reports/*.md` |
| 联调记录 | `docs/frontend/frontend-integration-log.md` |
| 演示脚本 | `docs/repo/demo-script-sprint1.md` |
| 缺陷记录 | `docs/repo/defect-records.md`（五项字段） |

## 7. 答辩口径（50 分，须讲明白的三件事）

1. **分层为什么这么分**：V 模型左支右支对应关系；为什么单测必须由写代码的人做（只有他知道异常路径在哪）。
2. **每层测到什么程度**：用 §3 的实数讲（87 / 15 / 13 / 8），并说明**哪些没测、为什么、什么时候补**（§4）—— 承认缺口比假装全覆盖更能得分。
3. **证据链**：spec 的 SHALL/MUST → change 的「测试与验证」板块 → 测试文件 → 证据 md → `defect-records.md`。**任何一条 SHALL 都能点回测试**，这是 Final Release 验收项。
