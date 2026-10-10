# 前端三页面实现与联调

> Sprint 1 ｜ 对应飞书《工作周报》任务 F2/F3/F4（建 change 提案 + 三页面实现 + 前后端联调）
> 起稿 2026-10-09 ｜ 起稿人 刘帅华 ｜ 关联契约：`docs/pages.md`、`docs/contracts/api-format.md`

## Why

脚手架已合入 `main`（PR #33），但三个页面仍是 `el-empty` 骨架占位。课程 Sprint 1 要求「MVP 至少一条从界面到数据层的完整流程」——前端线需要真正实现三页面并对接后端接口，链路才从「数据 → 模型 → 接口 → 页面」全部打通。

## What Changes

- **风险列表页**：按 `risk_score` 降序、筛选（`model_name` / `min_risk` / 时间范围）、分页、点击行跳详情
- **提交详情页**：风险值 + 风险等级标签 + 14 项特征（五维分组）+ `explanation` 解释条
- **趋势看板页**：粒度切换、折线图（ECharts）、汇总卡片、明细表
- **三态处理**：加载中 / 空数据 / 请求失败，按 `docs/pages.md` 第 5 节错误码区分
- **接口对接**：API-01 `GET /api/commits`、API-02 `GET /api/commits/{hash}`、API-03 `GET /api/trends`

**不做什么（显式列出）**

- **不做** 第四个页面（模型管理、用户设置等）——课程未要求
- **不直连数据库、不自己算指标**——风险概率与聚合结果一律来自接口
- **不改** `docs/contracts/` 字段名——字段不够用先提契约变更
- **不另立** 风险阈值——`risk_score ≥ 0.5` 只按 `docs/pages.md` 第 5 节一处定义

## Capabilities

### New Capabilities

- `risk-list`：按风险排序的提交列表，支持筛选与分页，点击跳详情
- `commit-detail`：展示单次提交的风险值、14 项特征与模型解释
- `trend-board`：按周/月聚合的风险趋势折线图与明细

### Modified Capabilities

无 —— 本 change 之前 `openspec/specs/` 无前端相关能力。

## Impact

| 项 | 内容 |
|---|---|
| 影响目录 | `frontend/src/`（views / api / components / router） |
| 消费契约 | `docs/pages.md`（字段映射）、`docs/contracts/api-format.md`（接口格式）——只读不改 |
| 新增依赖 | ECharts 已列 `frontend/package.json`，无新增 |
| 下游依赖 | 后端 #52（API-01/02/03 落地）——否则联调无接口可调 |
