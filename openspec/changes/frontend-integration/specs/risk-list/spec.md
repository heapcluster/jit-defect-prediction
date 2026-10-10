## Purpose

按风险概率降序展示提交列表，支持筛选与分页，点击行进入提交详情，回答「哪些提交最该先看」。

## ADDED Requirements

### Requirement: 按风险降序展示

风险列表 MUST 按 `risk_score` 降序排列，MUST NOT 开放自定义排序。风险值 MUST 由前端 ×100 转百分比并保留一位小数。

#### Scenario: 正常加载列表

- **WHEN** 打开风险列表页且接口返回 `items`
- **THEN** 展示按 `risk_score` 降序的提交列表，风险列显示百分比与色条

#### Scenario: 风险值转百分比

- **WHEN** 接口返回 `risk_score = 0.8732`
- **THEN** 页面显示 `87.3%`，MUST NOT 显示 `0.8732` 或后端拼接的百分比字符串

### Requirement: 筛选

列表 MUST 支持 `model_name`、`min_risk`、`start_time`/`end_time` 三项筛选，筛选后结果仍按 `risk_score` 降序。

#### Scenario: 按最低风险筛选

- **WHEN** 用户填入 `min_risk = 0.5` 并查询
- **THEN** 只返回 `risk_score >= 0.5` 的提交

### Requirement: 分页

列表 MUST 支持 `page`/`size` 分页，默认每页 20 条，`size` 上限 100。

#### Scenario: 翻页

- **WHEN** 用户点击下一页
- **THEN** 请求携带递增的 `page`，列表更新为该页数据

### Requirement: 点击行跳详情

点击任意行 MUST 跳转提交详情页，路由携带 `commit_hash`。

#### Scenario: 点击行跳转

- **WHEN** 用户点击某一行
- **THEN** 路由跳转到 `/commit/{commit_hash}`，详情页能拿到该哈希并加载对应提交
