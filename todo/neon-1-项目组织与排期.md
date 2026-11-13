# neon — 项目组织与排期

> 任务编号：N-1｜负责人：neon｜板块：任务调度｜优先级：P0
> 依赖：无｜关联依据：`docs/common/project-requirements.md` 项目协作规则

## 目标

把组内任务按 Sprint 组织、映射看板、持续跟踪，并保留过程记录。

## 依据（docs/common 原文）

> 使用飞书多维表格/华为云CodeArts/禅道（ZenTao）进行项目管理，看板中任务应能对应到Sprint和OpenSpec的change/task。——《docs/common/project-requirements.md》
>
> 每组每周五课上需进行一次简短进展汇报，并产出工作周报，写明已完成工作、下一步和存在问题。——同上

## 范围

**做：**
- Sprint 排期与依赖排序。
- 看板映射（任务 ↔ Sprint ↔ OpenSpec change/task）。
- 每周五进展汇报与周报。
- PR 审阅人分配。

**不做：**
- 不写产品代码（归蛋神的蛋）。
- 不写测试文档与规范（归 sober）。
- 不做具体测试执行（可派 lsh）。

## 当前未完成

已有子任务拆分，缺排期、看板映射与周报。

## 输入

- `todo/` 各人任务文档。
- `openspec/changes/` 变更清单。

## 输出（交付物）

- Sprint 排期表。
- 看板任务映射。
- 周报（连续）。

## 依赖与前置

- 前置：各人任务已定义。
- 协作：技术问题找 **蛋神的蛋**，文档规范找 **sober**。

## 验收标准

- [ ] 看板能按 Sprint 查看进度。
- [ ] 任务能对上 OpenSpec change/task。
- [ ] 周报连续、含已完成/下一步/问题。

## 约束（用 agent 执行）

- 排期贴合真实进度，不把未完成项标成已完成。
