# 趋势看板（TrendBoard）

## 页面与路由
- 页面名：缺陷引入趋势看板
- 路由：`/trend`
- 入口：导航栏「趋势看板」

## 布局
- 顶部：时间粒度（week / month）、模型选择、时间范围
- 主区：折线/柱状图，**横轴 = 时间（period），纵轴 = 数量**，至少两条线：
  - **提交数量**（`commit_count`）
  - **缺陷数量**（`defect_count`，真实缺陷 = `commit_label` 中 `is_bug_inducing=1` 的 szz 标签）
- 汇总卡：区间提交总数、高风险数、加权平均风险

## 交互
- 切换粒度 / 模型 / 时间范围刷新图表；
- 点击数据点下钻到该时段的风险列表；
- 数据点 < 2 时不画折线，只显明细表。

## 数据接口
| 用途 | 接口 |
|---|---|
| 趋势 | `GET /api/trends?granularity=&model_name=&start_time=&end_time=` |

## 说明
- 课程要求「缺陷引入趋势」= 时间 × 数量，**不能**用 `avg_risk`（0~1）的单条风险折线替代。
- `series[]` 需返回 `commit_count` 与 `defect_count`；`defect_count` 依赖 szz 真标签入库（当前无数据源，需后端补标签入库路径）。
