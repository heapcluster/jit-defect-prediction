# 测试交付总说明

> 本目录按 [`../common/test-assessment-guide.md`](../common/test-assessment-guide.md) 第八章「交付物清单汇总」组织，最终把整个 `docs/test/` 改名为小组名后上传飞书。仓库唯一入口见根 `README.md`。
>
> **本目录是纯文档目录**：只放测试文档、覆盖率 HTML 报告及其渲染资源、执行证据截图；**不存放测试代码或脚本**，运行与维护的唯一真源在仓库各端目录，见 §2。
>
> **本轮（2026-11-15，`2734c1b`）已把所有可自动化的测试重新跑过一遍**，各文档里的数字都是这轮实测的；不能自动化的项（跨浏览器、JMeter 截图、人工签字、现场演示）在每篇文档的「未闭合项」里逐条列明，汇总见 [`human-todo.md`](human-todo.md)。

## 1 · 项目概述

| 项 | 内容 |
|---|---|
| 系统名称 | 即时软件缺陷预测（JIT Defect Prediction）Web 系统 |
| 技术栈 | 后端 FastAPI + SQLAlchemy + MySQL 8；前端 Vue 3 + Vite；模型线 Python（scikit-learn / XGBoost / LightGBM / CodeBERT） |
| 现行接口 | 运行时 `/openapi.json` 共 11 个路由，契约见 `docs/api/` |
| 模型规模 | 四条线共 25 个模型（expert 8 / semantic 8 / fused 8 / e2e 1） |
| 课程要求 | `docs/common/project-requirements.md`、`docs/common/test-assessment-guide.md` |

## 2 · 目录与代码唯一真源

| 角色 | 位置 | 说明 |
|---|---|---|
| **唯一真源**（可编辑、可运行、CI 执行） | `backend/tests/`、`data_model/tests/`、`frontend/tests/`、`infra/tests/`、`backend/scripts/` | pytest / vitest / CI 路径绑定各端目录；接口脚本依赖 `backend/` 运行时与本机 MySQL |
| **纯文档与证据** | `docs/test/`（本目录） | 测试计划、用例、报告、Bug 清单、提示词归档、覆盖率 HTML、执行证据；不参与 CI |
| **执行证据原文件** | `*_test/execution_records/` | 各轮脚本输出与截图，按日期命名，历史记录不覆盖 |

**为什么不在此放代码**：移动会破坏 `backend/pytest.ini` 的 `testpaths`、CI 的 `--cov=app` 与 vitest 扫描；两份必然漂移。课程 §8 目录树把 `unit_test/tests/`、`integration_test/scripts/` 列为代码位置，本项目改为**文档索引指向真源**；若飞书要求自包含，从各端目录单独打包附上。

### 交付物一览

| 测试类型 | 主要文档 |
|---|---|
| 单元（25 分） | [`unit_test/unit_test_report.md`](unit_test/unit_test_report.md)｜覆盖率 [`unit_test/coverage_report/htmlcov-2734c1b/index.html`](unit_test/coverage_report/htmlcov-2734c1b/index.html) |
| 集成（25 分） | [`integration_test/endpoint_inventory.md`](integration_test/endpoint_inventory.md)、[`integration_test/report.md`](integration_test/report.md)、[`integration_test/execution_records/`](integration_test/execution_records/) |
| 系统（30 分） | [`system_test/test_plan.md`](system_test/test_plan.md)、[`test_cases.md`](system_test/test_cases.md)、[`bug_list.md`](system_test/bug_list.md)、[`performance/performance_report.md`](system_test/performance/performance_report.md)、[`summary_report.md`](system_test/summary_report.md) |
| 验收（20 分） | [`acceptance_test/acceptance_plan.md`](acceptance_test/acceptance_plan.md)、[`acceptance_cases.md`](acceptance_test/acceptance_cases.md)、[`model-accuracy-evidence.md`](acceptance_test/model-accuracy-evidence.md)、[`defect_residual.md`](acceptance_test/defect_residual.md)、[`acceptance_report.md`](acceptance_test/acceptance_report.md) |
| 缺陷处理（贯穿四类） | [`defect-handling.md`](defect-handling.md)（边界与职责）、[`issues/`](issues/)（新单草稿 + 历史单更新/合并草稿） |

四份「人工撰写」文档（系统测试计划 / 总结、验收方案 / 总结）由 AI 起草、**无人工签字**；按 AI-R5 该部分存在计 0 分风险，须由人工复核修订。

## 3 · 用例总数与来源统计

| 测试类型 | 用例总数 | AI 生成 | AI 生成-人工修改 | 手写 | 核对状态 |
|---|---:|---:|---:|---:|---|
| 单元测试 | 494 | 待核 | 待核 | 待核 | 后端 254 / 模型线 162 / 前端 59 / 基础设施 8 / CI 契约 11，全部本轮通过 |
| 集成测试 | 35 | 35 | 0 | 0 | 34 通过 / 1 失败（T-IN-29） |
| 系统测试 | 30 | 30 | 0 | 0 | 25 通过 / 1 失败 / 3 部分达标 / 1 不适用 |
| 验收测试 | 20 | 20 | 0 | 0 | 11 通过 / 9 不通过（55%） |
| 合计 | 579 | 85 | 0 | 0 | 单元线来源比例仍不可追溯 |

来源标签只有三种：`[AI生成]` / `[AI生成-人工修改]` / `[手写]`；确认不了就写「待核」，不倒填。

单元线为什么还是「待核」：测试文件里只有 20 处文件级标签（后端 12 个文件、模型线 1 个、前端 7 个），没有逐条记录，也没有可回溯的原始提示词。硬填一个比例就是数据造假，所以按 AI-R1 / R2 如实申报扣分风险。

## 4 · 本轮实测结果速览

| 项 | 命令 | 结果 |
|---|---|---|
| 后端单测 | `cd backend && python -m pytest -q` | **254 passed**，行覆盖 87.2%、分支 76.2% |
| 模型线单测 | `cd data_model && python -m pytest -q` | **162 passed** |
| 前端单测 | `cd frontend && npm run test:unit` | **59 passed / 9 文件** |
| 基础设施 + CI 契约 | `python -m pytest -q infra/tests` 等 | **8 + 11 passed**，OpenSpec 结构 0 error |
| 前端构建 | `npm run build` | 成功，17.55s（单 chunk 2,217 kB，见 C-06） |
| 接口集成 | `python scripts/integration_cases.py` | **34 / 35**，11/11 端点覆盖 |
| 安全 | `python scripts/security_cases.py` | **18 / 18** |
| 系统异常 | `python scripts/system_exceptions.py --scenario all` | **13 / 13**（修脚本前置后） |
| 25 模型矩阵 | `python scripts/online_models_matrix.py` | **23 / 25**（两个 tabnet 受 #222 限制） |
| 性能 | `perf_loop.py` / `load_test.py` | 单客户端 p95 **68.1ms**（同日两次 53.3 / 68.1）；20 并发 p95 **688.9ms** 未达标 |
| 联调留痕 | `python scripts/linkage_capture.py` | 13 条真实请求/响应包络 |
| 验收自动子集 | `python scripts/acceptance_scenarios.py` | 137 个 Scenario 中自动可判定 **10 / 10** |
| 浏览器走查 | Playwright（Chromium 151） | 7 张：5 个页面 + 抽屉首测 / 复验 + 「提交不存在」态 |

所有产物同一提交、同一环境、同一天；按日期命名，未覆盖历史记录。

> 跑之前补建了 `backend/static/figures/` 并从 `data_model/pipelines/*/reports/figs_by_model/` 拷了 133 张 PNG 过去（该目录被 `.gitignore` 忽略，不进版本控制）。这两步是 BUG-01 / BUG-02 的临时绕过，长期要靠修代码与固化部署流程解决。

## 5 · 覆盖率报告

| 项 | 值 |
|---|---|
| 报告位置 | [`unit_test/coverage_report/htmlcov-2734c1b/index.html`](unit_test/coverage_report/htmlcov-2734c1b/index.html)（37 个文件，本 SHA 唯一产物） |
| 行覆盖 | 1333 / 1528 = **87.2%** |
| 分支覆盖 | 256 / 336 = **76.2%**（40 个分支只走一半） |
| HTML 首页显示 | **85%**（line+branch 合并口径，别看错） |
| PDF 截图 | 待人工采集 |

目录里的 `.js` / `.css` / 图标是报告渲染资源，不是代码副本。

> 一个容易踩的坑：coverage 生成的报告目录里自带一个内容为 `*` 的 `.gitignore`，会让整份报告被 git 忽略、提交时"凭空消失"。本轮已把它删掉。下次重新生成报告后记得检查 `git status` 里能不能看到这 37 个文件。

## 6 · AI 工具与提示词归档

| 用途 | 归档 |
|---|---|
| 11 端点四类场景集成用例、35 条脚本与复跑 | [`integration_test/prompts/`](integration_test/prompts/)（4 个文件） |
| 系统测试用例初稿、负载脚本、缺陷登记 | [`system_test/prompts/`](system_test/prompts/)（3 个文件） |
| 验收用例初稿、Scenario 对照、实测取证 | [`acceptance_test/prompts/`](acceptance_test/prompts/)（2 个文件） |
| 本轮复跑 / 缺陷登记 / 验收取证所用的提示词 | 本轮新增 4 个文件：`integration_test/prompts/integration_rerun_02.md`、`system_test/prompts/system_buglist_02.md`、`acceptance_test/prompts/acceptance_evidence_02.md`、`unit_test/prompts/unit_rerun_01.md` |
| 单元三线原始用例生成提示词 | **仍缺**，只有线索登记，不得补「还原版」 |

本轮使用的工具：CodeBuddy（DeepSeek-V4.1-Flash）驱动 pytest / vitest / httpx 脚本 / Playwright MCP。归档文件里写了工具、日期、关联文件、提示词原文、输出摘要与人工审核状态（当前均为「待人工审核」）。提示词中不含密钥、令牌或个人数据。

## 7 · 运行说明

| 类型 | 命令 | 前置 |
|---|---|---|
| 单元（后端） | `cd backend && python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov` | MySQL `jit_test`；**先 `mkdir backend/static/figures`（BUG-01）** |
| 单元（模型线 / 前端） | `cd data_model && python -m pytest -q`；`cd frontend && npm ci && npm run test:unit -- --coverage` | 各自环境；前端覆盖率需 `npm ci` 补 `@vitest/coverage-v8` |
| 集成 / 安全 / 性能 | `python scripts/integration_cases.py`；`security_cases.py`；`perf_loop.py`；`load_test.py` | 后端 `uvicorn` 已启动 |
| 系统异常 / 25 模型 / 联调 | `python scripts/system_exceptions.py --scenario all`；`online_models_matrix.py`；`linkage_capture.py` | 同上（异常场景自起子进程） |
| 验收自动子集 | `python scripts/acceptance_scenarios.py` | 同上 |
| JMeter 负载 | `jmeter -n -t backend/scripts/jmeter/jit-predict.jmx -l <sha>.jtl -Jtoken=… -Jcommit_hash=…` | 需 JMeter（本机未装） |
| 一键复跑 | `powershell -File backend/scripts/reproduce_all.ps1 -Sha <sha>` | 前后端服务已启动、`API_TOKEN` 已设置 |

所有命令在**各端真源目录**执行；`docs/test` 不参与 CI。脚本只产出证据，不自动改文档、不自动提交，截图仍须人工复核与脱敏。

## 8 · 符合性自查矩阵

图例：`已齐` = 产物存在且字段合规；`部分` = 有缺口；`缺` = 尚未产出；`AI代写` = 已由 AI 完成但按 AI-R5 有评分风险。

| 测试类型 | 交付物 | 状态 | 说明 |
|---|---|---|---|
| 单元 | 测试代码（含来源标注） | 部分 | 494 条存在且全绿；文件头比例注释仍不合 §2.1（#233） |
| 单元 | 覆盖率报告 | 部分 | 本 SHA HTML 已归档（行 87.2% / 分支 76.2%）；**PDF 待人工** |
| 单元 | 测试说明文档 | 部分 | 模块、命令、数值齐全；AI 比例仍「待核」 |
| 单元 | AI 提示词归档 | **缺** | 仅线索登记 |
| 集成 | 接口用例集 / 脚本 | 已齐 | 11/11 端点、四类场景 |
| 集成 | 接口报告 / 联调记录 | 已齐 | 34/35 + 失败项根因 + 13 条包络留痕；逐条人工复核待补 |
| 系统 | 测试计划 / 总结 | **AI代写** | 结构与结论明确；无人工签字，AI-R5 风险 |
| 系统 | 用例 / Bug / 性能 | 部分 | 30 条、11 条产品缺陷（1 闭环）、四指标齐全；JMeter 截图与逐条截图待人工 |
| 验收 | 方案 / 用例 / 缺陷遗留 / 总结 | **AI代写** / 部分 | 20 条四类齐全；A-01~A-20 逐条编号取证仍缺（红线风险） |
| 缺陷处理 | 职责边界 + issue 台账 | 已齐 | 边界与五要素规范成文；4 条新单已提交（#239~#242），12 条历史单已更新，3 组重复已合并说明 |
| 全局 | AI-R1 / R2 / R3 / R4 / R5 | 部分 / **待人工** | 来源待核、单元提示词缺、85 条用例未审核、核心断言未复核、四份文档 AI 生成 |

**红线自查**：不伪造覆盖率、Bug、截图、验收结论与签字；AI 生成文档均标注来源；未执行项标「未执行」；自动化预验收不冒充现场演示；数值均标注提交与环境；不适用项（越权、上传）如实申报而非写成通过；已关闭但未修的 issue 如实标注，不写成已解决。

## 9 · 上传飞书前检查

- [ ] 四类目录与课程 §8 目录树一致；本文件 §3 统计表按最终提交填实。
- [ ] 提示词只在 `docs/test/*/prompts/`，人工审核记录已补。
- [ ] 四类产物 SHA 一致（当前均为 `2734c1b`）。
- [ ] 覆盖率 HTML 已按最终 SHA 重跑归档，PDF 截图已人工采集并脱敏。
- [ ] JMeter / Locust 结果截图已采集；浏览器补齐 Edge / Firefox。
- [ ] 11 条产品缺陷逐条补截图与复现签字，闭环记录已更新。
- [x] 4 条新缺陷已建成 issue（#239~#242）并回填编号；12 条历史单的更新/合并评论已发出（记录见 [`issues/`](issues/)）。
- [ ] 四份 AI 生成文档已人工复核修订；验收逐条截图齐备、结论二选一。

测试侧需要人工协助的环节（含分工边界）见 [`human-todo.md`](human-todo.md)；缺陷提单与修复的职责划分见 [`defect-handling.md`](defect-handling.md)。
