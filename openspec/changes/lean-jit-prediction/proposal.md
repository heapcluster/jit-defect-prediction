# 预测服务范围收敛：只同步最新提交，不做历史回填

## Why

两件事让「预测」比它该有的样子重：

1. **全量历史同步成本高**：`predict_commit_all_models()` 对每个已加载模型打分并落库。演示库 83,943 条提交若全部同步，8 模型约产生 67 万行 `prediction`。现行裁定保留每条提交的全模型结果，通过限制同步到最新 N 条控制总量。
2. **同一件事三条入口**：启动基线（`run_startup_sync`）、手动 `POST /api/sync`、webhook（`opened/synchronize/reopened`）都须遵守最新提交数量上限。代码事件进来，对本次范围内的改动逐模型打分。

## 立场：库里的数据只应该是最新的

**不做种子数据、不做离线导入、不做历史回填。** 库内内容由实时同步决定：谁被预测，取决于「最近 N 条提交」这一件事（`limit` 由调用方给，硬上限 50）。

理由：种子/回填的数据一进库就开始贬值——特征口径一升级（`v1`→`v2`）、模型一换版本，历史行的 `risk_score` 就与线上现算对不上，却仍以「库里的事实」被展示和统计。与其维护一份会过期的快照，不如让库只回答「现在」。

代价（接受，并写进规格）：新库第一次启动只有最新 N 条，趋势看板数据点可能不足 2 个、质量看板 0 样本。这是**数据的真实状态**，用空态引导说清楚，而不是拿种子填满。

## What Changes

- **统一缺省模型**：新增 `runtime_setting.champion_model`；所有读写入口共用有效默认模型解析规则。冠军有预测行时用冠军，否则回退到有行的最高版本已加载模型；空库选冠军。具体判据由 `default-model-resolution` 变更维护。
- **同步范围**：`POST /api/sync`、`/api/sync/catchup`、`/api/sync-prs` 默认对全部已加载模型落预测行；`all_models` 不作为启用全模型的前置条件。
- **入口分层**：
  - 实时（webhook / PR 事件）→ 只处理最新 `WEBHOOK_SYNC_LIMIT` 条与该 PR 内提交；
  - 显式拉取（`POST /api/sync?limit=N`）→ 只处理最新 N 条，N ≤ 50；
  - 启动（`SYNC_ON_STARTUP=1`）→ 只补 `SYNC_INITIAL_LIMIT` 条（默认 10），`MUST NOT` 追平历史。
- **删除现存种子链路**（已随本 change 执行）：删除 `backend/scripts/seed_dev_data.py`，`infra/setup_mysql.py` 移除 `--seed` 与 `run_seed()`，同步更新 `docs/backend/acceptance.md`、`docs/frontend/integration-log.md` §0、`docs/owners/s1mple-less.md`、`data_model/pipelines/expert/README.md` 里「造 3 行种子」的说法。
- **阈值按预算（phase 2）**：质量看板增加「按评审预算」视图（Recall@20% / @50% 随阈值变化）。

## Capabilities

### Added Capabilities

- `predict-api`：共享缺省模型解析、批量模型范围、入口分层、限制历史回填、预算阈值。

### Modified Capabilities

- 无。本 change 不改 `db-schema`：`实时同步入库` 那条「运行时只此入口」的既有口径已经包含了本 change 要的结论，不再重复表述。

## Impact

- 后端：`app/model_registry.py`（冠军选择）、`app/api/{predict,sync,prs}.py`、`app/services/settings.py`（新增 champion 键）、`app/schemas.py`（响应补 `models` 字段）。
- 前端：无破坏性改动；模型下拉仍可用，展示各模型已同步预测结果。
- 数据：新同步提交对全部已加载模型落库；以最新 N 条的范围上限控制数据量。**已有历史行不回删**。
- 文档：`README.md` / `docs/common/local-runbook.md` 里的「第一次启动」只说清「先拉最新 N 条」，不提供任何灌库捷径。

## 不做什么

- **不做种子数据、不做离线 CSV 导入、不做历史回填**——包括不新增 `infra/seed_dev.py` 之类的脚本（`#168` 已删过一次，本 change 不再恢复）。
- 不删任何已交付模型，不重训，不改 `.pkl` 与 `feature_order.txt`。
- 不回删库里已有的多模型 `prediction` 行。
- 不改接口字段与错误码（`risk_score` / `model_name` / `risk_level` 语义不变）。
- 不做多模型同图对比、不做在线语义模型（CodeBERT）接入。
