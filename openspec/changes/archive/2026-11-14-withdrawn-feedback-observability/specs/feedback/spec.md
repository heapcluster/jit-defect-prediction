## ADDED Requirements

### Requirement: 人工缺陷标签写入

`PUT /api/commits/{commit_hash}/label` SHALL 以 `label_method="manual"` 写入或更新 `commit_label` 行（`is_bug_inducing` 取请求 `is_defect` 的 0/1，`labeled_at` 取当前 UTC），并返回该标签。`is_defect` SHALL 为三态：`true` = 引入缺陷、`false` = 确认非缺陷（保留标签行，会计入质量指标的 `tn`/`fp`）、`null` = 撤销。撤销 SHALL 删除该 commit 的 `manual` 标签行，并返回 `is_defect=null`、`labeled_at=null`；`MUST NOT` 用 `is_defect=false` 顶替撤销 —— 否则「已撤销」会被当成「已确认非缺陷」留在库里并污染指标。`commit_hash` 不存在于 `commit` 表时 SHALL 返回 40400；请求体非法（缺 `is_defect`，或值既非布尔也非 `null`）SHALL 返回 40001。MUST NOT 使用 5 个契约错误码之外的码。

#### Scenario: 标记为引入缺陷

- **WHEN** 对已存在的 commit 提交 `{"is_defect": true}`
- **THEN** 返回 `code=0` 且 `data.is_defect=true`、`labeled_at` 为当前 UTC；`commit_label` 新增 `label_method="manual"` 的一行

#### Scenario: 确认非缺陷（保留标签行）

- **WHEN** 同一 commit 再次提交 `{"is_defect": false}`
- **THEN** 该 commit 的 manual 标签行 `is_bug_inducing` 更新为 0，`labeled_at` 刷新，`MUST NOT` 删除该行（该样本计入 `tn`/`fp`）

#### Scenario: 撤销标记（回到未标注）

- **WHEN** 一个已有 manual 标签的 commit 提交 `{"is_defect": null}`
- **THEN** 删除该 manual 标签行，返回 `code=0`、`data.is_defect=null`、`data.labeled_at=null`；详情 `data.label` 回到 `null`，该样本不再计入任何质量指标

#### Scenario: 撤销未标注的 commit（幂等）

- **WHEN** 对一个没有 manual 标签的 commit 提交 `{"is_defect": null}`
- **THEN** 返回 `code=0` 且 `data.is_defect=null`，`MUST NOT` 报错，`MUST NOT` 创建标签行

#### Scenario: commit 不存在（异常）

- **WHEN** 对一个不存在于 `commit` 表的 `commit_hash` 提交标签
- **THEN** 返回 `code=40400`、`data=null`，`MUST NOT` 静默创建孤立标签行

#### Scenario: 参数非法（异常）

- **WHEN** 请求体缺少 `is_defect`，或 `is_defect` 取值既非布尔也非 `null`（如 `0`、`"true"`）
- **THEN** 返回 `code=40001` 且 message 指出参数非法，`MUST NOT` 写入任何行

### Requirement: 标签可见与按标签过滤

`GET /api/commits/{commit_hash}` SHALL 在 `data.label` 返回该 commit 的 manual 标签（`is_defect` / `labeled_at`），无标签或已撤销时为 `null`。`GET /api/commits` SHALL 支持 `has_label=true` 查询参数，仅返回存在 manual 标签行的 commit；`MUST NOT` 因过滤而触发任何新预测。

#### Scenario: 详情展示标签

- **WHEN** 请求一个已被标记为引入缺陷的 commit 详情
- **THEN** `data.label.is_defect=true`，并带上 `labeled_at`

#### Scenario: 未标记（边界）

- **WHEN** 请求一个从未被标记的 commit 详情
- **THEN** `data.label` 为 `null`，`MUST NOT` 返回占位空对象

#### Scenario: 仅看已确认

- **WHEN** 以 `has_label=true` 查询 commit 列表
- **THEN** 仅返回存在 manual 标签的 commit，其余字段口径不变，且未触发任何预测
