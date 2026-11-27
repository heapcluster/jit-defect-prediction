## Why

设计文档已明确 7 个页面、6 类任务与统一数据链路，但代码仍有 8 处“文档已定、实现待补”的差异：图集接口只认 `effort`、不能按评估批次单独取图；评估不逐图登记 `model_figure`；storage 缺少链路汇总与整链删除；collect 缺少分支枚举、公开数据集 URL 拉取与字段映射；批量预测缺预览与测试集父任务接线；详情页定位仍跳转独立页面。本次按文档补齐这些契约，保持模块边界与产物契约不变。

## What Changes

- `GET /api/figures`：`figure_type` 改为 `roc/pr/confusion/calibration/effort_unaware/effort_aware/feat_importance`；`model_name` 与 `job_id` 至少一个，可只按评估批次取图；响应补 `figure_name`；历史 `effort` 行读取时归一。
- 评估：`threshold/model_names/report_format/format` 从配置移除，阈值沿用预测结果；产物改为评估图集 zip + 评估指标表；逐张图落盘并登记 `model_figure`，可按 `job_id` 查询批次图集。
- storage：新增 `GET /api/storage/lineage` 与 `DELETE /api/storage/chains/{chain_id}`；`create_dataset.source_type` 只接受 `git_repo`。
- collect：新增 `GET /api/collect/branches`、`POST /api/collect/source-columns`；公开数据集模式改为 URL 拉取 + 字段/标签映射，与 Git 模式交付同一 `collected_commits` 契约；收集任务不再预生成 XLSX。
- predict：新增 `GET /api/predict/preview/{job_id}`；配置补 `testset_ref/output_name/save_to_db`，测试集只能来自训练成功任务；结果行写入 `prediction`；父任务同时接测试集训练任务与模型训练任务。
- explain：预测核对表 manifest 存在时，把预测任务接入链路父节点。
- 前端：模型性能页按评估批次下拉取图；评估页改为选择已保存预测任务并命名输出；storage 增加数据链路视图与整链删除；collect 启用公开模式与分支刷新；详情页内联定位面板，移除独立路由与 ⑦/⑧ 编号。

## Capabilities

### New Capabilities

- `query-api`：storage 链路汇总与整链删除。
- `commit-collection`：分支枚举与公开数据集 URL 拉取（作为现有收集能力的增量要求）。
- `predict-api`：批量预测预览与测试集父任务接线（增量要求）。
- `model-figure`：批次查询、`figure_name`、逐图登记（新增能力规格）。

### Modified Capabilities

- `ui`：批次下拉、链路视图、内联定位。

## Impact

- 代码：`backend/app/api/{figures,predict,collect,storage,evaluate}.py`、`backend/app/services/{storage,collect_run,evaluate_run,predict_run,explain_run}.py`、`backend/app/{schemas,errors}.py`、`data_model/preparation/{collect,public_load}.py`、`data_model/evaluation/evaluate.py`、`frontend/src/{api/index.js,router/index.js,views/*,components/LocalizationPanel.vue}`。
- 文档：`docs/api/{figures,storage,collect,evaluate,predict}.md`、`docs/web_page/{predict_detail,evaluate,collect,storage}.md` 删除对应“待补”标注。
- 不新增依赖；不恢复已删除的测试目录，验证使用 compileall、内核/API 冒烟与前端构建。
