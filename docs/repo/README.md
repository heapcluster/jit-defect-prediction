# repo 包（工程与协作）· 苏哲勋

> **你打开这个文件夹就能知道：你负责什么、最近要干什么、每次任务怎么干、改东西的红线在哪。**
> 包负责人：**苏哲勋**（工程化与协作线，兼 PO）｜ 目录：`infra/` `.github/` ｜ 审核：蒋励
> 配套依据：飞书《产品需求文档》Epic **A–F 全程可追溯**；OpenSpec `openspec/changes/`、`openspec/specs/`；看板/周报在飞书。

---

## 0. 👤 你的职责一句话

你是**工程化与协作线负责人 + PO**：搭好仓库工程基线（分支/PR/Issue/CI/模板）、推 OpenSpec 流程、管飞书看板与周报、做 PR 非作者审阅、把 31 条用户故事与 OpenSpec 逐条挂接。**不写业务代码**（数据/后端/前端各线自己负责）。

## 0.5 谁依赖这个包（阻塞关系）

本包是**全员的前置**——它不产业务功能，但任何一环缺失都会让别的线动不了。

| 依赖方 | 依赖什么 | 卡住的后果 |
|---|---|---|
| 全员（4 人） | 分支模型 + PR 非作者审阅规则（`collaboration.md` §3、`git-pr.md`） | 没有分支与审阅规则 → 任何 PR 无法合入 main，全线停摆 |
| 全员 | OpenSpec SDD 流程（`openspec-workflow.md` + `common/openspec-rules.md`） | 不立 change 就改码 = **SDD 缺陷（一票否决）** |
| 蒋励（SM） | 看板字段与状态判定（`kanban.md`）、周报模板（`weekly-reports.md`） | 周报与看板对不上账 → 过程证据失分 |
| 各线 | 缺陷管理五项（`defect-management.md`） | 缺陷无记录 → 测试实践 40 分缺项 |
| 蒋励（SM） | Sprint 日历（`sprints.md`）、用户故事追溯（`user-story-traceability.md`） | Sprint 边界与故事挂接不清 → 范围控制失分 |

> 反向依赖：本包**不依赖**任何业务包的产出（只读 Git / 看板 / Issue），因此它必须最早就位——Sprint 0 的「可协作工程基线」即指此。

## 1. 📋 你的任务清单（来自进度台账，带验收与下一步）

| # | 任务 | 验收标准 | 状态 | 你下一步 |
|---|---|---|---|---|
| S1 | 需求范围表回填（PRD 核心 27 条 User Story 状态写实；现扩为 31 条含 Epic G 4） | 状态不再「全未开始」与实际不符 | ✅已完成 | 已回填 22 完成/5 未开始 |
| **S2** | 用户调研问卷设计与发放（≥10 有效样本） | 问卷链接+回收记录；原截止 10/16 | 用户确认已解决（证据未核） | 10/24 用户告知无需再处理；不代发、不冒称已核满 ≥10 份，详见 `catchup-ledger.md` |
| S3 | 《用户调研报告》入 PRD 附录 | 报告入附录 B；第四章据实重写 | ✅已完成 | 已入 rev 329 |
| S4 | PR 审阅 #52/#33 非作者结论 | 两 PR 留 Approve/Request changes | ✅已完成 | 闭环 |
| **S5** | 31 条用户故事（核心 27 + 可选 G 4）与 OpenSpec 逐条挂接 | 每条能点回 change/spec；看板可点开 | 🔄进行中 | #60 已合入；`user-story-traceability.md` 有核心 22 条候选目标、5 条无同主题 OpenSpec 的清单，仍待 PRD 原始故事与飞书看板逐行核验 |
| S6 | 跨章一致性逐章过口径收口 | 需求/设计跨章口径一致 | ✅已完成 | PRD v0.6→v0.8、设计 v0.4→v0.5 |
| **S6+1** | A2-4 正样本比例判据方向订正 | 二选一订正；dataset_stats 同步 | 🔄进行中 | 仓库侧已按 40%–60% 区间内告警对齐；飞书 PRD 未核实订正，Issue #59 仍 open |
| S7 | 分支保护可自助核验说明 | `collaboration.md` 给核验步骤，照做能自查 | ✅已完成 | PR #57 已合入 |

> 实时状态以**飞书看板**为准。S2 由用户确认已解决，验收证据未核；S5/S6+1 仍需飞书侧核对。本仓库的 R1/R5 证据状态见 `r1-r5-evidence-2026-10-24.md`。

## 2. 🚀 后续工作开展方式（每次接到任务的标准动作 · 必须走 OpenSpec）

1. **认领/分派**：飞板置「进行中」；作为 PO 你把需求拆成看板行并对应 Sprint/change。
2. **需求变更必走 change**：任何范围/接口/字段变动 → 提 OpenSpec change（你推进节奏踩 Sprint）。
3. **本包自身改动也走 PR**：模板/规范改动由蒋励非作者审阅（**你自己的 PR 不能自己合**）。
4. **推流程**：change 立/审/归踩 Sprint；未归档清零；`openspec archive` 前确认 tasks 全勾且有证据。
5. **审阅别人 PR**：统一由你（苏哲勋）做非作者审阅，留 Git 平台记录（课程证据）。
6. **openspec 风格与格式统一把关**（2026-10-13 组长指派）：审 PR 时按 `docs/common/openspec-task-template.md` §6 检查清单逐份核 `tasks.md` 格式（文件头四行 / 任务编号连续 / 末尾「测试与验证」五节齐 / 证据路径可点），不合规打回并写清缺哪节，**不代改**。只管增量，存量 7 份已于 2026-10-13 补齐，不回头重排。
6. **周报/看板**：每周五收蒋励统稿；看板状态与 Git/周报三处同口径。
7. **回写**：看板置完成 + 台账 `catchup-ledger.md` 回填「✅日期+证据链接」。

> ⚠️ 课程硬要求：**改需求只改码不改规格 = 缺陷**；只勾 `tasks.md` ≠ 功能合格；所有 PR 合并前至少 1 位非作者审阅。

## 3. 🚫 你的红线

- **不写业务代码**：数据/后端/前端各线负责；你只管工程基线与流程。
- **文档线（`docs/`）例外**：组长蒋励（GitHub 账号 `jolly326`）的 `docs/` 类 PR，除 `repo/collaboration.md` §3.8 列出的六种必须 Request changes 的情形外，sober 直接 Approve 放行；**但不得无条件合入**——§3.8 是硬阻断，优先于「文档线合入更快」的约定；其余 PR 一律非作者审阅。
- **看板是权威**：任务日常状态以飞书看板为准，台账只追「补齐实证还差什么」。
- **模板不改**：周报/PR/Issue 模板基线在 `common/templates.md`，动模板要先共识。

## 4. 本包交付物与课程对应

| 课程要求 | 本包落地 |
|---|---|
| GitHub 协作：提交/分支/Issue/看板/OpenSpec 为过程证据 | 全套规范 + 标签 + 模板 |
| PR 合并前至少 1 位非作者审阅 | §3.3 统一苏哲勋审 |
| 飞书多维表格管理 + 看板对应 Sprint/change | `kanban.md` |
| 缺陷使用 Issue 管理（五项） | `defect-management.md` |
| Scrum：每周五汇报 + 周报 | `sprints.md` + `weekly-reports.md` |
| OpenSpec SDD（propose→specs→design→tasks） | `openspec-workflow.md` |

## 5. 子文件导航

- `collaboration.md` — 分支/提交/PR/开发规范/Issue（合并自 `repo/collaboration.md`）
- `git-pr.md` — 分支与 PR 规范速查
- `kanban.md` — 看板字段与状态口径
- `defect-management.md` — 缺陷管理（合并自 `repo/defect-management.md`）
- `defect-records.md` — 缺陷处置记录索引（五项字段 + 仓库证据；权威在 GitHub Issue）
- `weekly-reports.md` — 周报模板与填写规范
- `openspec-workflow.md` — OpenSpec SDD 流程
- `sprints.md` — Sprint 日历与节奏
- `user-story-traceability.md` — 31 条 User Story → OpenSpec 挂接映射（S5）
- `catchup-ledger.md` — 进度追平台账（全员任务+验收+状态）
- `demo-script-sprint1.md` — Sprint1 端到端演示脚本

## 6. 先读 common 里的哪几份

打开 `common/`：`openspec-rules.md`（每次改动必须走规范）、`team-charter.md`（分工与审阅人）、`templates.md`（模板基线）、`dev-handbook.md`（开工）。**common + 本文件 = 你开展工作的全部依据。**
