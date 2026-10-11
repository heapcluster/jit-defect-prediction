# OpenSpec 规范驱动开发（SDD）流程

> 合并自原 `docs/collaboration.md` §6（已并入本文件） ｜ 负责人：苏哲勋 ｜ 关联：`docs/common/openspec-rules.md`
> 课程：「使用 OpenSpec 框架实践规范驱动开发（SDD）。每组须初始化 OpenSpec，并将 openspec/ 及相关 AI 工作流文件一并提交版本控制。」

## 🔴 核心

**propose → apply → archive；先有提案后有代码。代码写完了再补提案 = 没走 SDD。**

## 1. 一个 change 怎么走

| 阶段 | when | 谁 | 产出 | 约束 |
|---|---|---|---|---|
| propose | 做新能力/改规格，**写码前** | 提出人 | `changes/<id>/`：proposal+specs+design+tasks | 顺序：先提案后代码 |
| 规范评审 | 提案完、写码前 | 苏哲勋（≠提案人）+ 相关线 | PR 审阅意见 | 评的是规格不是代码 |
| apply | 提案通过 | 提案人 | 按 tasks 实现+勾选；`openspec validate` | 每任务有可验收单元；勾选≠合格 |
| PR+审阅 | 实现完 | 作者+苏哲勋 | PR（写 change id） | 走 §3 流程 |
| archive | PR 合后 | 提案人 | `openspec archive`；规格并入 specs/ | **归档后规格必须与产品一致** |

## 2. 三条易违反

- 码完补提案 = 没走 SDD。
- tasks 勾了 ≠ 功能合格（要有运行/验收测试证据）。
- 改需求只改码不改规格 = 缺陷（走 `defect-management.md`）。

## 3. 与 Sprint 的节奏

| 时点 | 动作 |
|---|---|
| Sprint 开始 | 本 Sprint 能力**先立 change 提案**；无提案的代码不收 |
| Sprint 中 | 按 tasks 实现+勾选；变更同步登记进 change |
| Sprint 末（回顾前） | **归档清零**：已合 change 一律 archive；未归档=缺口，进下 Sprint 第一优先级 |

当前遗留（2026-10-05）：`model-expansion`（4.4 未勾）、`nfr-evidence-scripts`（4.1/4.3/4.4 未勾）、已归档 `data-collection-and-szz-labeling`（5.4 未勾）—— Sprint 1 内清零。

## 4. 工具约定

- `openspec init` 只在仓库根跑一次（已初始化，勿重跑）；子目录执行会生成第二份规范，追溯失效。
- `openspec list` / `openspec validate <change>` / `openspec archive <change-id>`。
- `config.yaml` 的 `context:` 填技术栈与团队约定，技术栈变更要同步改。
