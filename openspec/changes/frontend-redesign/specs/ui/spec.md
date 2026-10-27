## ADDED Requirements

### Requirement: 统一页面引导结构

每个一级页面 SHALL 以「一条 `PageHint`（一句话说明本页目的与下一步动作，右侧放主操作）→ `StatCard` 概览行 → 筛选栏 → 内容」的顺序组织，`MUST NOT` 在页面内重复写页面标题（标题由布局层统一提供）。页面级说明文案 SHALL 为一句、不超过 60 个字符，`MUST NOT` 以多段长文或命令行代替引导。

#### Scenario: 风险列表首屏

- **WHEN** 打开 `/`
- **THEN** 依次看到一句引导（含「补齐缺口 / 刷新」操作）、三张指标卡、筛选栏、表格；`MUST NOT` 出现两条以上重复说明同一件事的提示条；`MUST NOT` 用指标卡重复表格或分页器已经给出的数字（如条数）

#### Scenario: 空库引导（边界）

- **WHEN** 库内没有任何提交且无筛选条件
- **THEN** 显示「还没有数据」卡片，含一句说明、同步条数下拉与「开始同步」按钮，`MUST NOT` 展示大段命令行说明

#### Scenario: 趋势看板首屏

- **WHEN** 打开 `/trend`
- **THEN** 依次看到一句引导、三张汇总卡（区间提交 / 高风险提交 / 加权平均风险）、筛选栏、折线图；明细表只在数据点 < 2（画不出折线）时出现，`MUST NOT` 与折线重复展示同一份逐期数据

### Requirement: 概览指标先行

一级页面 SHALL 在内容之前给出不超过四张 `StatCard`，每张含标签、数值与一行注解；数值未知时 SHALL 显示 `—`，`MUST NOT` 显示 0 或空白。

#### Scenario: 服务降级时的状态卡

- **WHEN** `/api/health` 返回 `status="degraded"`
- **THEN** 「服务状态」卡显示「降级」并使用警示色，注解说明模型数与数据库状态

### Requirement: 风险等级标签统一

风险等级 SHALL 由 `RiskTag` 组件统一渲染：优先使用后端返回的 `risk_level`，缺失时按 `risk_score` 与默认阈值（0.5 / 0.2）兜底；`risk_score` 为 `null` 时 SHALL 显示「未预测」，`MUST NOT` 显示为 0%。

#### Scenario: 未预测的 PR

- **WHEN** PR 的 `risk_score` 为 `null`
- **THEN** 风险列显示「未预测」，`MUST NOT` 渲染 0.0% 或「低风险」

#### Scenario: 使用后端等级

- **WHEN** 后端返回 `risk_level="高"`
- **THEN** 标签显示「高风险」并使用 danger 色，前端 `MUST NOT` 用本地阈值覆盖后端结论

### Requirement: 质量看板

`/quality` SHALL 展示预测质量指标（精确率、召回率、F1、评估样本数）、混淆矩阵、当前与推荐阈值，并提供「按标签校准」（`POST /api/quality/calibrate`）与「应用推荐阈值」（`PUT /api/config`）两个操作。样本不足时 SHALL 给出「先去标记提交」的引导，`MUST NOT` 展示 0 值指标冒充结果。

#### Scenario: 无样本

- **WHEN** `evaluated=0`
- **THEN** 四张卡显示 `—`，并出现一条「先到风险列表标记提交」的提示

#### Scenario: 校准未改善

- **WHEN** 校准返回 `applied=false`、`reason="no_improvement"`
- **THEN** 页面提示「当前阈值已是最优」，`MUST NOT` 显示「已校准」成功文案

### Requirement: 特征名称可读

提交详情的 14 项特征 SHALL 显示中文名（`utils/features.js::FEATURE_LABELS`，逐字对齐后端 `app/explain.py`），悬停可看原始字段名；解释因子条 SHALL 优先使用后端返回的 `label`。

#### Scenario: 特征明细区

- **WHEN** 打开有特征的提交详情
- **THEN** 特征以中文名展示（如「代码改动量大」），悬停显示 `la`；`MUST NOT` 只显示 `la`、`nf` 这类缩写
