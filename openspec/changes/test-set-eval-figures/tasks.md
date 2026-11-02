# test-set-eval-figures — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/model-figure/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-11-01

## 1. 规格与文档

- [x] 1.1 `figure_type` 增加 `effort`；同步 `docs/database/model_figure.md`、`docs/api/figures.md`、`docs/web_page/eval.md` — 口径变更
- [x] 1.2 新增本 change 的 `specs/model-figure/spec.md`

## 2. 数据侧实现

- [x] 2.1 新增 `data_model/evaluation/`（config / predict_testset / figures / export_sql / run_all）
- [x] 2.2 25 个模型对测试集预测（expert/semantic/fused 用 pkl；e2e 复用 `pipelines/e2e/data/prediction_result.csv`）
- [x] 2.3 按模型出图：roc / pr / confusion / calibration / effort，expert 另加 feat_importance
- [x] 2.4 导出 `schema.sql`（7 表）与 `data_init.sql`（测试集初始化数据），两文件分开

## 3. 数据库与 ORM 同步

- [x] 3.1 `backend/app/models.py` 新增 `model.line`、`commit_feature.is_test`、`ModelFigure`
- [x] 3.2 `infra/schema.sql` 由 `Base.metadata` 重新编译生成
- [x] 3.3 `backend/tests/test_schema_sql.py` 表集合纳入 `model_figure`，静态测试通过

## 测试与验证（强制板块）

| 项 | 内容 |
|---|---|
| 覆盖对象 | schema 静态比对、25 模型预测、按模型出图、SQL 数据完整性 |
| 复现命令（data_model） | `python -m evaluation.run_all` |
| 复现命令（backend） | `python -m pytest tests/test_schema_sql.py` |
| 结果 | schema 静态测试 25 passed；25 模型 / 629,575 条预测 / 133 张图 |
| 数据覆盖 | npz / e2e 预测 / 文本 / raw 特征均 0 条缺测试集 |
| 未覆盖 | MySQL 实机执行 `schema.sql` + `data_init.sql` 待补（本机 MySQL 未启动） |
