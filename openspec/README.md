# OpenSpec 使用说明

OpenSpec 记录**产品应该怎样工作**，并保存每次改动的来龙去脉。阅读时先看现行规格，再看正在实施的变更；历史归档不能代替当前要求。

| 要找什么 | 位置 | 用途 |
| --- | --- | --- |
| 现行要求 | [`specs/`](specs/) | 已生效的能力规格，按 capability 分文件。 |
| 待实施或待验收的改动 | [`changes/`](changes/) | 提案、设计、任务、规格增量与测试证据。 |
| 历史记录 | [`changes/archive/`](changes/archive/) | 已完成或已撤回的旧提案；撤回件不并入现行规格。 |
| 产品与技术契约 | [`../docs/README.md`](../docs/README.md) | 当前范围、接口、数据、页面及测试结果。 |
| 归档核对结果 | [`changes/README.md`](changes/README.md) | 每个活跃 change 的进度、阻断原因和完成条件。 |

## 写一个 change

1. 在 `changes/<change-id>/` 写 `proposal.md`：说明原因、改变什么、影响哪些能力及范围。
2. 在 `specs/<capability>/spec.md` 写增量：`ADDED` / `MODIFIED` / `REMOVED` 下使用稳定的 `### Requirement:` 标题。每条要求写清正常场景和必要的异常或边界场景；场景使用 `WHEN` / `THEN`。
3. 有跨模块决策时写 `design.md`，记录取舍和接口，不重复提案。
4. 按 [`TASKS_TEMPLATE.md`](TASKS_TEMPLATE.md) 写 `tasks.md`。任务完成与功能验收分开记录；没有执行证据时保留未勾选。
5. 变更代码或技术契约时，同步更新对应的 [`../docs/`](../docs/) 文件，并在 PR 中给出命令、结果与证据链接。

`.openspec.yaml` 仅在需要自定义 schema 或生成上下文时使用，不要求每个 change 都有。

## 何时归档

归档前同时核对四件事：**实现已合入、Scenario 有可复核的测试或验收结果、增量能正确并入现行规格、飞书看板状态已更新**。仅有任务勾选、旧报告或通过的格式校验，均不能证明功能完成。

- 条件齐全：运行 OpenSpec 归档命令，复查 `specs/` 与代码、`docs/` 一致。
- 工作未完成：保留在 `changes/`，写明负责人、缺少的证据与完成条件。
- 范围取消：在归档目录保留 `WITHDRAWN.md`，明确**撤回且未应用 delta**。

当前 10 份活跃 change 都还有未完成任务，逐项结论见 [`changes/README.md`](changes/README.md)。不要为达到“全部归档”的数量目标，把未完成项移入归档。

## 校验

在仓库根目录运行：

```powershell
openspec validate --specs --strict
openspec validate --changes --strict
python openspec/check_structure.py
```

前两项检查 OpenSpec 语法与结构；最后一项检查本仓库的任务模板、编号、已勾选任务的路径和活规格引用。它们都不能代替真实运行和人工验收。若本机未安装 OpenSpec CLI，在 PR 中写明“未执行”，不要写成通过。

## 文字和版式

统一写法见 [`WRITING_GUIDE.md`](WRITING_GUIDE.md)。本目录使用可在 GitHub、飞书和 OpenSpec CLI 中稳定显示的 Markdown：标题建立层级，**加粗**强调结论，代码样式表示路径或命令；列表和表格前后留空行。Markdown 文件不指定字体或文字颜色，状态必须写出文字，不能只靠颜色区分。
