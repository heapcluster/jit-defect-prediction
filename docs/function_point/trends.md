# 趋势分析

**一句话**：按时间粒度聚合提交量与高风险数。它支撑前端 **趋势看板** 的两张趋势图。

## 对应前端功能
| 页面 / 入口 | 用这个功能点的哪部分 |
|---|---|
| 趋势看板 | 选架构 → 选模型（两级级联）+ 独立时间范围，看两张图：提交数 + 高风险数 |

## 各层职责
| 层 | 职责 |
|---|---|
| 后端 | `GET /api/trends` 聚合（`granularity` / `start_time` / `end_time` / `model_name`） |
| 前端 | 趋势看板两张图（提交数 + 高风险数）；架构 → 模型两级级联 + 独立时间范围；汇总卡展示平均风险 |

## 验收
- 切换粒度 / 架构 / 模型 / commit 时间区间都能刷新两张图；
- 图一绑定 `commit_count`（提交数），图二绑定 `high_risk_count`（高风险数）；MUST NOT 用 `avg_risk` 顶替图二；
- `avg_risk` 只用于汇总卡「加权平均风险」，不单列折线；
- 三张汇总卡由同一份 `series` 前端聚合（Σ `commit_count` / Σ `high_risk_count` / 加权平均风险），无独立接口；
- `high_risk_count` 按 `.env` 写死的 `HIGH_RISK_THRESHOLD` 统计；
- 数据来自 `prediction` 按选中模型聚合，不含未预测提交。
