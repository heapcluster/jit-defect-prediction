## Why

`docs/database/model_figure.md`、`docs/web_page/model_performance.md`、`docs/api/figures.md` 已定义「测试集评估看板」的图索引与明细展示，但数据侧尚未实现：没有 `model_figure` 表数据、没有按模型拆分的图，`figure_type` 枚举也缺少 JIT 缺陷预测最核心的 effort-aware 曲线。本次补齐数据侧交付物。

## What Changes

- `figure_type` 枚举新增 `effort`（Effort-aware 曲线，含 Popt / Recall@20%）。
- 新增 `data_model/evaluation/`：25 个模型（expert 8 + semantic 8 + fused 8 + e2e 1）对测试集的预测、按模型出图、导出 SQL。
- `infra/schema.sql` 与 `backend/app/models.py` 同步新增 `model.line`、`commit_feature.is_test`、`model_figure` 表。
- 产出 `schema.sql`（7 表 DDL）与 `data_init.sql`（测试集初始化数据），两者分开，不合成一个长文件。
- 不做：不改预测接口的判定阈值语义、不改模型训练、不改前端。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `model-figure`：`figure_type` 增加 `effort`，并要求数据线产出与 `model_figure.file_path` 对应的 png。

## Impact

- 文件：`data_model/evaluation/`、`infra/schema.sql`、`backend/app/models.py`、`backend/app/db.py`、`backend/tests/test_schema_sql.py`、`docs/database/model_figure.md`、`docs/api/figures.md`、`docs/web_page/model_performance.md`。
- 规格：`openspec/changes/test-set-eval-figures/specs/model-figure/spec.md`，归档后并入现行 `model-figure`。
- 不新增依赖：预测/出图复用现有 sklearn / matplotlib / joblib；e2e 复用仓库内 `prediction_result.csv`，不重跑 CodeBERT。
- 数据体积：`data_init.sql` 约 87 MB（25 模型 × 25,183 条测试集预测），放 `data_model/evaluation/out/`（`.gitignore`），只把生成脚本入库。
