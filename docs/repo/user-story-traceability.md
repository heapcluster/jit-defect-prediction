# 用户故事追溯映射（S5）

> 任务：苏哲勋 S5 ｜ 飞书 PRD 第五章「需求范围」：**核心 27 条（Epic A–F）+ 可选附加 4 条（Epic G）= 31 条**
> 目标：每条 User Story 能点回 `openspec/specs/` 或 `openspec/changes/`（看板「规格变更或任务」列可点开）。
> 2026-10-24 静态核验：#60 已于 10-16 合入，不再是前置阻塞。下表为仓库侧**候选映射**，不是飞书看板已回填证明；按现有摘要，核心 22 条有同主题 OpenSpec 路径，5 条工程流程故事只有仓库规范文档，不能硬凑 OpenSpec。PRD 原始故事 ID 与看板实际回填仍待飞书逐行复核。

## 1. 为什么做

课程要求「看板中任务应能对应到 Sprint 和 OpenSpec 的 change/task」。S5 = 把 31 条故事（核心 27 + 可选附加 G 4）逐条挂回 openspec，让「规格变更或任务」列可点开、可追溯。本质是收口活，不是写新需求。

## 2. 候选映射表（31 条；不是已回填记录）

> 口径：核心 27 条按「界面 / 数据模型 / 工程协作」三族归纳（对应 PRD Epic A–F），A=需求/界面类 → 多挂 `specs/` 能力；B=数据/模型类 → 挂 `data-collection-*`/`model-*` change；C=工程/协作类 → 挂 `repo` 规范与 `openspec` 流程。第 28–31 条为 PRD **可选附加功能 Epic G**：G1-1/G1-2（不进 MVP，Sprint 3）挂 `feature-addons-sprint3`，**G1-3 已提升为承诺范围挂 `public-dataset-quality`、G1-4 已提升为模型线主线挂 `semantic-feature-mainline`**。

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
| 28 | G | 缺陷可视化定位（行级，可选） | change `feature-addons-sprint3` |
| 29 | G | 高质量修复建议（可选） | change `feature-addons-sprint3` |
| 30 | G | 公开缺陷数据集加载与质量治理（**已提升为承诺范围**） | change `public-dataset-quality` |
| 31 | G | 预训练语义特征建模（**已提升为模型线主线**） | change `semantic-feature-mainline` |

## 3. 可挂 / 暂不能挂清单（2026-10-24）

| 核心故事序号 | 结论 | 可点目标或原因 |
|---|---|---|
| 1–9 | 可挂，待核 PRD 原始 ID 与看板状态 | `openspec/specs/query-api/spec.md`、`predict-api/spec.md`、`model-delivery/spec.md`；页面实施还可指 `openspec/changes/frontend-integration/`（#60 已合入） |
| 10–19 | 可挂，待核 PRD 原始 ID 与看板状态 | `openspec/specs/{commit-collection,szz-labeling,feature-extraction,model-training,model-coverage}/spec.md`；历史执行证据在 `openspec/changes/archive/2026-09-19-data-collection-and-szz-labeling/`、`2026-09-21-model-training-and-delivery/`、`2026-10-10-model-expansion/` |
| 20–21 | 可挂，待核 PRD 原始 ID 与看板状态 | `openspec/specs/predict-api/spec.md`、`db-schema/spec.md` |
| 22–26 | **暂不能按“逐条挂 OpenSpec”验收** | 看板、缺陷、周报、PR 审阅、OpenSpec 流程是工程协作事项；目前只有 `docs/repo/{kanban,defect-management,weekly-reports,collaboration,openspec-workflow}.md`，没有同主题的 change/spec。需 PO 裁定看板此列允许用这些规范文档作为追溯目标，或另立工程化 change；不能填无关 spec 凑数 |
| 27 | 可挂，待核 PRD 原始 ID 与看板状态 | `openspec/specs/nfr-evidence/spec.md` + `openspec/changes/archive/2026-10-10-nfr-evidence-scripts/` |

本表只核查**目标文件存在性与主题匹配**，不能证明 PRD 第五章的真实 27 行与本仓库摘要逐字一致，也不能证明飞书看板已填。之前“核心 22/27 待挂接”是看板回填状态，不应被误读为 22 条无可用规格；认证恢复后应先与 PRD 原始 ID 逐行对照，再补看板链接并记录无法挂接的 5 条裁定。

## 4. 操作

- #60 已合入；下一步把可挂条目的「规格变更或任务」列填上面的**实际路径**（归档 change 必须带日期前缀），并点开验证。第 22–26 条等 PO 对纯工程流程追溯目标的裁定。
- 纯飞书产物（如需求文档章节）填 `—`，不硬凑。
- Epic G 已拆分（2026-10-13）：G1-1/G1-2 挂 `feature-addons-sprint3`（仅立项不实现）；**G1-3 已提升为承诺范围挂 `public-dataset-quality`、G1-4 已提升为模型线主线挂 `semantic-feature-mainline`**；各 change 开工时按 tasks 逐条回填。
- 挂接完成 = S5 收口（看板该列可点开）。
