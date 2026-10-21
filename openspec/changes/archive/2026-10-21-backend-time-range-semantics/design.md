# Design: backend-time-range-semantics

## Context

契约三冻结时只写了「ISO 8601 时间范围」，闭/开与纯日期串解释未定义；前端 date-picker 送纯日期串、后端按 00:00 解析、查询闭区间，三处相乘产生 #61。#55 重组后契约三位于 `docs/backend/api-spec.md`（**本 change 之前为 v1.4**；本 change 按 `docs/common/writing-norms.md` §4 的口径补充 0.1 步进升为 **v1.5**，见 tasks 2.1）。

## Goals / Non-Goals

- Goals：区间语义入契约且可判定；结束日含全天；同一日期只允许一种写法；列表/趋势同口径。
- Non-Goals：不改前端代码（#60 内跟进）；不动排序/阈值（#37/#38，PO 裁定 Sprint 2）；不为 Issue #65 登记的其余失效 `docs/contracts/` 引用买单（10-11 12:41 裁定分工，后端线只负责 `backend/README.md`）。

## Decisions

- **D1 服务端收尾**（修法 b）：end 纯日期串 → `23:59:59.999999`。备选 a（前端收尾）被否：调用侧补丁会各写一套，且契约 MUST NOT 明禁；备选 c（半开区间 [start, end+1d)）被否：要改查询算子与既有测试口径，收益不抵改动面。
- **D2 紧凑基本格式拒收**而非视作纯日期：`fromisoformat` 接受 `20260803` 与带 Z/偏移变体，若视作纯日期则同一时刻两种写法、且绕过格式校验；拒收（40001）保证「同一日期只允许一种写法」（#62 复审 1+3）。
- **D3 start 不随 end 规则变**：start 纯日期串 = 当天 00:00:00 是闭区间下界的天然后备，一刀切收尾会吞掉 start 当天（评审点名）。
- **D4 版本 1.5（0.1 步进）**：writing-norms 现行 §4「小改/加章节/改口径 → 0.1」；我初稿引的旧「1.0 步进」字面已被 #54 废除（复审裁定）。
- **D5 主规格不直改**：`openspec/specs/query-api` 的同步留在归档 PR 随 delta 落入，避免两套规格来源并行（复审 2）。

## Risks / Trade-offs

- 月粒度 end「次月 1 日」送法在新语义下多收一天 → 前端 #60 已改当月最后一日；若漏改，趋势月粒度多一日数据（可观测、可回退）。
- 拒收紧凑格式对历史调用方是 breaking（此前静默 00:00）→ 本系统唯一调用方为组内前端，且其送法为扩展格式，风险为零。

## Migration Plan

- 合入顺序 #62 → #60（rebase 移除 toEndTime 兜底与 pages.md 过渡句）。
- 无数据迁移；无配置变更。

## Open Questions

- 无（区间语义已定；#37/#38 属另案）。
