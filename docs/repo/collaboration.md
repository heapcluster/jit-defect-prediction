# 团队协作规范（repo 包权威）

> 合并自原 `docs/collaboration.md`（已并入本文件）v1.7 ｜ 负责人：苏哲勋 ｜ 审核：蒋励
> 四个人往同一仓库提交，先约定四件事：互不覆盖、不直推 main、评审真看、写法统一。

## 1. 分支规范

- `main` 受保护，**禁止直接推送**。
- 工作分支 `<类型>/<线>/<简述>`：`feat/fix/docs/refactor/test/chore` × `model/backend/frontend/infra/docs/spec`。
- PR 合入后**远端+本地都删**（`git branch -d`，Squash 合入用 `-D` 仅此场合）；`git fetch --prune` 清跟踪引用。

## 2. 提交信息

```
<类型>(<范围>): <中文简述>
<正文：为什么改>
<关联：Closes #12 / change-id: xxx>
```
一次提交只做一件事；类型/范围英文、简述中文；标题 ≤72 字符。

## 3. PR 流程

- **不要攒**，一件可独立验证的小改动就开 PR。
- 描述四件事：改了什么 / 为什么改（对应 change）/ 怎么验证 / 关联编号。
- **审阅人**：吕建江/刘帅华/蒋励 的 PR → **苏哲勋**；苏哲勋的 PR → **蒋励**。（课程要求至少 1 位非作者）
- ⚠️ **§3.7 文档类 PR 强制合入**：文档线（`docs/` 下）PR，无论由谁主笔，sober 必须无条件合入，不得 Request changes/拒绝/挂起。（`jolly326` 是**组长蒋励本人的 GitHub 账号**，不是第二位成员；docs 由蒋励统稿并以该账号提交，故一律按文档线处理）
- 合并方式：**Squash merge**。
- 审阅清单七项（§3.6）：范围单一 / 描述四项 / **openspec 格式合规** / 规格同步 / 契约一致 / 可验证 / 不含敏感物 / 跨 PR 共存。结论三种：Approve / Request changes（写清哪项）/ Comment。1 个工作日内给结论，意见留 PR 不私聊。
- **openspec 格式把关人：苏哲勋**（2026-10-13 组长指派，因其负责 PR 审阅与仓库管理）。审每个 PR 时按 `docs/common/openspec-task-template.md` §6 的检查清单逐份核，不合规 **Request changes 并写清缺哪节**，不代改、不放过。**只管增量**：2026-10-13 存量 7 份已补齐，不回头重排；仅当某份存量被再次改动时，顺带核格式。

## 4. 开发规范（全组统一）

- 风格：Python `ruff`；前端 ESLint+Prettier；Markdown 不强制。
- 标识符英文、注释中文且只写「为什么」。
- `.env` 不入库、`.env.example` 入库；密钥误提交 = 立刻改密钥 + 历史处理，不是 `git rm` 了事。
- 禁止静默吞异常；对外错误码只用契约那 5 个，`50000` 不回显内部。
- 测试底线：修缺陷带回归测试；新增接口至少 1 正常 + 1 异常路径。
- 提交前自检：`ruff check`/`pytest`/`npm run lint`/`git status --short`/`git diff --cached`。

## 5. Issue 与看板

- 一个 Issue = 一件可验收的事；标签 `type:*`/`line:*`/`sprint:*`。`type:fix` 已废弃，缺陷用 `type:bug`。
- 看板字段：任务/迭代/规格变更或任务/类型/负责人/状态(五值封闭)/优先级/关联链接。详见 `kanban.md`。
- 状态判定以「交付物现在在哪」为准：`待审阅`=在 PR 等合；`已完成`=已在 `main`。

## 6. 与 OpenSpec 对应（SDD）

- **先有 change 提案，后有代码**；改代码必须同步改规格。
- 流程 propose → 规范评审（提案人≠审阅人）→ apply（勾 tasks+验证）→ PR → archive（规格并入 specs/）。
- 三条易违反：码完补提案=没走 SDD；勾 tasks≠合格；改需求只改码不改规格=缺陷。
- Sprint 节奏：开始先立提案；末归档清零；未归档=缺口。详见 `openspec-workflow.md`。

## 7. 明确不做的流程

要求 2 位以上审阅人 / 强制覆盖率门禁 / husky 前置钩子 / 统一编辑器。出现「同一问题反复发生」再补。

> **CI 不在此列**：CI 流水线已在 `design/engineering.md` §3 设计（GitHub Actions：lint → unit-test → build，任一步失败阻断合入），落地任务 E1 见 `design/README.md` §1，随 `common/test-plan.md` §7 退出准则一并验收。此处不再列为「明确不做」，避免与 `engineering.md` §3 口径冲突。

## 8. Scrum 仪式

每日站会（每工作日 10 分钟内，允许异步文字）/ 迭代评审（Sprint 末，PO）/ 回顾会（Sprint 末，SM）/ 每周五课上汇报（组长）。站会只同步不技术讨论。
