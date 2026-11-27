# 功能点 5 模型预测

一句话：用训练阶段已保存的模型对训练产出的测试集打分，输出风险分数与预测标签，把预测二维表写入数据库，并交付一份核心预测结果文件。

设计状态：目标设计。Web 页面只做训练产物上的批量预测；判定阈值默认 `0.5`；预测结果二维表必须写入 `prediction` 表；结果文件区只展示一个核心「预测结果」。

训练测试集与模型文件契约、predictions 列契约；数据库落库见 [`../database/prediction.md`](../database/prediction.md)；API 见 [`../api/predict.md`](../api/predict.md)；页面见 [`../web_page/predict.md`](../web_page/predict.md)。

## 1 职责

- 单条预测：读已存特征或现算特征，返回 `risk_score`、`predicted_label`、`risk_level` 与版本信息。
- 批量预测：吃训练任务产出的 `train_testset`，逐行打分并交付 `predict_predictions` 文件。
- 把批量预测成功的全部结果行写入 `prediction` 表，供提交详情与预测页分页预览读取。
- 维护阈值判定、风险等级、模型 / 特征版本与 stale 标记。

## 2 不负责

- 不训练模型、不生成特征、不生成解释或定位、不评估。
- Web 页面不提供手动上传、不选择任意数据集；测试集只能是训练阶段产物。
- 不设默认模型：必须显式给出 `model_name`。
- 不把缺失特征当作 0。
- 不在结果文件区展示 summary、manifest、failed_samples 等内部记录。

## 3 输入

| 入口 | Web 页面 | API / CLI |
|---|---|---|
| 模型 | 已登记且可用模型下拉框 | `model_name` 必填 |
| 测试集 | 训练成功任务产出的 `train_testset` 下拉框 | `testset_ref` / `dataset_id` / 上传表 |
| 判定阈值 | 滑杆，默认 `0.5`，范围 `[0.05,0.95]` | `decision_threshold` 可选，默认 `0.5` |
| 输出名称 | `预测结果 / 导出文件名称` | `output_name` 可选 |

模型与测试集必须匹配：

- 模型特征线为 expert 或 semantic；
- 测试集 schema 符合训练测试集与模型文件契约；
- `train_testset` 真标签非空；
- 不匹配时拒绝运行，不产出结果。

## 4 流程

1. 用户选择训练阶段已保存的模型，系统自动带出同训练任务测试集；用户可改选其他训练任务测试集。
2. 用户查看模型详情与测试集详情，确认模型、特征线和样本规模。
3. 用户设置判定阈值，默认 `0.5`；页面不展示阈值说明文字。
4. 用户填写预测结果 / 导出文件名称，并核对配置摘要。
5. 用户点击 [开始预测]，校验模型可用性、测试集 schema、特征线与输出名称。
6. 加载模型，对测试集逐行打分，输出 `risk_score`。
7. 按 `risk_score >= decision_threshold` 生成 `predicted_label`。
8. 按配置生成 `risk_level`，写入摘要与结果表。
9. 成功行写入 `prediction` 表；失败行进入 `failed_samples`（≤100）。
10. 发布核心结果文件，页面展示统计、摘要、分页预览和入库行数。

## 5 输出

用户可见核心产物只有一份：

```text
predict_predictions_<job_id>.csv
```

填写 `output_name` 时：

```text
<output_name>.csv
```

列严格采用 predictions 列契约，且预览展示全部列：

```text
commit_hash, model_name, risk_score, predicted_label, decision_threshold,
model_version, feature_version, predicted_at, is_bug_inducing
```

不展示内部特征列：

```text
features, raw_feature_vector, explanation, localization
```

下载：

- `format=csv`：直接返回规范主表；
- `format=xlsx`：下载时从同一 CSV 即时生成单 sheet XLSX，不落盘、不登记。

内部记录：

```text
predict_summary_<job_id>.json
<stem>.manifest.json
```

数据库落库：

- 全部成功行写入 `prediction` 表；
- 落库列与 predictions 列契约对齐；
- 同一 `(commit_hash, model_name)` 幂等 upsert；
- 保存失败视为任务失败，文件产物保留，可重试。

## 6 约束

- Web 页面测试集只能是训练阶段产出的 `train_testset`。
- `decision_threshold ∈ [0.05,0.95]`，默认 `0.5`。
- 阈值变化只改 `predicted_label`，不改 `risk_score`。
- 特征维度固定：expert 14、semantic 768；不一致拒绝。
- 预测结果二维表必须数据库保存。
- 结果文件区只展示「预测结果」一个逻辑文件；下载菜单只有 CSV 与 Excel。
- 历史预测结果在 `/storage` 产物库查看，不在预测页展示历史列表。

## 7 验收

- 页面只能选择训练阶段产出的测试集，不能手动上传或选择任意数据集。
- 选中模型后显示模型详情；选中测试集后显示测试集详情。
- 判定阈值默认 `0.5`，无说明文字。
- 预测进度显示“已完成 X / Y 条提交”，支持取消与失败重试。
- 成功后预测结果二维表写入 `prediction` 表，并显示已入库行数。
- 分页预览展示 predictions 列契约全部列，不展示内部特征列；每一行都可点击进入该条预测详情。
- 预测详情页按 `commit_hash`、`model_name`、`job_id` 定位单条预测；主体为当前 commit 的预测详情，随后是预测结果解释和缺陷定位及修复两个普通板块，UI 不刻意展示功能编号 ⑦ / ⑧。
- 结果文件区只有一个「预测结果」逻辑文件；下载菜单只有 CSV 与 Excel。
- 解释与定位入口只在预测详情页；预测页不重复放置。
- 单条与批量同模型、同阈值、同特征结果一致。

## 8 边界

预测是独立工具：文件与模型齐备即可运行，不要求库里有提交、清洗或训练记录；Web 页面固定使用训练产物，便于页面验收与结果回溯。评估、解释、定位不在本模块完成。




