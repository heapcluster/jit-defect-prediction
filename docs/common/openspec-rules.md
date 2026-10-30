# OpenSpec 规则（每次改动必须执行规范）

> 公共铁律 ｜ 关联：`docs/repo/openspec-workflow.md`、`docs/backend/openspec-compliance.md` 等
> 🎯 Nothing Is True, Everything Is Permitted —— 但**过程证据必须留下**：改需求/接口/字段，先走 change。

## 🔴 总纲

**课程原文：「需求变更必须通过同步新增或修改管理工具及 OpenSpec change 记录，不得只改代码而不更新规格。」**

改了行为就必须同步 spec 或契约；只改代码不更新规格 = 课程判定为缺陷。

## 1. 什么时候必须提 change（触发条件）

| 你要做的 | 走什么 |
|---|---|
| 新增能力 / 新接口 | 新 change（propose → apply → archive） |
| 改接口字段 / 响应结构 / 错误码 | 契约三变更 change |
| 改库表字段 | 契约一变更 + 对应 change |
| 改特征口径 | 升 `feature_version` v2 + change（`model/README.md` §2.8） |
| 改页面要的字段 | 先改契约 / 提 change，前端不自己造 |
| 纯修复 Bug（不改规格语义） | `type:bug` Issue + PR，仍同步受影响 spec |
| 纯视觉/文档笔误 | 可不走 change，但 PR 仍须审阅 |

## 2. 标准生命周期（SDD）

```
propose（写码前）→ 规范评审（提案人≠审阅人）→ apply（按 tasks 勾选+验证）
→ PR（描述写 change id，非作者审阅）→ archive（合入后，规格并入 specs/）
```

- **顺序错了（码完补提案）= 没走 SDD。**
- `tasks.md` 勾了 ≠ 功能合格，要有运行/验收测试证据。
- archive 后**当前规格必须与产品一致**（Final Release 验收项）。

## 3. 字段一致铁律（跨线）

- 接口 `features` 14 项键名、库表字段名、页面变量名，**三处同一来源**（契约一/二），禁止各写一份。
- 任何偏离 = 课程「规格与代码不一致」缺陷。

## 4. 与 Sprint 节奏

- Sprint 开始先立提案；Sprint 中变更同步进 change；Sprint 末归档清零（未归档=缺口）。
- 当前待清零：`model-expansion`(4.4)、`nfr-evidence-scripts`(4.1/4.3/4.4)、已归档 `data-collection-and-szz-labeling`(5.4)。

## 5. 工具

- `openspec init` 只在仓库根跑一次（已初始化，勿重跑；子目录执行会生成第二份规范，追溯失效）。
- `openspec list` / `openspec validate <change>` / `openspec archive <change-id>`。
- `config.yaml` 的 `context:` 填技术栈，变更要同步改。

## 6. `tasks.md` 统一格式与强制「测试与验证」板块（2026-10-13 起）

**起因：课堂反馈 —— openspec 各人写法不一；每份 `tasks.md` 末尾必须有「测试和验证」板块，确保 propose 真正落地。**

- 统一模板：**`docs/common/openspec-task-template.md`**（文件头四行、任务编号、证据写法、测试板块五节、归档自检五条）。
- `openspec/config.yaml` 的 `rules.tasks` 已把该板块立为**强制**：**板块缺失 = 提案不完整，不得进入 apply**。
- 三层测试责任（与 `docs/common/test-strategy.md` 同源）：
  **单元测试** = 写该段代码的人，提 PR 前完成；
  **集成测试** = 大版本合并后，由负责合入的一条线组织；
  **验收测试** = 交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走。
- 铁律：**勾了 tasks ≠ 功能合格**；「已实现」与「已验收」是两个状态，不得混用。
- 存量 7 份已于 2026-10-13 全部补齐（已归档 5 份按实际已发生的验证回溯补录，**不倒填**）。

## 7. 文档线合入规则

组长蒋励（GitHub 账号 `jolly326`）的 `docs/` 类 PR 按 `docs/repo/collaboration.md` §3.8 判断：会造成运行失败、契约冲突、虚假证据或泄露敏感信息的问题须修复；纯格式和非关键措辞先留评论，不因小问题阻断。仍须非作者审阅。
