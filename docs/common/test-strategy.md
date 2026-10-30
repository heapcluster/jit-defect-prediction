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

## 3. 现状覆盖矩阵（2026-10-27 快照）

以下状态以 `main@3379d4c` 的 [CI 运行 #245](https://github.com/heapcluster/jit-defect-prediction/actions/runs/40495635657) 为自动化证据。该次运行的 lint、活规格校验、链接与 delta 检查、工程化/后端/前端/模型测试及构建步骤均成功。CI 成功只证明这些自动化步骤通过；浏览器现场走查、真实权重交付和完整业务验收仍须分别取证。

| 线 | 自动化测试（CI） | 跨模块集成 | 验收测试 | 非功能 | 状态 |
|---|---|---|---|---|---|
| 后端 `backend/` | `backend/tests/test_*.py` 在 CI 的 `Test backend` 步骤通过 | 套件已含接口、数据库、同步、模型注册等跨模块用例；CI 使用一次性 MySQL 测试库 | 以 `docs/backend/acceptance.md` 的场景与证据逐项确认，不能由单测绿灯代替 | 性能、安全结果分别看 `backend/scripts/evidence/` 的对应实测记录 | 🟡 自动化通过；现场验收另核 |
| 前端 `frontend/` | `frontend/tests/*.spec.js` 共 8 个文件；CI 的 `Test frontend` 为 **31 passed** | `docs/frontend/integration-log.md` 记录联调；浏览器场景已有部分截图 | `docs/frontend/evidence/tf-fe-01-screenshots.md` 明列未取证的加载、空态和契约错误码场景 | 三态与错误分发需按上述未取证项补浏览器证据 | 🟡 单测通过；场景取证未齐 |
| 数据/模型 `data_model/` | `data_model/tests/test_*.py` 在 CI 的 `Test data model` 步骤通过，**1 条因干净检出无 `.pkl` 而跳过** | 已有特征、交付清单、模型注册等契约测试；跨线完整链路需结合后端验收 | 模型指标见 `data_model/reports/`；实际权重包须另跑 `python -m pipelines.verify_all_weights --check` | CI 的跳过项不证明 8 个权重可加载，交付包要独立核验 | 🟡 自动化通过；权重交付另核 |
| 工程化 `infra/` | `infra/tests/test_*.py` 可按需单独运行；本次精简后不在自动门禁中 | `.github/workflows/ci.yml` 顺序执行三线测试与构建 | 历史 `main` CI #245 全绿只对应旧配置；新工作流待首次运行取证 | 必需检查 `CI` 保持不变；运行边界见 `infra/ci.md` | 🟡 配置已精简，运行证据待补 |

**复现命令**（每行独立从仓库根目录运行；依赖统一由 `data_model/environment.yml` 安装，后端测试需要可用的 MySQL 测试库）：
```bash
(cd backend && python -m pytest -q)
(cd data_model && python -m pytest -q)
(cd frontend && npm ci && npm run test:unit)
```

仓库精简后的 CI 只运行三线测试与构建；Ruff、OpenSpec 和链接检查改为按需人工执行，具体见 `infra/ci.md`。以上测试数量仅对应所引的 `main@3379d4c` 旧运行；后续变更需重新取证，不沿用本快照。

## 3.1 数据线补齐记录（2026-10-13 历史快照，蒋励）

课堂反馈后由**数据线负责人蒋励**按「谁写代码谁写单测」补齐，只覆盖纯函数、不依赖 git 与仓库数据：

| 文件 | 条数 | 覆盖 |
|---|---|---|
| `data_model/tests/test_feature_contract.py` | 8 | 特征契约（14 项列名与顺序） |
| `data_model/tests/test_szz_labeling.py` | 34 | 打标判据词首边界、diff 解析、区间合并、blame 缓存键 |
| `data_model/tests/test_split_dataset.py` | 17 | 切分下标、排序稳定性、守恒与时间序断言 |

**过程中测试抓到了自己的两个错误预期**（已修正，证明断言有效）：
① 把「`CAMEL-102 fix the message dispatch handling`」误列为应拒案例 —— 该消息 `fix` 在词首，本就应判为修复提交；
② `merge_ranges` 默认阈值预期算错 —— 合并条件是 `start - 上段止行 - 1 <= gap`，间隔 20 仍合并、21 才不合并。

## 4. 当前验证缺口与责任线

| # | 尚缺的证据 | 下一步 | 责任线 |
|---|---|---|---|
| 1 | 前端截图只覆盖部分浏览器状态；详情加载、趋势加载/空态及契约错误码分发尚未取证 | 按 `docs/frontend/evidence/tf-fe-01-screenshots.md` 的「未取证项」补真实场景与截图 | 前端刘帅华，后端配合 |
| 2 | CI 干净检出不带模型 `.pkl`，1 条磁盘清单测试按设计跳过 | 对实际交付包独立运行权重核验并保存结果，不能把 CI 通过写成 8/8 权重验收 | 数据/模型蒋励 |
| 3 | 单线及后端跨模块自动化已通过，但从 Camel 提交同步到前端显示的完整现场流程仍需按验收场景留证 | 在真实联调环境依次记录同步、预测、列表/详情/趋势的结果与环境边界 | 后端吕建江牵头，前端/模型配合 |
| 4 | 本次 CI 运行未输出各线最新覆盖率；既有覆盖率报告属于其记录时的代码版本 | 需要覆盖率结论时按当前提交重新运行并附输出，不沿用旧百分比 | 各代码线作者 |
| 5 | CI 运行成功与「合并必需检查」是两项不同证据 | 回读仓库规则中 `CI` 的必需检查配置并留链接/截图 | 工程化苏哲勋 |

具体负责人、截止与进度以飞书《工作周报》为准；本表只登记仓库内可核验的验证缺口。

## 5. 测试配置与 CI 入口（现行）

| 文件 | 作用 |
|---|---|
| `backend/pytest.ini` | pytest 测试路径、命名约定、报告输出 |
| `data_model/pytest.ini` | 同上（数据线） |
| `frontend/vite.config.js` | vitest 环境（jsdom）与 `frontend/tests/**` 匹配（`setupFiles: ./tests/setup.js`） |
| `frontend/package.json` `scripts` | `test:unit` 为当前单测入口；目前没有 `test:coverage` 脚本 |
| `.github/workflows/ci.yml` | 在 PR、`main` 推送和 merge queue 上顺序执行三线测试与构建 |

> 命名约定：后端 `tests/test_<模块>.py`，用例 `test_<行为>_<期望结果>`；前端 `tests/<对象>.spec.js`。
> 每个用例必须能**独立复现**：不依赖执行顺序、不依赖上一次运行的残留数据。

## 6. 证据归档位置（一处集中，答辩直接取）

| 类型 | 位置 |
|---|---|
| 单测 / 集成测试结果 | 对应 PR 的验证记录与 GitHub Actions 运行链接；`docs/common/test-report-sprint1.md` 保留 Sprint 1 历史结果 |
| 性能 / 安全证据 | `backend/scripts/evidence/*.md` |
| 数据 / 模型统计 | `data_model/reports/*.md` |
| 联调记录 | `docs/frontend/integration-log.md`；截图范围与缺口见 `docs/frontend/evidence/tf-fe-01-screenshots.md` |
| 演示脚本 | `docs/repo/demo-script-sprint1.md` |
| 缺陷记录 | `docs/repo/defect-records.md`（五项字段） |

## 7. 答辩口径（50 分，须讲明白的三件事）

1. **分层为什么这么分**：V 模型左支右支对应关系；为什么单测必须由写代码的人做（只有他知道异常路径在哪）。
2. **每层测到什么程度**：引用 §3 指向的具体 CI 运行与场景证据，说明哪些已自动化、哪些仍需现场验收，以及 §4 的缺口；历史用例数不能冒充当前结果。
3. **证据链**：spec 的 SHALL/MUST → change 的「测试与验证」板块 → 测试文件 → 证据 md → `defect-records.md`。**任何一条 SHALL 都能点回测试**，这是 Final Release 验收项。
