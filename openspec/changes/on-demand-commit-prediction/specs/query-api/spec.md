## MODIFIED Requirements

### Requirement: 提交详情查询

`GET /api/commits/{commit_hash}` SHALL 返回提交元信息、14 项特征值与 `explanation`；`features` SHALL 读自 `commit_feature` 表，键名与 `docs/model/feature-columns.md` 逐字一致；本响应 MUST NOT 返回真实标签。优先显示表内全局默认模型的预测；若该提交没有默认模型预测但有其他模型预测，SHALL 回退到该提交已有模型中版本序最新的一条，不得误报尚未预测。

#### Scenario: 哈希不存在

- **WHEN** 以不在 `commit` 表中的 `commit_hash` 查询
- **THEN** 返回 40400（HTTP 404），message 为 `commit not found`

#### Scenario: 提交存在但尚无预测

- **WHEN** 查询的提交在 `commit` 表存在但 `prediction` 表无对应行
- **THEN** 返回 `code` 0，`risk_score` 与 `model_name` 为 null、`explanation` 为空数组

#### Scenario: 在线模型与历史默认模型不同

- **WHEN** 某提交只有在线模型的预测，表内全局默认模型在该提交无预测
- **THEN** 详情展示该提交已有预测的风险和模型名，不返回 null 冒充未预测
