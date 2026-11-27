# contract-completion — 任务清单

> 提案：`proposal.md` ｜ 规格：`specs/model-figure/spec.md`、`specs/commit-collection/spec.md`、`specs/predict-api/spec.md`、`specs/query-api/spec.md`、`specs/ui/spec.md`
> 负责人：后端与前端联合 ｜ 创建：2026-11-26
> 关联需求：设计文档落地；页面见 `docs/web_page/collect.md`、`docs/web_page/evaluate.md`、`docs/web_page/storage.md`、`docs/web_page/predict_detail.md`
> 状态：实现已交付，HTTP 实机冒烟待 MySQL 环境

## 1. 规格与文档

- [x] 1.1 新增本 change 的 5 份 spec delta
- [x] 1.2 删除 `docs/api/figures.md`、`docs/api/storage.md`、`docs/api/collect.md`、`docs/api/evaluate.md`、`docs/api/predict.md` 对应“待补”标注
- [x] 1.3 更新 `docs/web_page/predict_detail.md` 的内联定位状态
- [x] 1.4 更新 `docs/web_page/collect.md`、`docs/web_page/evaluate.md`、`docs/web_page/storage.md` 的实现状态

## 2. 后端契约

- [x] 2.1 `figures` 7 类图、只传 `job_id`、`figure_name`、历史 `effort` 归一
- [x] 2.2 `GET /api/predict/preview/{job_id}` 分页预览（prediction 表 + CSV 回退）
- [x] 2.3 storage `create_dataset.source_type` 只接受 `git_repo`
- [x] 2.4 评估配置移除 `threshold/model_names/report_format/format`，阈值沿用预测结果
- [x] 2.5 评估产物改为图集 zip + 指标表，逐图登记 `model_figure`
- [x] 2.6 `GET /api/storage/lineage`、`DELETE /api/storage/chains/{chain_id}`
- [x] 2.7 `GET /api/collect/branches`、`POST /api/collect/source-columns`
- [x] 2.8 predict 补 `testset_ref/output_name/save_to_db`、结果写 `prediction`、父任务接线
- [x] 2.9 explain 接入预测父任务

## 3. 前端接线

- [x] 3.1 模型性能页评估批次下拉
- [x] 3.2 评估页选择已保存预测任务 + 输出命名
- [x] 3.3 storage 数据链路视图与整链删除
- [x] 3.4 collect 公开模式、分支刷新、字段读取
- [x] 3.5 详情页内联定位，移除独立路由与 ⑦/⑧ 编号

## 4. 数据内核

- [x] 4.1 `data_model/preparation/public_load.py` 抽出 `normalize_public` 并支持标签映射
- [x] 4.2 `data_model/preparation/collect.py` 新增 `list_branches/validate_public_config/run_public/source_columns`
- [x] 4.3 收集不再预生成 XLSX；移除 `format/split_ratio`

## 测试与验证

### 1. 单元测试

- 覆盖：`python -m compileall backend/app data_model` 与后端/内核模块导入通过。测试目录按用户决定保持删除，未运行 pytest。

### 2. 集成测试

- 覆盖：`figures`、`predict preview`、`storage lineage/chain`、`collect branches/source-columns` 的 HTTP 冒烟需可用 MySQL 环境；本次仅完成导入级验证，待有库环境补跑并记录。

### 3. 验收测试

- 依据：本 change 的 5 份 spec delta 与 `docs/api/{figures,predict,evaluate,storage,collect}.md`；前端 `npm run build` 已通过（1701 modules transformed）。页面截图与逐项操作结论待补。

### 4. 非功能验证

- 未声明新的性能靶子；整链删除仍按单事务执行，大链路删除耗时与产物目录清理待实测。

### 5. 已知缺口与后续计划

- 历史 `effort` 图只在读取层归一，未做库迁移；整链删除不删除仓库内交付权重；公开数据集许可证按文档为可选。责任：后端线；完成条件：在 MySQL 实机跑通 5 个新端点、补一次历史库兼容验证与页面截图。
