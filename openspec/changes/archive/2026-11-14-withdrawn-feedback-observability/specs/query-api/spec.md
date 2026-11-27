## ADDED Requirements

### Requirement: 解释因子可读化

`ExplanationItem` SHALL 携带 `label` 字段，为该因子对应的中文名（取自 14 项特征字典）；`predict`、commit 详情与 PR 理由 SHALL 共用同一份字典（`MUST NOT` 各处各维护一份）。未知因子名 SHALL 回退为原英文缩写，`MUST NOT` 报错。前端 commit 详情 SHALL 以横向条形图呈现贡献（正 / 负贡献分色、按绝对值降序），替代纯文本列表。

#### Scenario: 因子带中文名

- **WHEN** 某 commit 的 top 正贡献因子为 `la`
- **THEN** 该解释项返回 `feature="la"` 且 `label="代码改动量大"`

#### Scenario: 未知因子（边界）

- **WHEN** 解释项出现字典中不存在的因子名（如自定义 `foo`）
- **THEN** `label` 回退为 `"foo"`，`MUST NOT` 抛错或返回 null

#### Scenario: 前端条形图

- **WHEN** 打开 commit 详情页
- **THEN** 解释区以条形图按贡献绝对值降序展示，正 / 负贡献配色区分，并保留原始 `contribution` 数值
