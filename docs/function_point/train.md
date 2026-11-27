# 功能点 4 模型训练

一句话：按设计图，用清洗后数据划分训练 / 测试集，选择一个或多个算法并设置超参数，交付每个算法的 `.pkl` 权重、训练集与测试集。

clean_dataset 列契约、训练测试集与模型文件契约；API 见 [`../api/train.md`](../api/train.md)；页面见 [`../web_page/train.md`](../web_page/train.md)。

## 1 职责

- 维护两条特征线的算法目录与超参数 schema，由 `algorithm` 表登记，表单不硬编码。
- 按比例或提交时间切分训练 / 测试集，训练一个或多个算法；Web 页的比例切分与时间切分都用滑杆，时间滑杆在数据集最早与最晚提交时间之间取值并实时显示两侧比例。
- 交付每个算法一个独立的 `.pkl` 权重文件、训练集、测试集与 manifest；**不做任何模型性能对比**，不产出指标、排序、对比图与评估报告。
- 训练页不设判定阈值；阈值只在⑤预测时设置，训练任务缺省取系统配置。
- 训练成功后自动登记模型并热加载，结果区展示登记 / 加载状态。

## 2 不负责

- 不做特征抽取实现，不做标签生成；expert / semantic 特征在训练中生成并固化进 `.pkl` 与其侧车元数据。
- 不做在线预测、详细性能评估、解释或定位；不展示或排序任何性能指标。
- 不设隐式默认模型；模型必须由运行配置显式选择。
- 不把训练 / 测试标记列写入 collect 或 clean 产物。

## 3 输入

| 输入 | 说明 |
|---|---|
| 清洗后数据集 | clean_dataset 列契约 `clean_dataset.csv`，CSV 为规范主表；XLSX 仅在下载时按需生成，不得含 `is_test` 与模型特征列 |
| 已登记数据集 | `dataset_id`，要求绑定可读取的本地仓库路径 |
| 训练测试集 | 训练测试集契约 `train_testset`，仅在复用已切分数据时作为输入，标签必须非空 |

`config`：`line`、`algos`、`feature_set`、`hyperparams`（按算法分键）、`split`（`ratio` 或 `time_boundary` 二选一）、`seed`、`register`、`auto_load`，以及 `dataset_id` / `template_name`。`decision_threshold` 仍可由 API / CLI 显式传入，Web 页不展示，缺省取系统配置。

## 4 流程

1. 校验线、算法、超参与特征维度；模板命中后与显式配置合并，显式优先。
2. 读取清洗后数据集，校验列契约与标签完整性。
3. 按 `split` 切分（比例或提交时间边界），产出训练集与测试集；逐算法按请求顺序训练，进度回显当前算法，记录耗时与警告。
4. 为每个成功算法生成独立的 `.pkl`，统一产出训练集、测试集与 manifest；特征顺序 / schema / 超参写入侧车 JSON，训练日志仅作内部记录。
5. 发布产物与 manifest，自动登记并热加载模型；失败只记录状态，不影响其他算法。

## 5 输出

```text
train_<algo>_model_<job_id>.pkl
train_<algo>_meta_<job_id>.json
train_trainset_<job_id>.csv / .xlsx
train_testset_<job_id>.csv / .xlsx
<stem>.manifest.json
```

每个成功算法一个 `.pkl`，结果文件区逐算法单独展示与下载；`train_<algo>_meta_<job_id>.json` 是侧车元数据（特征顺序、特征 schema、超参与版本），只随 manifest 归档，不占结果文件位。训练不产出 ZIP 模型包，逐算法 `.pkl` 单独下载。

训练集只用于用户下载核对，不作为下游模块输入；预测与评估只消费测试集。训练产物同时提供训练集 `train_trainset_<job_id>.csv/.xlsx` 与测试集。

`train_comparison_*.json` 与 `/api/train/compare` 不属于训练结果；模型元数据 JSON 只作注册内部文件，不登记为用户结果文件。

`summary`：`input_rows, labeled_rows, unlabeled_rows, train_rows, test_rows, success_count, failed_count, warnings[]`。

不产 `train_metrics_*.csv`、ROC / PR / 混淆 / 指标条形图；这些是功能 ⑥ 的交付物。

## 6 约束

- `.pkl` 必须可被 predict 直接加载；元数据由侧车 JSON 提供（model_name / line / algo / feature_set / feature_order / feature_schema / 超参 / 划分 / 种子），checksum 由 manifest 登记。
- 测试集标签必须全部非空，否则拒绝训练。
- 未打标样本不参与训练；标签分布写入 summary。
- 相同输入、算法与种子结果可复现，模型名 / 版本随指纹变化；种子可由用户手填或随机生成。
- 时间切分依赖清洗产物登记提交时间范围与时间分布；缺少该元数据时 Web 页只能退回手填时间边界。
- 后端已按逐算法 `.pkl` + 侧车 JSON 产出并登记；训练不生成 ZIP 模型包。
- 训练页不展示指标、不做算法排序、不画对比图；混淆矩阵、ROC / PR 与评估报告均由⑥产出。
- 前端算法与超参数标签使用中文用户语言，不暴露原始 key / value。

## 7 验收

- 两条线的算法均可用；线与算法、超参不匹配被拒绝。
- 每个 `.pkl` 能被预测模块加载并给出预测。
- 每个算法的 `.pkl`、训练集、测试集与 manifest 齐全；训练集与测试集均可下载为 CSV / XLSX；页面不展示任何性能对比，也不产出 ZIP 模型包。
- 时间切分在清洗产物带时间范围时可用滑杆并实时显示两侧比例；缺少时间范围时明确提示并退回手填。
- 数据量不足、标签缺失、维度不符时给出明确错误。
- 多算法单次训练中，单个算法失败不影响其他算法。

## 8 边界

训练只吃文件：不要求库中已有 commit 或预测；模型注册是自动完成的展示路径，未注册的 `.pkl` 仍可用于预测 / 解释的文件入口（外部交付包可为 ZIP，训练自身不产出 ZIP）。

