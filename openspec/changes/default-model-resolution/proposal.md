## Why

PR #186 把查询侧的历史模型降级规则接入预测侧后，CI 暴露 400/500 错误码回归：数据库中有预测行的模型不一定仍在运行时注册表中。该 PR 尚未合并，本提案补回缺失的变更记录，不追认前一版规则已经获批。

## What Changes

- **BREAKING**：缺省请求的有效默认模型只从已加载模型中选择，历史预测行不能把已卸载模型提升为默认推理模型。
- 保留 PR 已提出的降级顺序：注册表冠军有行则使用冠军；否则选择有行的已加载模型中 `version_key` 最大者；没有已加载模型有行时读写均使用注册表冠军。
- 注册表为空时缺省预测返回 50000 与固定文案；显式传入未加载模型仍为 40001。显式查询历史模型的已有分数不受本提案限制。
- 同步候选按**当前已加载模型集合**判断覆盖缺口：缺任一在线模型的行即算待预测（不能因为默认模型或任意模型已有行就跳过）；注册表为空时退回有效默认模型单模型判据。
- 不修改数据库结构、前端、模型权重、特征算法、阈值校准和人工标签；不宣称已经补齐全部八模型历史缺口。PR 可达性与 SQLite 迁移仍分别由 #185/#184 承载。
- 不扩大 `docs/design/sprint0-scope.md` 的产品范围，保持建议性风险预警定位。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `query-api`：MODIFIED「风险列表查询」「趋势聚合查询」——缺省模型改为共享解析结果；顺带订正趋势阈值句（活规格仍写“固定常量 0.5”，实现自 #172/3379d4c 起读运行时配置）。
- `predict-api`：ADDED「有效默认模型解析」「同步候选按在线模型集合判断缺口」。**不用 MODIFIED「在线预测入口」**：该 Requirement 已被进行中的 change `on-demand-commit-prediction`（同一负责人）MODIFIED，两个未归档 change 撞同名 Requirement 会被 `infra/check_spec_references.py deltas` 判红；本 change 以 ADDED 承载新口径，并在 delta 内写明归档时须对齐那句旧文。

## Impact

- 后端：`backend/app/services/champion.py`、`services/commits.py`、`services/predict.py`、`api/sync.py`。
- 契约与测试：`docs/backend/api-spec.md`、上述 capability 的 delta，以及默认模型、同步、查询、质量与 PR API 相关测试。
- 测试数据需要以实际注册的 fixture 模型作为正常默认样本；已卸载历史模型另设回归场景，不删除边界断言来迁就实现。
- `on-demand-commit-prediction` 也声明了 `predict-api` 的“在线预测入口”，该重叠必须在应用/合入前对齐，不能绕过 MODIFIED 冲突门禁。
