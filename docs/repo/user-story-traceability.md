# 用户故事追溯映射（S5）

> 任务：苏哲勋 S5 ｜ 飞书 PRD 第五章 27 条 User Story（A/B/C 三 Epic）
> 目标：每条 User Story 能点回 `openspec/specs/` 或 `openspec/changes/`（看板「规格变更或任务」列可点开）。
> 现状：22/27 待挂接（卡在 #60 前置），5 条已挂。

## 1. 为什么做

课程要求「看板中任务应能对应到 Sprint 和 OpenSpec 的 change/task」。S5 = 把 27 条故事逐条挂回 openspec，让「规格变更或任务」列可点开、可追溯。本质是收口活，不是写新需求。

## 2. 映射表（27 条 → openspec）

> 口径：A=需求/界面类 → 多挂 `specs/` 能力；B=数据/模型类 → 挂 `data-collection-*`/`model-*` change；C=工程/协作类 → 挂 `repo` 规范与 `openspec` 流程。

| # | Epic | User Story（摘要） | 挂接目标（openspec） |
|---|---|---|---|
| 1 | A | 查看风险提交列表 | `specs/query-api` + change `predict-api` |
| 2 | A | 按风险排序筛选 | `specs/query-api` |
| 3 | A | 查看提交详情与特征 | `specs/query-api` |
| 4 | A | 查看风险解释（推高/降低） | `specs/query-api` + `specs/model-training`(解释) |
| 5 | A | 查看缺陷趋势看板 | `specs/query-api`(trends) |
| 6 | A | 趋势按周/月切换 | `specs/query-api` |
| 7 | A | 模型版本切换查看 | `specs/query-api` + `specs/model-delivery` |
| 8 | A | 在线预测某次提交 | `specs/predict-api` + change `predict-api` |
| 9 | A | 低风险提交跳过评审 | `specs/predict-api` |
| 10 | B | 从开源仓库挖数据 | change `data-collection-and-szz-labeling` |
| 11 | B | SZZ 识别引入缺陷提交 | `specs/szz-labeling` |
| 12 | B | 计算 14 项特征 | `specs/feature-extraction` |
| 13 | B | 训练经典模型 | `specs/model-training` + change `model-training-and-delivery` |
| 14 | B | 训练深度学习模型 | `specs/model-training` + change `model-expansion` |
| 15 | B | 两类指标评估 | `specs/model-training` |
| 16 | B | 8 种模型覆盖 | change `model-expansion` |
| 17 | B | 时间序切分 | `specs/model-training` |
| 18 | B | 全量预测落库 | change `model-training-and-delivery` |
| 19 | B | 缺陷概率解释 | `specs/model-training`(SHAP) |
| 20 | C | 接口鉴权 | `specs/predict-api` + 契约三 |
| 21 | C | 提交历史入库 | `specs/db-schema` |
| 22 | C | 看板管理任务 | `repo/kanban.md` |
| 23 | C | 缺陷记录与追踪 | `specs` + `repo/defect-management.md` |
| 24 | C | 每周周报 | `repo/weekly-reports.md` |
| 25 | C | PR 审阅协作 | `repo/collaboration.md` §3 |
| 26 | C | OpenSpec 变更流程 | `repo/openspec-workflow.md` |
| 27 | C | 非功能验证（性能/安全） | change `nfr-evidence-scripts` |

## 3. 操作

- #60 合入后，把每条的「规格变更或任务」列填对应 change id / spec 路径。
- 纯飞书产物（如需求文档章节）填 `—`，不硬凑。
- 挂接完成 = S5 收口（看板该列可点开）。
