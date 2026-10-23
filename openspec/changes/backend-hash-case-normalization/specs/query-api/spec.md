## ADDED Requirements

### Requirement: 提交哈希大小写归一化

后端 SHALL 把请求中的 `commit_hash` 当作大小写不敏感的 40 位十六进制串处理：先校验（不合法 SHALL 返回 `40001`），校验通过后 SHALL 归一化为小写，再用于查库、写库与响应回显；MUST NOT 用请求原文的大小写形式匹配 `commit` / `commit_feature` / `prediction`。归一化 MUST NOT 放宽长度或字符集校验。`GET /api/commits/{commit_hash}` 与 `POST /api/predict` SHALL 对同一哈希的任意大小写形式给出一致结论，响应中的 `commit_hash` SHALL 为库内小写值。

#### Scenario: 大写或混合大小写哈希命中同一提交

- **WHEN** 以库内某提交哈希的全大写或混合大小写形式请求 `GET /api/commits/{commit_hash}`
- **THEN** 返回 `code` 0 与和小写请求逐字段相同的数据，`data.commit_hash` 为库内小写值，MUST NOT 返回 40400

#### Scenario: 归一化后仍不存在

- **WHEN** 以 40 位合法十六进制、但归一化为小写后库内无对应提交的哈希请求详情
- **THEN** 返回 40400（HTTP 404），message 为 `commit not found`，MUST NOT 因大小写归一化而改判为 `40001`

#### Scenario: 非法字符仍按参数错误拒收

- **WHEN** 以 40 位但含非十六进制字符（任意大小写形式，如 `g` × 40 或 `G` × 40）的路径参数请求详情
- **THEN** 返回 40001（HTTP 400），MUST NOT 进入查库分支，MUST NOT 因归一化而放宽字符集校验

#### Scenario: 预测接口的大小写幂等

- **WHEN** 以同一提交的大写形式与小写形式各调用一次 `POST /api/predict`
- **THEN** 两次都返回 `code` 0、`data.commit_hash` 均为库内小写值，且 `prediction` 表中该 `(commit_hash, model_name)` 只有一行（复合键按归一化值计算）
