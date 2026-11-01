# 测试集评估看板

纵向功能点：把测试集（按提交时间切出的后 30%）的 commit 信息、选中模型的判断与该模型线的性能图统一展示。跨模型线、数据库、后端、前端。

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 交付逐提交预测 CSV（`data_model/pipelines/{line}/data/prediction_result.csv`）、对比图集（`{line}/reports/figs/*.png`），并给出测试集时间边界 `test_split_at` |
| 数据库 | **不加新表、不加新列**：`prediction` 按模型导入；真标签取 `commit_label` 的 szz 行；测试集边界存 `runtime_setting.test_split_at` |
| 后端 | `GET /api/commits?scope=test` 出明细；`StaticFiles` 挂 `/static/figures/{line}/*.png` |
| 前端 | eval 页：两级选择 `line` → `model`，展示该线图集 + 明细表（可按 commit 时间区间收窄） |

## 范围
- 特征只展示 Kamei 14 维，**且仅 expert 线**；semantic / fused / e2e 的 14 维不是它们的模型输入，明细不显示特征列；
- 真标签只取 szz，无人工标签；
- 模型覆盖四线 25 个（可先 expert 8 个打样）；
- 图按线给现有对比图（`roc_curves` / `metric_bars` / `effort_curves_loc`），不做逐模型图集、不建 `model_figure` 表。

## 阈值工作点
本看板接手原质量看板的校准职责：在明细与图上选定工作点后，经 `PUT /api/config` 写入 `runtime_setting.high_risk_threshold`，立即作用于前端的风险分级与高/低判定（判定由调用方按阈值算，接口不返回布尔判定字段）。真值只有 szz，人工标签不参与。

## 实现状态（写在这里防漂移）
截至 `21a1a77`，本节内容**除模型线产物外全部未实现**：后端无 eval 页接口（测试集明细已并入 `/api/commits?scope=test`）、无 `StaticFiles` 挂载、`model` 表无 `line`、`commit_feature` 无 `is_test`、库中无 `model_figure` 表；前端 `views/` 无 eval 页、路由表无 `/eval`。模型线侧已有 4 条线的 `reports/figs/*.png` 与 `expert/data/prediction_result.csv`（83,943 行，覆盖全集而非测试集）。
落地顺序：模型线交 `test_split_at` → 后端建接口 → 前端建页。**在接口存在之前，任何文档与页面都不许引用它。**

## 验收
- 配好 `test_split_at` 后，`scope=test` 的明细只出现边界之后的提交；
- 切换 `line` → `model`，明细与图集同源刷新，互不串线；
- 页面上 effort-unaware 与 effort-aware 两类指标图各至少一张（课程硬要求）；
- 未预测的提交不进明细行，用页顶「测试集 `test_total` / 已预测 `total` / 缺 K」表达缺口；MUST NOT 渲染成风险 0。
