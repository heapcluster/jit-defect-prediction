# 课程要求与本项目映射

> 来源：课程《项目要求及日程安排》《项目要求》原文 ｜ 维护：蒋励
> 本文把课程硬要求逐条抄录，并指到本项目落地的包/文件，避免「要求飘在天上」。

## 0. 项目任务描述（原文摘录）

即时软件缺陷预测（JIT）：在**每次代码提交粒度**预测该提交是否引入缺陷，在缺陷进入主干前预警，指导评审员优先审高风险提交。开发完整可用 JIT 缺陷预测系统：从真实开源仓库（ActiveMQ/Lucene/Hadoop 等）挖历史数据、训机器学习模型、对外提供在线预测服务与可视化前端。

**主要功能模块**（课程列）：数据采集与仓库解析 / 特征工程与样本构建（Kamei 14 维 + 语义特征可选）/ 模型训练与评估（≥2 类不少于 8 种、两类指标、训练测试划分）/ 预测与解释（概率 + 归因）/ 可视化前端（风险列表、趋势看板）/ 工程化（分支规范+PR、CI/CD、插件化可选）。

> **在线 / 离线双层（先读，避免误判「项目太简单」）**：课程的 6 大模块里，**A 数据采集 / B 特征工程 / C 模型训练评估** 是离线管线，工作量占系统约 90%，落在 `model/` + `data_model/`，产出的「模型文件 + `prediction_result.csv`」按方案 A+C 交给后端；**D 预测接口 / E 查询接口 / F 前端** 是在线服务层，落在 `backend/` + `frontend/`，只需「加载 + 展示」。所以在线库的 **4 张表 / 4 个接口 / 3 个页面** 是跨线交付的必然结果，不是范围缩水。工程化（分支/评审/CI-CD/插件化）设计见 `design/engineering.md`。

## 1. 基本要求（原文 → 本项目落地）

| 课程基本要求 | 本项目落地 |
|---|---|
| 自由组队 3~4 人，全员共担质量，保留可核验个人贡献 | 4 人一人一线；Git/看板/OpenSpec/PR/周报为证据（`team-charter.md` §1.4） |
| 面向明确用户与真实场景，不简单复刻/CRUD | 用户=代码评审员；场景=提交粒度风险排序（`design/sprint0-scope.md`） |
| 含可用界面/交互入口 + 可维护业务/数据层 | 三页面 + 后端 + 数据线（`frontend/` `backend/` `model/`） |
| Scrum，每 Sprint 可演示可运行增量 | `repo/sprints.md` |
| MVP + ≥20 关联核心用户故事形成闭环 | PRD 31 条故事（核心 27 + 可选附加 Epic G 4；`repo/user-story-traceability.md`） |
| 功能+非功能需求（非功能≥2 项） | `design/non-functional.md`（安全/性能/可靠/易用） |

## 2. 项目协作规则（原文 → 本项目落地）

| 课程协作规则 | 本项目落地 |
|---|---|
| GitHub/Gitee 协作，提交历史/分支/Issue/看板/OpenSpec 为过程证据 | `repo/collaboration.md` `repo/kanban.md` |
| OpenSpec SDD：初始化并提交流程文件 | `repo/openspec-workflow.md` `common/openspec-rules.md` |
| 飞书多维表格/CodeArts/禅道管理，看板对应 Sprint 与 change | `repo/kanban.md` |
| 缺陷管理工具，记录现象/复现/优先级/状态/关联 | `repo/defect-management.md` |
| PR 合并前至少 1 位非作者审阅，意见留 Git | `repo/collaboration.md` §3 |
| 每周五课上汇报 + 工作周报 | `repo/weekly-reports.md` `repo/sprints.md` |
| 工程化（分支规范 + PR、CI/CD 流水线、插件化） | `design/engineering.md`（CI-CD/插件化设计）+ `repo/collaboration.md` `repo/git-pr.md`（分支/评审细则） |

## 3. Sprint 计划（原文 → 本项目落地）

| Sprint | 课程目标 | 本项目落地重点 |
|---|---|---|
| 0（1–3 周） | 需求/设计/看板/OpenSpec 初始化 | 29 任务闭环；9 能力规格；模型包 r2（`repo/sprints.md`） |
| 1（4–6 周） | 首 MVP，≥1 条界面→数据层完整流程 | #33/#52 合→三页面→联调→端到端（`frontend/acceptance.md`） |
| 2（7–9 周） | 核心功能与集成，单元测试报告 | 契约三变更；各线单测（`backend/acceptance.md`） |
| 3（10–14 周） | 测试验证，≥2 项非功能验证，缺陷处置记录 | 性能/安全证据；四项附加功能（G1-1~G1-4，`design/addons.md`） |
| Final（15–16 周） | 可运行系统，change 全归档且规格一致 | 结题材料（`repo/sprints.md`） |

## 4. 评分维度（原文 → 本项目注意）

| 维度 | 分值 | 本项目注意 |
|---|---|---|
| 产品价值与范围控制 | 10 | MVP 边界合理（`design/sprint0-scope.md`） |
| 生成式软件开发（SDD） | 10 | change 链路完整、规格可验收、归档后一致（`common/openspec-rules.md`） |
| 软件开发过程实践 | 40 | 技术设计文档/ Git/PR/看板/各 Sprint 完成度 |
| 软件测试实践 | 40 | 单元/集成/系统测试，正向+异常，非功能证据 |

## 5. 项目展示 Demo Day

12 分钟（10 产品 + 2 问答），覆盖：用户问题/价值、架构决策、核心场景、一个 change 从规格→实现→测试→归档、测试概述、总结（关键数据/已知问题/亮点/教训）。
