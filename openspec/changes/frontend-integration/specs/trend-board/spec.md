## Purpose

按周/月聚合展示风险随时间的变化趋势，回答「风险随时间怎么变」。

## ADDED Requirements

### Requirement: 折线图

趋势看板 MUST 用 ECharts 绘制折线图：x 轴为 `period`，y 轴为 `avg_risk`（0~1 直接画轴，MUST NOT 转百分比）。粒度 MUST 支持 `week`（默认）与 `month`。

#### Scenario: 按周展示

- **WHEN** 用户选「周」粒度并查询
- **THEN** 折线 x 轴显示周周期（如 `2026-W30`），y 轴按 0~1 画平均风险

### Requirement: 汇总卡片

看板 MUST 展示三项汇总：提交总数（`commit_count` 求和）、高风险数（`high_risk_count` 求和）、平均风险（按 `commit_count` 加权平均，MUST NOT 简单算术平均）。

#### Scenario: 加权平均

- **WHEN** 各周期 `commit_count` 不相等
- **THEN** 平均风险按 `Σ(avg_risk × commit_count) / Σ(commit_count)` 计算

### Requirement: 明细表

看板 MUST 展示与图上数据点一一对应的明细表（`period` / `commit_count` / `avg_risk` / `high_risk_count`）。

#### Scenario: 明细对齐

- **WHEN** 折线图有 N 个数据点
- **THEN** 明细表恰有 N 行，且与图上周期一一对应

### Requirement: 数据点不足

当 `series` 少于 2 个数据点时，MUST NOT 画折线，只显示明细表并提示「数据点不足，无法绘制趋势」。

#### Scenario: 单周期数据

- **WHEN** 查询结果只有 1 个周期
- **THEN** 不画折线，显示明细表与「数据点不足」提示
