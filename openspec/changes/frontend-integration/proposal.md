# 前端三页面与联调（frontend-integration）

> Sprint 1 交付 ｜ 起草 2026-10-11 ｜ 起草人 蒋励（代）｜ 关联 docs/implementation/frontend-design.md、docs/pages.md
>
> ⚠️ 契约基线判定沿用首 change：以各契约文件头的「版本 + 冻结日期」为准，不引用 PR 编号或合并时机。

## Why
Sprint 1 验收要求可视化前端（风险列表 / 提交详情 / 趋势看板）三页面 + 前后端联调。前端线目前仅有脚手架 README（F1，PR #33 已合），三页面（F3）与联调（F4）尚未开始；需立项使看板「规格变更或任务」列可点回，并让刘帅华有可执行的实现依据（见 `docs/implementation/frontend-design.md`）。

## What Changes
1. 新增三页面：风险列表（`GET /api/commits`）、提交详情（`GET /api/commits/{hash}`）、趋势看板（`GET /api/trends`）；字段逐字照 `docs/pages.md`。
2. 集中接口封装（`src/api/`，axios + `X-API-Key` 构建期注入），统一三态（加载 / 空 / 错）。
3. 前后端联调 API-01~04，留联调记录。

## Capabilities
- `frontend-pages`：三页面 + 统一接口层 + 三态处理。

## 影响与边界
| 项 | 内容 |
|---|---|
| 影响目录 | `frontend/src/{views,api,components}` |
| 不做什么 | 不新增第四页面；不改契约字段名 / 接口路径；不直连数据库、不自己算指标 |
| 数据边界 | 所有数据来自接口；高风险阈值只在 `docs/pages.md` §5 定义一处（前端不重算） |
