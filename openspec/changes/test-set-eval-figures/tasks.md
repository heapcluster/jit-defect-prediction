# test-set-eval-figures — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/model-figure/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-11-01
> 关联需求：测试集评估图集；现行页面见 `docs/web_page/model_performance.md`
> 状态：实现已交付，待按现行五表设计复核并归档

## 1. 规格与文档

- [x] 1.1 `figure_type` 增加 `effort`；同步 `docs/database/model_figure.md`、`docs/api/figures.md`、`docs/web_page/model_performance.md` — 口径变更
- [x] 1.2 新增本 change 的 `specs/model-figure/spec.md`

## 2. 数据侧实现

- [x] 2.1 新增 `data_model/evaluation/`（config / predict_testset / figures / export_sql / run_all）
- [x] 2.2 25 个模型对测试集预测（expert/semantic/fused 用 pkl；e2e 复用 `pipelines/e2e/data/prediction_result.csv`）
- [x] 2.3 按模型出图：roc / pr / confusion / calibration / effort，expert 另加 feat_importance
- [ ] 2.4 核对 `data_model/evaluation/out/schema.sql` 与当前 `infra/schema.sql` 的五表结构；历史导出的 7 表版本不得作为现行建库脚本使用。`data_init.sql` 仅作测试数据，不入版本库。

## 3. 数据库与 ORM 同步

- [x] 3.1 `backend/app/models.py` 新增 `model.line`、`commit_feature.is_test`、`ModelFigure`
- [x] 3.2 `infra/schema.sql` 由 `Base.metadata` 重新编译生成
- [x] 3.3 `backend/tests/test_schema_sql.py` 表集合纳入 `model_figure`，静态测试通过

## 测试与验证

### 1. 单元测试

- 覆盖：后端 schema 静态比对；从 `backend/` 运行 `python -m pytest tests/test_schema_sql.py`。历史记录为 25 passed；当前提交须重跑，结果与运行日志待补。

### 2. 集成测试

- 覆盖：测试集预测、图生成与 SQL 导出；从 `data_model/` 运行 `python -m evaluation.run_all`。历史记录为 25 模型、629,575 条预测、133 张图；模型权重与数据不入库，须在有交付包的环境重跑。

### 3. 验收测试

- 依据：`specs/model-figure/spec.md` 的 Scenario、`docs/api/figures.md` 与 `docs/web_page/model_performance.md`；按实际模型逐项核对图类型及页面展示，截图和操作者结论待补。

### 4. 非功能验证

- 当前 change 未声明新的性能靶子；图文件加载时间和缺图时的页面行为待实测，不能以生成脚本成功代替。

### 5. 已知缺口与后续计划

- 当前 `infra/schema.sql` 为五表，历史 `out/schema.sql` 的 7 表口径需由模型线核对并重导；MySQL 实机执行 schema 和测试数据导入未验证。责任：模型线与后端线；完成条件：五表一致性检查、真实库导入记录及图集页面截图。
