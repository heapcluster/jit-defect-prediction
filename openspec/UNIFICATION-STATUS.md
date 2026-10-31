# OpenSpec 存量统一与待验收项

本页记录 2026-10-31 对当前仓库的整理状态，不代替 [`README.md`](README.md) 的写作规范，也不把未归档 change 当成现行规格。格式统一与真实交付验收是两件事。

## 已完成的规范整理

- 23 个活跃 change 的 `tasks.md` 统一使用四行元数据和“关联需求”；编号、五节测试与验证通过检查。17 个缺少 `.openspec.yaml` 的活跃 change 已补齐元数据；归档历史保持原貌。
- 修正活规格对已删除文档的引用；`python infra/check_spec_references.py links` 通过。按批准口径统一八分类器训练、有效默认模型解析、同步默认全已加载模型落库。`deltas` 检查同名 MODIFIED 冲突及不存在的目标标题。
- 已勾选任务若引用随 #187 删除的文件，改为固定提交的历史链接；这是历史交付记录，不是当前树的验收证据。`format` 检查会阻止以后用缺失的当前路径勾选任务。
- 以上三个仓库检查及其回归测试接入现有单个 `CI` 作业。它们是结构和引用检查，不能代替接口联调或真实权重压测。

## 尚不能宣称通过的验收

| 范围 | 当前状态 | 归档前需要的证据 |
|---|---|---|
| `architecture-refactor`、`feedback-observability`、`frontend-redesign`、`ops-hardening`、`quality-loop` | 任务分别为 13/13、15/15、14/14、13/13、14/14 勾选，仍在活跃区 | 核对当前设计与实现、重新执行相关测试、补当前提交可点的证据，再运行 OpenSpec CLI 归档；不凭勾选批量归档。 |
| 十八个只出现在活跃 change 中的 capability | 仍是提议中的规格增量 | 对应 change 合入并验收后，按正确顺序归档到 `specs/`；归档前不把提案复制成现行 Requirement。 |
| #187 删除的证据与代码路径 | 活跃任务中仍有历史记录或未来交付路径；旧链接已标历史，部分未完成任务所需文件当前不存在 | 各任务 owner 重跑当前提交的命令、补 PR/CI 链接或仓库内证据。不能把旧提交的 passed 计作当前验证。 |
| 在线八模型与同步规则 | OpenSpec 口径已按 owner 裁定统一；现行清单有八项 | 后端、模型、前端共同核实 8/8 权重加载、逐模型预测、同步幂等、默认模型回退和每模型性能；未实测不得写“八模型验收完成”。 |

## 复核命令

在仓库根目录运行：

```bash
python -m pytest -q infra/tests/test_spec_references.py infra/tests/test_ci_contract.py
python infra/check_spec_references.py format
python infra/check_spec_references.py links
python infra/check_spec_references.py deltas
openspec validate --changes --strict --no-interactive
openspec validate --specs --strict
```

本地前三项脚本已通过；本地 OpenSpec CLI 尚未安装，因此上面两条 `openspec validate` 尚未执行，不能写成已通过。历史任务中出现的旧路径与旧数值须按其发生时间阅读，当前交付以 `openspec/specs/`、当前设计和当前测试证据共同核实。
