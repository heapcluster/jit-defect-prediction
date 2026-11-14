## MODIFIED Requirements

### Requirement: 提交详情查询

`GET /api/commits/{commit_hash}` SHALL 返回提交元信息、所选模型预测时间与风险分、Kamei 14 维 log 特征、解释因子及 SZZ 真标签 `is_bug_inducing`；未打标为 `null`，MUST NOT 变成 0，也不返回已下线的人工 `label` 对象。显式给定 `model_name` 时 SHALL 仅查该模型；省略时 SHALL 与列表共用注册表默认模型，MUST NOT 自动回退到另一模型的预测行。

#### Scenario: 已有提交详情

- **WHEN** 查询存在且有预测行的提交
- **THEN** 返回该提交与单个模型的风险分、特征、解释和真实标签

#### Scenario: 尚未预测

- **WHEN** 提交存在但所选模型没有预测行
- **THEN** `risk_score` 与 `predicted_at` 为 `null`，MUST NOT 显示成零风险

#### Scenario: 显式查询非默认模型

- **WHEN** 同一提交已有非默认模型预测，详情请求显式传入该 `model_name`
- **THEN** 返回该模型的预测值和模型名，不以默认模型缺行判定为未预测

#### Scenario: 不跨模型回退

- **WHEN** 提交仅有另一模型预测，详情请求未传 `model_name`
- **THEN** 按默认模型返回未预测状态，MUST NOT 把另一模型的风险分回显为默认模型
