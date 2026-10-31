# 风险列表页（RiskList）

## 页面与路由
- 页面名：风险列表
- 路由：`/risks`（或 `/commits`）
- 入口：导航栏"风险"/"提交"

## 布局
- 过滤栏：模型、风险区间、时间
- 主区：提交风险表格（hash / author / time / risk_score / 判定）

## 交互
- 排序（按风险）、筛选；
- 点击行进入提交详情。

## 数据接口
| 用途 | 接口 |
|---|---|
| 列表 | `GET /api/commits?page=&model_name=&risk_min=&risk_max=` |
| 覆盖 | `GET /api/commits/coverage` |
