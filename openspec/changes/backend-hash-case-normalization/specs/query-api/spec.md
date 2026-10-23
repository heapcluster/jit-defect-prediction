## MODIFIED Requirements

### Requirement: 提交详情查询

`GET /api/commits/{commit_hash}` SHALL 返回提交元信息、14 项特征值与 `explanation`；`features` SHALL 读自 `commit_feature` 表，键名与 `docs/contracts/feature-columns.md` 逐字一致；本响应 MUST NOT 返回真实标签。路径参数 SHALL 先按「40 位十六进制」校验，不合法 SHALL 返回 `40001`；校验通过后 SHALL 归一化为小写再查库，MUST NOT 用请求原文的大小写形式匹配 `commit` / `commit_feature` / `prediction`。响应 `data.commit_hash` SHALL 取库内值。

#### Scenario: 哈希不存在

- **WHEN** 以不在 `commit` 表中的 `commit_hash` 查询
- **THEN** 返回 40400（HTTP 404），message 为 `commit not found`

#### Scenario: 提交存在但尚无预测

- **WHEN** 查询的提交在 `commit` 表存在但 `prediction` 表无对应行
- **THEN** 返回 `code` 0，`risk_score` 与 `model_name` 为 null、`explanation` 为空数组（口径见 design D3）

#### Scenario: 大写或混合大小写哈希命中同一提交

- **WHEN** 以库内某提交哈希的全大写或混合大小写形式请求详情
- **THEN** 返回 `code` 0 与和小写请求逐字段相同的数据，`data.commit_hash` 为库内小写值，MUST NOT 返回 40400

#### Scenario: 归一化后仍不存在

- **WHEN** 以 40 位合法十六进制、但归一化为小写后库内无对应提交的哈希请求详情
- **THEN** 返回 40400（HTTP 404），message 为 `commit not found`，MUST NOT 因为大小写归一化而改判为 `40001`

#### Scenario: 非法字符仍按参数错误拒收

- **WHEN** 以 40 位但含非十六进制字符（任意大小写形式，如 `g` × 40 或 `G` × 40）的路径参数请求详情
- **THEN** 返回 40001（HTTP 400），MUST NOT 进入查库分支，MUST NOT 因为归一化而放宽字符集校验
