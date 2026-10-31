# OpenSpec 统一规范与阅读入口

本文件是仓库内 OpenSpec 的写作与协作入口。产品需求、排期和人员分工由飞书对应文档决定；这里记录**已经归档的规格条款、拟议变更及其验证证据**。最新设计以负责人确认的 [`docs/overview.md`](../docs/overview.md) 及其分册为准；若设计、活规格与代码不一致，应提交变更并标明差异，不因统一格式而擅自改口径。

## 1. 在哪里看

| 要看什么 | 路径 | 含义 |
|---|---|---|
| 已归档的活规格 | [`specs/`](specs/) | 按 capability 分目录，每份 `spec.md` 写 Requirement 与 Scenario；新设计可能尚未同步，阅读时对照设计与代码 |
| 尚在推进的变更 | [`changes/`](changes/) | 每个 change 一个目录，包含提案、任务、可选设计和规格增量 |
| 已完成的变更过程 | [`changes/archive/`](changes/archive/) | 历史记录；判断**当前行为**仍以 `specs/` 为准 |
| 生成规则 | [`config.yaml`](config.yaml) | OpenSpec CLI 的项目上下文与各文档规则 |
| `tasks.md` 写法 | [`../docs/common/openspec-task-template.md`](../docs/common/openspec-task-template.md) | 固定文件头、编号及末尾五节验证板块 |
| 当前系统设计 | [`../docs/overview.md`](../docs/overview.md) | 系统全貌及 `docs/api/`、`docs/database/`、`docs/function_point/`、`docs/web_page/` 的入口 |

例如，在线预测的活规格见 [`specs/predict-api/spec.md`](specs/predict-api/spec.md)；某次改动的讨论过程则看 `changes/<change-id>/`。两者可能暂时不同，因为进行中的 change 尚未归档；活规格与最新设计的差异也要显式登记、安排对齐。

## 2. 一个 change 的统一结构

```text
openspec/changes/<kebab-case-change-id>/
├── proposal.md             为什么做、改什么、不做什么、影响范围
├── design.md               只有存在需要解释的技术取舍时才写
├── specs/<capability>/spec.md  行为变化的增量；纯重构可按 CLI 规则跳过
├── tasks.md                可验收的实施任务与测试证据
└── .openspec.yaml          需要显式指定 schema / skip_specs 时使用
```

- **提案**：标题与 `Why`、`What Changes`、`Capabilities`、`Impact` 顺序统一；写出范围边界和受影响的页面、接口、表或模型。没有变动的部分不写成新需求。
- **设计**：记录约束、选项、最终决策及理由、风险或待确认项；不复制提案正文。没有实质取舍时可不建 `design.md`，并在任务头说明。
- **规格增量**：使用 `## ADDED Requirements`、`## MODIFIED Requirements`、`## REMOVED Requirements`。每条写 `### Requirement: <稳定标题>`，用 SHALL/MUST 陈述可验证行为；至少一个 `#### Scenario: <具体场景>`，以 WHEN/THEN 表达输入与结果，并覆盖关键边界或失败路径。修改既有 Requirement 时核对完整原文和 Scenario，防止增量归档后静默丢失原语义；同一 capability 的同名 MODIFIED 条目不得与其他活跃 change 撞车。
- **任务**：按统一模板写四行元数据与连续的 `N.M` 编号。每项写具体动作、交付物、负责人或跨线交接，状态以实际交付为准。文件末尾保留“测试与验证”五节：单元、集成、验收、非功能、已知缺口。没有执行的测试写“未执行、原因、负责人和后续时间”，不填虚假的 passed，也不把勾选当成验收。
- **证据**：优先给仓库内相对路径、可复现命令、前置条件与实际结果；外部链接可补充，不能代替可核验路径。不得提交密钥、个人绝对路径、数据集或模型权重。

纯文案改错不必新建 change；行为、字段、错误码、数据口径或契约变更须先写 change。纯重构若确无规格增量，使用 `.openspec.yaml` 显式声明 `schema: spec-driven` 和 `skip_specs: true`，在 proposal 中说明行为不变并给回归证据。

## 3. 协作与归档

1. 作者先对照飞书需求、[`docs/overview.md`](../docs/overview.md) 与现行 `specs/` 明确范围，再提交 proposal；跨线口径由对应负责人共同确认。
2. 实施者按 tasks 交付，并同步规格增量与实际代码。每一条 SHALL/MUST 至少能对应一个测试或人工验收步骤；结果与缺口据实登记。
3. PR 描述写清改动、原因、验证命令及结果、关联 change。审阅者优先核对运行结果、契约一致性和证据真实性；纯排版或措辞差异留建议，原则上不阻断。
4. 合入并完成验证后归档 change，使现行 `specs/` 与已交付行为一致。归档目录是历史记录，不因新模板而批量重排。

在仓库根目录执行（已初始化，**不要在子目录再次 `openspec init`**）：

```bash
openspec list
openspec validate --changes --strict --no-interactive
openspec validate --specs --strict
```

验证失败时按输出修正对应 change；CLI 通过只证明结构和规格语法有效，不能代替程序测试及人工验收。归档前还要确认任务证据、未完成项和当前活规格；归档命令为 `openspec archive <change-id>`。
