## Purpose

展示单次提交的风险值、风险等级、14 项特征与模型解释，回答「这一次提交为什么被判为高风险」。

## ADDED Requirements

### Requirement: 风险值与等级标签

详情页 MUST 显示风险值（前端 ×100 转百分比）与风险等级标签。等级阈值 MUST 只按 `docs/pages.md` 第 5 节一处定义：`>= 0.5` 高风险、`>= 0.3` 中等、其余常规。

#### Scenario: 高风险提交

- **WHEN** 加载的提交 `risk_score >= 0.5`
- **THEN** 显示百分比与「高风险」标签，标签着色与阈值口径一致

### Requirement: 特征值展示

详情页 MUST 按 `docs/contracts/feature-columns.md` 的键名展示 14 项特征，按五个维度分组。特征值为 0 MUST 照常显示；字段缺失 MUST 显示「—」，MUST NOT 静默当成 0。

#### Scenario: 特征字段缺失

- **WHEN** 接口返回的 `features` 缺少某个键
- **THEN** 该特征显示「—」，使链路问题可见，MUST NOT 显示 0

### Requirement: 风险解释条

详情页 MUST 展示 `explanation[]`，按 `|contribution|` 降序，页面显示前 8 项。每条读作「该特征把风险推高 / 降低」：`direction = "increase"` 向右、`"decrease"` 向左。

#### Scenario: 解释条为空

- **WHEN** 接口返回 `explanation` 为空数组
- **THEN** 显示「该模型未提供特征解释」，并保留特征值区域
