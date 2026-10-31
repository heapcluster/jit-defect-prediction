# 趋势分析

纵向功能点：按时间粒度聚合风险/缺陷趋势。跨后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 后端 | `GET /api/trends` 聚合（granularity / model_name / range） |
| 前端 | 趋势看板绘图与交互 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `trends.points[].bucket` | 时间桶 |
| `trends.points[].defect_count` / `avg_risk` | 趋势指标 |

## 验收
- 切换粒度/模型刷新图表；数据来自 prediction 聚合。
