# Proposal: backend-time-range-semantics

## Why

Issue #61（P1）：风险列表与趋势接口的时间范围筛选**每次丢结束日当天**——前端 `el-date-picker` 送纯日期串 `2026-07-26`，后端 `_parse_time` 解析为当天 `00:00:00`，查询 `committed_at <= end` 闭区间，三者相乘把结束日整天（除整点）排除；趋势周下钻每周丢 1/7、与看板 `commit_count` 对不上，10/23 端到端演示会露。根因是契约三（现 `docs/backend/api-spec.md`）从未定义区间语义（闭/开、纯日期串如何解释），单修代码不补契约，下次还踩。

## What Changes

- `docs/backend/api-spec.md` 升 **1.5**（口径补充，0.1 步进，按 writing-norms 现行 §4；#62 复审裁定旧「1.0 步进」字面已被 #54 废除）：§一 新增「时间范围语义」表行——闭区间 `[start, end]`；纯日期串 start = 当天 `00:00:00.000000`、end = 当天 `23:59:59.999999`（**结束日含全天**）；带时间分量按原样；带时区先转 UTC；**紧凑基本格式（含 Z/偏移后缀变体）MUST 被拒（40001）**；前端 MUST NOT 依赖调用侧补 `T23:59:59`（理由：区间语义由服务端统一解释，避免各调用方各写一套）。文件头与新增变更日志节同步。
- 后端 `_parse_time(value, param, role)`：`role="end"` 且纯日期串 → 当天收尾；紧凑基本格式宽判据拒收（头 8 位数字后接 T 或结束）；`start` 保持午夜（评审明确不能一刀切）。`commits` 与 `trends` 两接口同修。
- 全仓引用点同步 1.4 → 1.5（backend docstring 7 处、`backend/README.md` 路径 4 处——路径修复按 10-11 12:41 归属裁定归后端线）。

## Capabilities

- New: （无）
- Modified: `query-api`（风险列表与趋势聚合两条 requirement 的时间过滤语义：闭区间 + 纯日期串 end 含全天 + 紧凑格式拒收；新增 4 条 scenario）

## Impact

- 后端线（本 change）：解析与查询、测试、契约与引用同步
- 前端线（另线跟进，PR #60）：周下钻送纯日期串在新语义下天然正确；**月粒度** `periodToRange` 的 end 送「次月 1 日」会多收结束日全天 → 改送当月最后一日（帅华 d6c7a95 已改）；其 toEndTime 兜底按 10-12 协调意见在 #62 合入后移除
- 契约消费方：区间语义从「未定义」变为「闭区间 + 结束日含全天 + 紧凑格式拒收」，行为变化仅 end 纯日期串与紧凑格式两类输入
- 不做：不改 `min_risk`/`model_name`/分页语义；不夹带 #37/#38 排序与阈值提案（PO 裁定 Sprint 2）
