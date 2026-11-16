## Why

本提案提出时，`docs/database/model_figure.md`、`docs/web_page/model_performance.md`、`docs/api/figures.md` 已定义测试集评估看板，但数据侧尚无逐模型图集，也缺少 effort-aware 曲线。本 change 补齐生成与导出流程；实际交付仍以当前测试结果为准。

## What Changes

- `figure_type` 枚举新增 `effort`（Effort-aware 曲线，含 Popt / Recall@20%）。
- 新增 `data_model/evaluation/`：25 个模型（expert 8 + semantic 8 + fused 8 + e2e 1）对测试集的预测、按模型出图、导出 SQL。
- `infra/schema.sql` 与 `backend/app/models.py` 同步新增 `model.line`、`commit_feature.is_test`、`model_figure` 表。
- 导出测试环境的 `schema.sql` 与 `data_init.sql`，分别保存。`schema.sql` 必须与现行五表 `infra/schema.sql` 一致；早期七表导出仅作历史记录，不能用于当前建库。
- 不做：不改预测接口的判定阈值语义、不改模型训练、不改前端。

## Capabilities

### New Capabilities

- `model-figure`：为逐模型评估图建立能力规格，包含 `effort` 图和缺图时的降级行为。

### Modified Capabilities

无。本仓库目前没有 `openspec/specs/model-figure/spec.md`；归档时应按新增能力创建活规格。

## Impact

- 文件：`data_model/evaluation/`、`infra/schema.sql`、`backend/app/models.py`、`backend/app/db.py`、`backend/tests/test_schema_sql.py`、`docs/database/model_figure.md`、`docs/api/figures.md`、`docs/web_page/model_performance.md`。
- 规格：`openspec/changes/test-set-eval-figures/specs/model-figure/spec.md`；完成验收后归档，并创建 `openspec/specs/model-figure/spec.md`。
- 不新增依赖：预测/出图复用现有 sklearn / matplotlib / joblib；e2e 复用仓库内 `prediction_result.csv`，不重跑 CodeBERT。
- 数据体积：`data_init.sql` 约 87 MB（25 模型 × 25,183 条测试集预测），放 `data_model/evaluation/out/`（`.gitignore`），只把生成脚本入库。
