# 趋势分析

纵向功能点：按时间粒度聚合提交量与高风险量。跨后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 后端 | `GET /api/trends` 聚合（`granularity` / `start_time` / `end_time` / `model_name`） |
| 前端 | 趋势看板双 y 轴绘图与交互 |

## 验收
- 切换粒度 / 选中模型 / commit 时间区间都能刷新两条 y 轴；
- 两条轴分别绑定 `commit_count` 与 `high_risk_count`，MUST NOT 用 `avg_risk` 顶替提交数；
- 数据来自 `prediction` 按选中模型聚合，不含未预测提交。
