# 反馈闭环与可观测性

## Why

当前系统是一条「单向」链路：抽取提交 → 现算特征 → 预测 → 前端展示。它缺了工业级 JIT 系统最重要的两环：

1. **没有真值回流（feedback loop）**。工业级 JIT（Microsoft 的提交级风险排序、Google 的缺陷预测）都把「预测 → 事后确认 → 标签回流 → 再训练」当作核心闭环：预测结果必须能被人工确认或纠正，「这条提交到底有没有引入缺陷」回流成标签，才能支撑再训练、阈值校准与效果评估。本仓库已有 `commit_label` 表，但**只有 SZZ 自动打标、没有任何写入接口**，人工确认无处落地；`labeled-dataset` capability 也只覆盖 SZZ 自动打标，不含人工反馈。
2. **没有运行状态可见性（observability）**。工业级系统必有健康检查端点（容器编排的 readiness / liveness 依赖它），运维需要知道「DB 通不通、模型加载了几个、已预测多少条、最后一次同步什么时候」。当前只有业务接口，没有任何可观测端点，出问题只能翻日志。

同时，解释（SHAP）目前只以 `feature` / `contribution` / `direction` 三元组返回，**因子名是 `la`、`ndev` 这类缩写**，评审者看不懂；工业级可解释性强调「因子名可读 + 正负贡献可视化」。

本 change 补齐这三处：人工反馈闭环、健康检查端点、解释因子可读化，并把它们接进前端。仍严格遵守三条契约（错误码只用 5 个、响应包络统一、字段名不改）。

## What Changes

- **人工反馈闭环（新增 `feedback` capability）**：
  - `PUT /api/commits/{commit_hash}/label`：写入/更新/撤销该提交的人工标签，落 `commit_label` 表且 `label_method="manual"`；`is_defect` 为三态 —— `true` 引入缺陷、`false` 确认非缺陷（保留标签行，计入质量指标的 `tn`/`fp`）、`null` 撤销（删除该 commit 的 manual 标签行）。`MUST NOT` 用 `false` 顶替撤销，否则「已撤销」会被当成「已确认非缺陷」留在库里并污染指标。`commit_hash` 不存在 SHALL 返回 40400；请求体非法（缺字段，或值非布尔/非 `null`）SHALL 返回 40001。
  - `GET /api/commits/{commit_hash}` 详情响应附带 `label`（`is_defect` / `labeled_at`），未标记时为 `null`。
  - `GET /api/commits` 支持 `has_label=true` 过滤（仅返回已人工确认的提交），用于「已确认」视图。
- **健康检查与运行状态（新增 `observability` capability）**：
  - `GET /api/health`：返回 `status`（`ok` / `degraded`）、`db`（`up` / `down`）、`models_loaded`（数量）与 `model_names`（名称列表）、`commit_count` / `prediction_count` / `labeled_count`、`last_sync_at`（来自同步状态快照）、`server_time`（当前 UTC，ISO 8601 带 Z）。
  - 响应 `MUST NOT` 回显连接串、口令、堆栈或文件路径（沿用契约三对 50000 的要求）。
- **解释因子可读化（修改 `query-api`）**：`ExplanationItem` 增加 `label` 字段（14 项特征的中文名）；`predict`、commit 详情、PR 理由 SHALL 共用同一份字典（`MUST NOT` 各处各维护一份）。前端 commit 详情 SHALL 以**横向条形图**呈现正负贡献（正 / 负分色、按绝对值降序），替代纯列表。
- **前端改造**：`CommitDetail.vue` 加「标记为引入缺陷 / 撤销标记」操作与 SHAP 条形图；`RiskList.vue` 加「仅看已确认」筛选与顶部健康状态条（模型数 / 已预测数 / DB 状态）。

## Capabilities

### Added Capabilities

- `feedback`：提交缺陷标签的人工确认（写入 / 读取 / 撤销）与按标签过滤，形成「预测 → 确认 → 回流」的最小闭环。
- `observability`：健康检查与运行状态可见（`GET /api/health`）。

### Modified Capabilities

- `query-api`：解释项增加中文因子名；commit 详情附带人工标签状态；列表支持 `has_label` 过滤。

## Impact

- 后端：新增 `app/api/feedback.py`（label 端点）与 `app/api/health.py`（健康端点）；新增 `app/explain.py` 集中 14 项特征中文名，供 `predict.py` / `commits.py` / `prs.py` 共用（消除 `prs.py` 内重复字典）；`schemas.py` 增加 `LabelData` / `HealthData`，`ExplanationItem` 增加 `label`；`commits.py` 列表加 `has_label` 过滤、详情附带 `label`；`main.py` 注册两个新路由。
- 前端：`api/index.js` 新增 `putCommitLabel` / `getHealth`；`CommitDetail.vue` 标记操作 + SHAP 条形图；`RiskList.vue` 健康状态条 + 「仅看已确认」筛选。
- 数据库：复用既有 `commit_label` 表（`label_method="manual"`，与 SZZ 标签靠唯一约束 `(commit_hash, label_method)` 隔离），**无需迁移、不改表结构**。
- 契约：`docs/backend/api-spec.md` 需登记 `PUT /api/commits/{commit_hash}/label` 与 `GET /api/health`（本 change 内同步）。
- 测试：`tests/test_mirror.py` 的路径集与详情字段集需同步（新增两条路径、详情加 `label`）；新增 `test_feedback_api.py` / `test_health_api.py`。

## 不做什么

- `MUST NOT` 新增错误码：只用 0 / 40001 / 40100 / 40400 / 50000。
- `MUST NOT` 改动 `commit_label` 表结构或 SZZ 自动打标逻辑；人工标签以 `label_method="manual"` 与自动标签共存。
- **不做备注（note）字段**：`commit_label` 表不新增列，本 change 只记录 `is_defect` 与标记时间，避免迁移与 `infra/schema.sql` 漂移（后置）。
- **不做再训练流水线**：本 change 只把标签「存下来」，不触发自动重训（需额外调度与数据规模，后置）。
- **不做 webhook 事件驱动同步**（后置，见上一 change 的「不做什么」）。
- **不做多仓库**（`SOURCE_REPO` / `GITHUB_REPO` 仍为单值）。
- 不引入任何外部监控组件（Prometheus / Grafana），`/api/health` 只返回进程内可算的指标。
- 不追求模型预测效果（本 change 与模型准确率无关）。
