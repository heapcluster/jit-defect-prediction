# 启动即基线同步与实时可见

## Why

空库首启是体验痛点：当前启动同步默认关闭、无进度可见、前端靠手动按钮触发，且 PR 主视图直接展示原始概率，审 PR 的人看不懂；同时 commit 主链路只落默认模型一行、与 PR 链路落全部模型不对称，导致"切换模型"在 commit 视图残疾。

工业 JIT / 代码评审工具（SonarQube、Amazon CodeGuru、Codacy）处理"空库"的做法是：**模型预置、首次接入做基线扫描（慢但只一次、状态可见）、绝不造假数据、之后增量**。它们从不为空库预填，而是把"空"解释成"分析中"。其分析单位是"自锚点以来的增量/保持最新"，**绝不**让用户挑选任意历史日期段去按需预测——预测触发要么是接入基线、要么是 push 增量，日期只用于"看已分析的结果"。

本 change 把这套工业做法轻量化落地，并顺带修复模型落库不对称与数据库规范化缺口：启动即后台建立基线、用 SSE 实时推送进度、PR 主视图用风险徽章 + 一句话理由替代裸概率、同步统一落全部模型、数据库最小 BCNF 化。仍严格遵守"不提前灌库、数据全部现算"的裁定。

## What Changes

- **首启分级基线 / 日常增量（语义区分）**：`config.SYNC_ON_STARTUP` 默认开启。**首启**（空库、`prediction` 为空）取 `SYNC_INITIAL_LIMIT`（默认 10，可配）条最新 commit 建立基线，避免 84k 全量；**日常增量**（库非空）SHALL 补齐从 DB 最新到 git HEAD 之间所有「git 有而 DB 无 prediction」的 commit，**不设小限额、直接追到最新**，仅受 `SYNC_CATCHUP_LIMIT`（默认 500，安全上限）约束防失控。全程后台线程、不阻塞启动。
- **同步统一落全部注册模型**：`sync`（commit 主链路）与 `sync-prs`（PR）统一调用 `predict_commit_all_models`，对每条 commit 落全部注册模型的 `prediction` 行，消除"commit 视图仅默认模型有数、切模型为空"的不对称；前端按 `model_name` 取对应行，缺失则引导至「补齐到最新」补预测（幂等）。
- **同步控制面（新增 `sync-api` capability）**：
  - `GET /api/sync/status`：返回当前同步状态快照（running / mode / scope / total / done / current_hash / started_at / last_error）。
  - `GET /api/sync/stream`：SSE（`text/event-stream`），`_sync_state` 变化时推送进度，替代前端轮询。
  - `POST /api/sync/catchup`：补齐到最新——扫描 git HEAD 与 DB 之间所有「git 有而 DB 无 prediction」的 commit 并预测（无日期参数，MUST NOT 让用户指定历史区间）。
- **日期仅用于查看过滤（不触发预测）+ 覆盖可视化**：前端日期范围 **MUST 只作为查询已预测结果的过滤器**（按 `commit.committed_at` 看某段风险分布），**MUST NOT 让用户选日期触发新预测**；前端显示"已预测时间覆盖"区间，让用户知晓缺口并通过「补齐到最新」按钮由系统补齐。
- **PR 风险转译呈现（扩展 `query-api`）**：`GET /api/prs` 返回每个 PR 的**风险等级（高/中/低，阈值可配）+ 一句话理由摘要**（基于 top 特征 / SHAP 因子模板生成，不依赖 LLM）；前端 PR 主视图以风险徽章呈现。
- **前端改造**：`PrList` 主视图加风险徽章 + 理由卡；`RiskList` 与 `PrList` 改用 `EventSource` 接收 SSE 进度；`RiskList` 的日期范围仅作**查看过滤**（不触发预测）、加「已预测覆盖」展示与「补齐到最新」按钮、新入库自动出现。
- **数据库最小 BCNF 化（扩展 `db-schema`）**：新增 `model` 表（`model_name` PK、`version_key`、`trained_at`、`algo`、`feature_version`）承载模型元数据；`prediction.model_name` 改 FK；四表间加 `commit_hash` 外键；各表加 `updated_at` 审计列。不拆分 `author` 表（commit 仅存 author 字符串，无传递依赖）。

## Capabilities

### Added Capabilities

- `sync-api`：启动自动同步（首启分级）、同步状态查询、同步进度 SSE 推送、补齐到最新（catchup）。

### Modified Capabilities

- `db-schema`：空库首启场景扩展为"首启分级基线"；新增模型元数据表、四表外键与审计列。
- `query-api`：新增 PR 风险转译呈现（等级 + 理由摘要）；新增模型切换、查看过滤与已预测覆盖。

## Impact

- 后端：`config.py` 新增 `SYNC_ON_STARTUP` / `SYNC_INITIAL_LIMIT` / `SYNC_CATCHUP_LIMIT`；`app/main.py` 默认开启启动同步；`app/api/sync.py` 统一落全部模型 + 新增 status / stream / catchup 端点与 `_sync_state`；`app/api/prs.py` 增加等级映射与理由摘要；`app/api/commits.py` 列表查询支持 `since`/`until` 仅作查看过滤。
- 前端：`PrList.vue` 风险徽章 + 理由卡；`RiskList.vue` 日期仅查看过滤 + 覆盖显示 + 「补齐到最新」按钮 + SSE；`api/index.js` 新增 `getSyncStatus` / `subscribeSyncProgress` / `postSyncCatchup` / `getCommitsByDate`。
- 数据库：新增 `model` 表 + 四表 `commit_hash` 外键 + 各表 `updated_at`，需迁移脚本（ALTER / Alembic），数据量小、秒级完成；14 项数值口径、幂等键不变；仍不预填任何数据。

## 不做什么

- `MUST NOT` 提前灌库：首启仍是现算特征 + 预测 + 落库，只是范围分级。
- `MUST NOT` 拆分 `author` 表：commit 仅存 author 字符串，无传递依赖，BCNF 已满足。
- `MUST NOT` 提供「前端选历史日期区间触发预测」的能力：预测触发只有启动自动 / 重启追到 HEAD / 手动「补齐到最新」，日期筛选仅用于查看已预测结果。
- **webhook 触发**后置为后续增强（本地需外网隧道才能验证，不阻塞核心链路）。
- **特征历史索引缓存**（消 15s/条）后置为 P1（首启先靠范围分级缓解）。
- **成本敏感排序 / cost-effectiveness 曲线**不做（属模型效果，本轮不追求）。
- 不引入 LLM 生成理由，仅用模板化因子拼接。
