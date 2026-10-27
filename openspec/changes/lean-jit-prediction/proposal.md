# 预测服务瘦身：冠军模型单跑 + 只要最新，不做历史回填

## Why

两件事让「预测」比它该有的样子重：

1. **一条提交写 8 行**：`predict_commit_all_models()` 对注册表里每个模型都打一次分并落库。演示库 83,943 条提交 → 约 67 万行 `prediction`。8 个模型是课程验收（≥2 类、不少于 8 种）与离线横评的产物，**不该成为运行时默认**：真实 JIT 场景里，评审只需要「这次改动有多大概率引入缺陷」一个数。
2. **同一件事三条入口**：启动基线（`run_startup_sync`）、手动 `POST /api/sync`、webhook（`opened/synchronize/reopened`）都走「全模型」这条最重的路径。标准 JIT 的主链路只有一条——代码事件进来，对**这一次**改动打分。

## 立场：库里的数据只应该是最新的

**不做种子数据、不做离线导入、不做历史回填。** 库内内容由实时同步决定：谁被预测，取决于「最近 N 条提交」这一件事（`limit` 由调用方给，硬上限 50）。

理由：种子/回填的数据一进库就开始贬值——特征口径一升级（`v1`→`v2`）、模型一换版本，历史行的 `risk_score` 就与线上现算对不上，却仍以「库里的事实」被展示和统计。与其维护一份会过期的快照，不如让库只回答「现在」。

代价（接受，并写进规格）：新库第一次启动只有最新 N 条，趋势看板数据点可能不足 2 个、质量看板 0 样本。这是**数据的真实状态**，用空态引导说清楚，而不是拿种子填满。

## What Changes

- **服务模型收敛**：新增 `runtime_setting.champion_model`；预测默认只对冠军模型打分并落库（1 行/提交）。其余已交付模型保留「按需单跑」（`POST /api/predict` 指定 `model_name`）。
- **显式 `all_models` 开关**：`POST /api/sync`、`/api/sync/catchup`、`/api/sync-prs` 增加 `all_models=false`（默认），演示八模型对比时显式置 `true`，行为与改动前一致。
- **入口分层**：
  - 实时（webhook / PR 事件）→ 只处理最新 `WEBHOOK_SYNC_LIMIT` 条与该 PR 内提交；
  - 显式拉取（`POST /api/sync?limit=N`）→ 只处理最新 N 条，N ≤ 50；
  - 启动（`SYNC_ON_STARTUP=1`）→ 只补 `SYNC_INITIAL_LIMIT` 条（默认 10），`MUST NOT` 追平历史。
- **删除现存种子链路**（已随本 change 执行）：删除 `backend/scripts/seed_dev_data.py`，`infra/setup_mysql.py` 移除 `--seed` 与 `run_seed()`，同步更新 `docs/backend/acceptance.md`、`docs/frontend/integration-log.md` §0、`docs/owners/s1mple-less.md`、`data_model/pipelines/expert/README.md` 里「造 3 行种子」的说法。
- **阈值按预算（phase 2）**：质量看板增加「按评审预算」视图（Recall@20% / @50% 随阈值变化）。

## Capabilities

### Added Capabilities

- `predict-api`：服务模型唯一（冠军）、批量模型范围、入口分层、量-不-回填、预算阈值。

### Modified Capabilities

- 无。本 change 不改 `db-schema`：`实时同步入库` 那条「运行时只此入口」的既有口径已经包含了本 change 要的结论，不再重复表述。

## Impact

- 后端：`app/model_registry.py`（冠军选择）、`app/api/{predict,sync,prs}.py`、`app/services/settings.py`（新增 champion 键）、`app/schemas.py`（响应补 `models` 字段）。
- 前端：无破坏性改动；模型下拉仍可用，非冠军模型需单条重算才会出数。
- 数据：`prediction` 从 8 行/提交降为 1 行/提交；**已有历史行不回删**（避免删数据带来的不可逆风险），新提交按新口径写。
- 文档：`README.md` / `docs/common/local-runbook.md` 里的「第一次启动」只说清「先拉最新 N 条」，不提供任何灌库捷径。

## 不做什么

- **不做种子数据、不做离线 CSV 导入、不做历史回填**——包括不新增 `infra/seed_dev.py` 之类的脚本（`#168` 已删过一次，本 change 不再恢复）。
- 不删任何已交付模型，不重训，不改 `.pkl` 与 `feature_order.txt`。
- 不回删库里已有的多模型 `prediction` 行。
- 不改接口字段与错误码（`risk_score` / `model_name` / `risk_level` 语义不变）。
- 不做多模型同图对比、不做在线语义模型（CodeBERT）接入。
