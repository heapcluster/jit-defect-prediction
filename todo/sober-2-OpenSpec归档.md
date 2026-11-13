# sober — OpenSpec 归档与一致性

> 任务编号：S-2｜负责人：sober｜板块：生成式软件｜优先级：P0
> 依赖：各人交付与证据｜关联评分：生成式软件开发（10）

## 目标

让 OpenSpec 的 change 链路完整、归档后规格与产品一致。

## 依据（docs/common 原文）

> 全部OpenSpec变更归档且当前规格与产品一致。——《docs/common/project-requirements.md》
>
> 归档前确认规格与代码一致，测试或验收证据已齐。——《openspec/config.yaml》archive 指引

## 范围

**做：**
- 逐个检查 change：完成则归档，未完成写明保留理由与计划。
- 归档后核对 specs 与产品一致（重点 nfr-evidence、model-coverage、predict-api、query-api、observability）。
- 检查 `tasks.md` 勾选是否有可复现证据。

**不做：**
- 不写产品代码或测试。
- 不为凑数虚构任务完成状态。

## 当前未完成

部分 change 未归档；部分 tasks 勾选缺证据。

## 输入

- `openspec/changes/`、`openspec/specs/`。
- 各人的测试/验收证据。

## 输出（交付物）

- 归档记录。
- 规格一致性核对结论。
- tasks 证据清单。

## 依赖与前置

- 前置：各线交付与证据齐备。
- 协作：证据找 **蛋神的蛋** / **neon**。

## 验收标准

- [ ] 归档后 specs 与产品一致。
- [ ] 每条勾选任务都有可复现证据。
- [ ] 没有"规格说做了、代码没做"的虚点。

## 约束（用 agent 执行）

- 不虚构完成状态；无证据的勾选如实标记。
