# 术语表（common 包）

> 维护：蒋励 ｜ 新成员先读

| 术语 | 含义 |
|---|---|
| JIT | Just-in-Time 缺陷预测：在**提交粒度**预测是否引入缺陷 |
| SZZ | 从修复提交反向追溯引入缺陷的提交；本组自研标准行级 + 文件级简化版 |
| `szz` / `szz_lite` | 两种标签方法（`label_method`）；逐数据集交叉比对 |
| Kamei 14 项 | 经典提交变更度量元：`ns nd nf entropy la ld lt fix ndev age nuc exp rexp sexp` |
| 特征口径 | 特征的取值处理约定（除 `fix` 取对数；`la/ld/lt/nuc` 归一化）；见 `feature-columns.md` |
| SHAP | 模型解释方法；本组 `explanation` 用它，逐特征带 direction |
| Effort-unaware / Effort-aware | 两类评估指标：不计审查成本 / 按审查精力算性价比 |
| OpenSpec | 规范驱动开发框架；`openspec/` 含 proposal/specs/design/tasks |
| SDD | Specification-Driven Development，先规格后代码 |
| change | OpenSpec 一次变更提案（目录 `openspec/changes/<id>/`） |
| spec | 能力规格（`openspec/specs/<cap>/spec.md`）；归档后并入 |
| MVP | 最小可行产品 |
| DoD | Definition of Done：代码能跑+有验证+规格同步+非作者审合 |
| Sprint | 课程 4 个迭代（S0–S3 + Final） |
| A+C 交付 | 跨线方案：A 后端加载 `.pkl` 实时推理；C 数据线出 `prediction_result.csv` 由后端导入 |
| 时间序切分 | 按 `committed_at` 前 70%/后 30%，禁随机（防时序泄漏） |
| NFR | 非功能需求（安全/性能/可靠性/易用性） |
| 三类契约 | 契约一库表/契约二特征/契约三接口（冻结点） |
| 合并策略 | 默认 Squash merge；`main` 受保护 |
