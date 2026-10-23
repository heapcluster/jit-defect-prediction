# frontend-integration — 设计要点

## Context

脚手架已合入 `main`（PR #33），但三个页面仍是 `el-empty` 骨架。前端线需要在 Sprint 1 实现风险列表 / 提交详情 / 趋势看板三页面并对接后端接口，打通「界面到数据层」的完整流程。字段口径以 `docs/frontend/pages.md`（v1.4 已裁定）为唯一依据。

## Goals / Non-Goals

**Goals**

- 三页面实现：风险列表（排序/筛选/分页/跳详情）、提交详情（风险值/SHAP 解释/特征分组）、趋势看板（折线/汇总/明细）。
- 统一接口层（`src/api/`）：axios + `X-API-Key` 构建期注入 + 响应包络统一解包。
- 三态齐全：加载中 / 空数据 / 请求失败，错误码按 `docs/frontend/pages.md` §5 区分。
- 前后端联调 API-01/02/03，留联调记录。

**Non-Goals**

- 不做第四个页面（模型管理、用户设置等）。
- 不改契约字段名、接口路径；字段不够用先提契约变更。
- 不直连数据库、不自己算指标；风险概率与聚合结果一律来自接口。
- 不另立风险阈值；`risk_score ≥ 0.5` 只按 `docs/frontend/pages.md` §5 一处定义。

## Decisions

- **技术栈**：Vue 3 + Vite + Vue Router + Element Plus + ECharts + axios；`/api` 走本地代理到 `:8000`。
- **鉴权**：`X-API-Key` 由构建期环境变量 `VITE_API_KEY` 注入，不硬编码；`.env.example` 入库、真实值走 `.env.local`。
- **时间范围闭区间**：`end_time` 送纯日期串 `YYYY-MM-DD`，服务端含结束日全天；前端不自行拼接 `T23:59:59`（对齐契约三 1.5 口径）。
- **趋势下钻粒度**：点击数据点用「已加载数据的粒度」（`loadedGranularity`，load 时保存），不用尚未查询的筛选器粒度。
- **风险列表响应 query**：`watch(route.query)`，query 变化重新查、query 移除清日期并重置分页。
- **三态实现**：加载中骨架屏（容器高度不变）；空数据非错误（文案 + 清空/重置操作）；错误码按 §5 分发，`40001` 指出参数（取 `err.detail`）、`40100` 不重试、`40400`/`50000` 不显服务端 message 原文。
- **模型清单**：前端维护 `['xgb_v1', 'rf_v1', 'lr_v1']`（契约三冻结结论）。

## Risks / Trade-offs

- **依赖 #62**：前端送纯日期依赖 #62（后端 recognize 纯日期串含全天）先合入；#62 未合时旧后端按 `00:00:00` 解析会丢最后一天。已按「#62 先合、#60 后合」排期。
- **模型清单硬编码**：前端只列 3 个模型，而 `python -m pipelines.expert.train` 的训练口径有 8 个。选到无预测行的模型会落空态，用户分不清「模型没跑」还是「时间段没数据」。暂记待办，后续接口化。
- **产物体积**：echarts + element-plus 未分包，单 chunk 约 2.2MB，build 有 chunk 警告。课程项目可接受，记待办。

## Migration Plan

无迁移。全新三页面 + 接口层，无存量数据/旧接口需迁移。

## Open Questions

- 模型下拉是否改为接口提供（`GET /api/models`），待后端支持后前端接入。
- 产物分包（echarts/element-plus 按需引入）是否在 Sprint 1 后优化。
- `toEndTime` 兜底已在 #62 口径下移除，确认无遗漏（#62 合入后复核）。
