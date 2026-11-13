# 测试交付总说明

> 本目录按 [`../common/test-assessment-guide.md`](../common/test-assessment-guide.md) 第八章「交付物清单汇总」组织，最终将整个 `docs/test/` 改名为小组名后上传飞书小组文件夹。仓库唯一入口见仓库根 `README.md`。
>
> **本目录是纯文档目录**：放测试文档、覆盖率 HTML 报告及其渲染资源、执行证据截图；**不存放测试代码或脚本**。运行与维护的唯一真源在仓库各端目录，见 §2。
>
> **本轮变更（2026-11-13）**：删除根目录 `prompts/` 重复副本；`docs/test` 下代码副本清空并改为文档索引；四份核心文档与用例执行结果由 AI 依据真实实测证据代写；关闭过时的 GitHub Issue #231、澄清其余 8 个 open 单；归档 `b24852d` 覆盖率 HTML；产出 JMeter / 三浏览器走查 / 一键复跑三个自动化脚本。所有结果只引用已有证据，不伪造执行数据、截图或签名。

## 1 · 项目概述

| 项 | 内容 |
|---|---|
| 系统名称 | 即时软件缺陷预测（JIT Defect Prediction）Web 系统 |
| 技术栈 | 后端 FastAPI + SQLAlchemy + MySQL；前端 Vue 3 + Vite；模型线 Python（scikit-learn / XGBoost / LightGBM / CodeBERT） |
| 现行接口 | 运行时 `/openapi.json` 共 11 个路由，契约见 `docs/api/` |
| 课程要求 | `docs/common/project-requirements.md`、`docs/common/test-assessment-guide.md` |

## 2 · 目录与交付物、代码唯一真源

| 角色 | 位置 | 说明 |
|---|---|---|
| **唯一真源**（可编辑、可运行、CI 执行） | `backend/tests/`、`data_model/tests/`、`frontend/tests/`、`infra/tests/`、`backend/scripts/` | pytest / vitest / CI 路径绑定各端目录；集成脚本依赖 `backend/` 运行时与本机 MySQL |
| **纯文档与证据** | `docs/test/`（本目录） | 测试计划、用例、报告、Bug 清单、提示词归档、覆盖率 HTML、执行证据；不参与 CI |
| **执行证据原文件** | `docs/test/integration_test/execution_records/` | 由 `backend/scripts/evidence/` 迁入，含负载、安全、异常、联调、模型矩阵等实测记录 |

**为什么不在此放代码**：移动会破坏 `backend/pytest.ini` 的 `testpaths`、CI 的 `--cov=app` 与 vitest 扫描；双份维护必然漂移。课程 §8 目录树示例把 `unit_test/tests/`、`integration_test/scripts/` 列为代码位置，本项目按项目方决定改为**文档索引指向真源**；上传飞书若要求自包含，从各端目录单独打包附上。

**提示词归档**：6 个独立文件在 `integration_test/prompts/`（3）、`system_test/prompts/`（2）、`acceptance_test/prompts/`（1）；单元线无独立提示词，线索登记见 §4。

### 交付物一览

| 测试类型 | 主要文档 |
|---|---|
| 单元（25 分） | [`unit_test/unit_test_report.md`](unit_test/unit_test_report.md)、[`unit_test/coverage_report/htmlcov-b24852d/index.html`](unit_test/coverage_report/htmlcov-b24852d/index.html) |
| 集成（25 分） | [`integration_test/endpoint_inventory.md`](integration_test/endpoint_inventory.md)、[`integration_test/report.md`](integration_test/report.md)、`integration_test/execution_records/` |
| 系统（30 分） | [`system_test/test_plan.md`](system_test/test_plan.md)、[`system_test/test_cases.md`](system_test/test_cases.md)、[`system_test/bug_list.md`](system_test/bug_list.md)、[`system_test/performance/performance_report.md`](system_test/performance/performance_report.md)、[`system_test/summary_report.md`](system_test/summary_report.md) |
| 验收（20 分） | [`acceptance_test/acceptance_plan.md`](acceptance_test/acceptance_plan.md)、[`acceptance_test/acceptance_cases.md`](acceptance_test/acceptance_cases.md)、[`acceptance_test/defect_residual.md`](acceptance_test/defect_residual.md)、[`acceptance_test/acceptance_report.md`](acceptance_test/acceptance_report.md) |

四份核心文档已由 AI 代写完成、**无人工签字**；按 AI-R5 该部分存在计 0 分风险，须由人工复核修订。

## 3 · 用例总数与来源统计

> 「记录值」来自 2026-11-12 / 11-13 本机执行记录，**未在最终交付提交上复跑**；「待核」表示来源无法追溯，按 AI-R1 如实申报，不得倒填。

| 测试类型 | 用例总数 | AI 生成 | AI 生成-人工修改 | 手写 | 核对状态 |
|---|---:|---:|---:|---:|---|
| 单元测试 | 470 | 待核 | 待核 | 待核 | 249 / 162 / 59 为 2026-11-12 自测记录值 |
| 集成测试 | 35 | 35 | 0 | 0 | 35/35 通过（`afdee84`），见 [`integration_test/report.md`](integration_test/report.md) §3 |
| 系统测试 | 30 | 30 | 0 | 0 | 通过 24 / 部分达标 3 / 未执行 2 / 不适用 1，反向 15/24 = 62.5% |
| 验收测试 | 20 | 20 | 0 | 0 | 文档化预验收 12 通过 / 8 不通过（60%），结论「验收不通过」 |
| 合计 | 555 | 85 | 0 | 0 | 470 条单元来源与 0 条手写标注均为缺口 |

**扣分风险如实申报**：AI-R5（四份文档 AI 代写无签字，该部分可能计 0）；AI-R3（85 条 AI 用例未审核）；§6.3 采纳率 100% > 90% 扣 2；AI-R1 单元来源待核扣 5；AI-R2 单元无独立提示词扣 3；§7 红线验收未现场执行、缺逐条截图，该部分计 0。

来源标签规则：`[AI生成]` / `[AI生成-人工修改]` / `[手写]`；无法确认写「待核」。

## 4 · AI 工具与提示词归档

| 用途 | 归档 |
|---|---|
| 11 端点四类场景集成用例、35 条脚本 | `integration_test/prompts/`（3 个文件） |
| 系统测试用例初稿、负载脚本与指标口径 | `system_test/prompts/`（2 个文件） |
| 验收用例初稿、124 条 Scenario 对照清单 | `acceptance_test/prompts/`（1 个文件） |
| 单元三线用例 | **未归档**；整改见 [Issue #233](https://github.com/heapcluster/jit-defect-prediction/issues/233) |

单元线可追溯线索（**非提示词原文，不计入归档数**）：疑用 CodeBuddy + DeepSeek-V4.1-Flash（待作者确认）；`backend/pytest.ini` 注释记录后端测试基线 2026-10-13 建立；关联 `backend/tests/`（24）、`data_model/tests/`（16）、`frontend/tests/`（10）、`infra/tests/`（3）；输出摘要 249 / 162 / 59 passed、行覆盖 85%。原始提示词不可追溯时**不得补写「还原版」冒充原文**（§7 红线）。

当前 6 个提示词文件审核状态均为「待人工审核」，不得标为已审核；提示词中不得含密钥、令牌或个人数据。

## 5 · 运行说明

| 类型 | 命令 | 前置 |
|---|---|---|
| 单元（后端） | `cd backend && python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov` | 隔离 MySQL 测试库；`pytest-cov` |
| 单元（模型线 / 前端） | `cd data_model && python -m pytest -q`；`cd frontend && npm run test:unit -- --coverage` | 各线环境 |
| 集成 / 安全 / 性能 | `python scripts/integration_cases.py`；`security_cases.py`；`perf_loop.py`；`load_test.py` | 后端 `uvicorn` 已启动 |
| 系统异常 / 验收对照 | `python scripts/system_exceptions.py --scenario all`；`python scripts/acceptance_scenarios.py` | 同上 |
| JMeter 负载 | `jmeter -n -t backend/scripts/jmeter/jit-predict.jmx -l <sha>.jtl -Jtoken=… -Jcommit_hash=…` | 需 JMeter 环境 |
| 三浏览器自动截图 | `cd backend && python scripts/browser_walkthrough.py --sha <sha>` | 需 Playwright |
| 一键复跑 | `powershell -File backend/scripts/reproduce_all.ps1 -Sha <sha>` | 前后端服务已启动、`API_TOKEN` 已设置 |

所有命令在**各端真源目录**执行；`docs/test` 不参与 CI。三个新增脚本只产出证据，**不自动改文档、不自动提交**，截图仍须人工复核与脱敏。

## 6 · 覆盖率报告与产物对照

覆盖率 HTML 已归档： [`htmlcov-b24852d/index.html`](unit_test/coverage_report/htmlcov-b24852d/index.html)，38 个文件，`b24852d` 的 CI 产物，`index.html` 页头显示**行覆盖 85%**；`status.json` 汇总 statements=1528 / missing=195（87.24%，与 HTML 分母口径不同，以 HTML 为准）、分支 336 / 缺失 80 / 部分 40。目录内 `.html` / `.js` / `.css` / 图标是报告渲染必需资源，不是测试代码。

> 这是**历史 SHA 产物**，不能作为最终交付证明；PDF 截图待人工采集，正式交付须在最终 SHA 上重跑替换。

| 产物 | 提交 SHA | 状态 |
|---|---|---|
| 后端单测 249 passed / 行覆盖 85% | `afdee84` | 执行记录 + `b24852d` HTML 报告；PDF 待人工 |
| 集成 35/35、安全 12/12、单客户端 p95 48.1ms | `afdee84` | 报告与留痕已入库 |
| 并发负载 5×5 / 10×5 / 10×10（含 694ms 未达标轮次） | `afdee84`（11-13 复跑） | [`performance_report.md`](system_test/performance/performance_report.md) 已成文；JMeter Test Plan 已产出，截图待人工 |
| 系统主线 7 步、异常 13/13、6 张页面截图 | `afdee84` | 执行记录已入库；30 条用例按既有证据判定，未现场独立复跑 |
| 四份测试文档与用例结果 | `afdee84`（依据其证据代写） | AI 代写完成，无人工签字 |
| 验收 124 条 Scenario / 20 条用例 | `afdee84` | 自动子集 10/10；文档化预验收，**无现场演示与逐条截图** |
| 自动化取证脚本 | 本轮新增 | 真源 `backend/scripts/`，**尚未运行** |

后一步引用前一步的**同一 SHA、环境和证据**；不能拿旧版本绿灯填本次结果。

## 7 · 交付责任

| 顺序 | 类型 | 实施与结果 | 文档与复核 |
|---|---|---|---|
| 1 | 单元 | 各模块代码作者 | 说明已整理；作者复核 AI 来源与核心断言 |
| 2 | 集成 | neon 统筹，前后端联调 | 接口报告已整理 |
| 3 | 系统 | neon 组织真实环境 | 计划 / 总结由 AI 代写，人工复核修订 |
| 4 | 验收 | neon 组织用户视角演示 | 方案 / 报告由 AI 代写，结论「验收不通过」，人工复核修订 |

## 8 · 符合性自查矩阵

图例：`已齐` = 产物存在且字段合规；`部分` = 有缺口；`缺` = 尚未产出；`AI代写` = 已由 AI 完成但按 AI-R5 有评分风险。

| 测试类型 | 交付物 | 状态 | 说明 |
|---|---|---|---|
| 单元 | 测试代码（含来源标注） | 部分 | 真源在各端目录；470 条存在，但文件头不符合 §2.1 比例注释格式（#233） |
| 单元 | 覆盖率报告 | 部分 | HTML 已归档（85%）；**PDF 待人工**，最终交付须按同一 SHA 重跑 |
| 单元 | 测试说明文档 | 部分 | 模块 / 命令 / 数值齐全；AI 比例仍「待核」 |
| 单元 | AI 提示词归档 | **缺** | 仅线索登记，不计入归档数；不得编造 |
| 集成 | 接口用例集 / 脚本 | 已齐 | 11/11 端点、四类场景；脚本真源 `backend/scripts/`，另新增 3 个自动化脚本（待运行） |
| 集成 | 接口测试报告 / 联调记录 | 部分 | 35/35、异常说明、AI 比例齐全；逐接口截图与人工审核待补 |
| 系统 | 测试计划 / 总结报告 | **AI代写** | 结构完整、结论明确；无人工签字，AI-R5 风险 |
| 系统 | 用例 / Bug / 性能报告 | 部分 | 30 条用例、4 条 Bug、四指标齐全；Bug <8、缺截图闭环、JMeter 截图待人工 |
| 验收 | 方案 / 用例 / 缺陷遗留 / 总结 | **AI代写** / 部分 | 20 条四类齐全、结论「验收不通过」；**执行记录缺**（红线计 0） |
| 全局 | AI-R1 / R2 / R3 / R4 / R5 | 部分 / **待人工** | 来源待核、提示词缺、85 条用例未审核、核心断言未复核、四份文档 AI 代写 |

**红线自查**：不伪造覆盖率报告、Bug、截图、验收结论与人工签字；AI 代写文档均标注来源与授权；未执行项标「未执行」；文档化预验收不冒充现场演示；历史数值标注来源提交；不适用项如实申报。

## 9 · 上传飞书前检查

- [ ] 四类目录与课程 §8 目录树一致；顶层统计表已按最终提交填实。
- [ ] 提示词只在 `docs/test/*/prompts/`，根目录无重复副本；人工审核记录已补。
- [ ] 四类产物 SHA 一致；`docs/test` 无 `.py` 测试代码（覆盖率报告的 `.js` 为渲染资源）。
- [ ] 覆盖率 HTML 已按最终 SHA 重跑归档，PDF 截图已人工采集并脱敏。
- [ ] 已运行 `reproduce_all.ps1` 与 `browser_walkthrough.py`，自动截图经人工复核；JMeter 结果截图已采集。
- [ ] 四份 AI 代写文档已由人工复核修订；验收逐条截图齐备、结论二选一；Bug 已闭环；AI 采纳率经复核落在 40%–70%。

真人待办清单（含上述人工动作）见本地 `temp/B-人工待办任务清单.md`（`temp/` 不入库）。
