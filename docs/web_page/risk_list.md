# 风险列表页（RiskList）

## 页面与路由
- 页面名：风险列表
- 路由：`/`
- 入口：导航栏「风险列表」

## 布局
- 过滤栏：搜索（q）、模型、最低风险（min_risk）、时间范围
- 主区：提交风险表格（commit_hash 前 8 位 / 作者 / 时间 / 风险分 + 风险等级标签）

## 交互
- 按 risk_score 降序；分页（默认 20，上限 100）；
- 点击行进入提交详情；点击哈希复制。

## 数据接口
| 用途 | 接口 |
|---|---|
| 列表 | `GET /api/commits?page=&size=&q=&model_name=&min_risk=&start_time=&end_time=` |
