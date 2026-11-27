# 模型训练 API（train）

一句话：按专家特征线或语义特征线，用清洗后数据集或训练测试集，训练一个或多个分类器，交付每个算法的 `.pkl` 权重、训练集与测试集；详细性能指标与图由预测评估模块产出。

实现状态：已实现　期次：一期

特征与标签 schema 及模型产物契约见本文 §4 与 [models.md](models.md) §3；功能点职责见 [`../function_point/train.md`](../function_point/train.md)。

## 1. 职责与不负责范围

- 负责两条特征线的算法目录、超参数校验、训练 / 测试切分、训练对比信息、产物登记与模型注册 / 热加载。
- 不负责特征抽取实现（特征列由输入表或数据集提供）、不负责标签生成、不负责在线预测、解释、详细性能评估与定位。
- 不设隐式默认模型：训练产物以文件交付并可自动登记，文件入口不依赖数据库登记。

## 2. 端点契约

### GET /api/algorithms

| 参数 | 必填 | 契约 |
|---|---|---|
| `line` | 是 | `expert` / `semantic`，非法 40001 |
| `enabled_only` | 否 | 0/1，其他值 40001 |

响应 `data.algorithms[]`：`{line, algo, family, enabled, description, hyperparams_schema, input_requirements}`。

### POST /api/train/run

`multipart/form-data`，不接受 query 参数。

| part | 必填 | 契约 |
|---|---|---|
| `config` | 是 | JSON 文本 |
| `files[]` | 否 | 主表 CSV/XLSX + 可选同名 manifest，最多 2 个，合计 ≤64MiB |

`config` 字段：

| 字段 | 必填 | 契约 |
|---|---|---|
| `line` | 是 | `expert` / `semantic` |
| `algos` | 是 | 非空、不重复，必须在对应线算法目录内 |
| `feature_set` | 否 | expert→`kamei14`、semantic→`codebert768`，必须与 line 匹配 |
| `hyperparams` | 否 | 按算法分键，键必须在 schema 可选子集内 |
| `split` | 否 | 默认 `{"ratio":0.7}`；`ratio` 与 `time_boundary` 互斥；Web 页时间切分由滑杆生成 `time_boundary` |
| `seed` | 否 | 非负整数，默认 42；Web 页可手填或随机生成 |
| `decision_threshold` | 否 | [0,1]，缺省取系统配置；Web 页不展示，仅供 API / CLI |
| `register` / `auto_load` | 否 | bool，默认按配置 |
| `dataset_id` | 否 | 已导入数据集；与上传主表二选一 |
| `template_name` | 否 | 训练模板名，须存在于配置 `train.templates`，否则 40400 |

上传表与 `dataset_id` 都没有 → 40001「请上传训练主表或选择已导入数据集」。未知键 40001。

响应：

- 同步（行数 ≤2000 且算法 ⊆ `{lr,nb,dt,knn,rf,et}`）：`{job_id,status,outputs,models,summary,testset,error_log}`。
- 异步：`{job_id,status}`。

`summary`：`input_rows,labeled_rows,unlabeled_rows,train_rows,test_rows,success_count,failed_count,warnings[]`。

`models[i]`：`algo,model_name,version_key,feature_version,status,metrics,warnings,error,elapsed_ms,hyperparams,register_status,load_status`。

### GET /api/train/outputs/{job_id}/{name}

下载已登记产物。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 配置/超参/line/algos 非法、输入缺失、测试集含空标签、数据量不足、模型文件校验失败 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 数据集、模板、模型文件、比较产物或输出不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 上传主表：清洗后数据集 schema（clean_dataset 列契约），expert 线另需 14 维特征；semantic 线需 768 维向量。
- `dataset_id`：成员非空，且绑定可读取的本地仓库路径；URL 形式返回 40001。
- 测试集标签必须全部非空，否则 40001。
- Web 页时间滑杆需要清洗产物提供 `summary.time_range`（最早、最晚提交时间）与 `summary.time_bins`（时间分桶与累计样本数）；缺少时页面退回手填时间边界，不影响 API 直接传 `time_boundary`。

## 4. 输出契约

```text
train_<algo>_model_<job_id>.pkl
train_<algo>_meta_<job_id>.json
train_trainset_<job_id>.csv / .xlsx
train_testset_<job_id>.csv / .xlsx
<stem>.manifest.json
```

每个成功算法产出一个独立的 `.pkl`，结果文件区逐算法展示与下载；`train_<algo>_meta_<job_id>.json` 是模型注册所需的内部元数据，落盘但不登记为用户结果文件。训练不产出 ZIP 模型包。

`train_trainset` 与 `train_testset` 均作为用户产物下载核对；`train_comparison_<job_id>.json` 与 `/api/train/compare` 已移除。

- `.pkl` 非空且可被预测模块直接加载；checksum 由 manifest 登记，不再生成单独的 `checksum.sha256`。
- `model_name = "{algo}_{fingerprint前8}_v1"`，`version_key = fingerprint[:16]`。
- `models[].metrics` 仅作内部诊断，训练页不展示、不排序；权威指标、混淆矩阵与图由功能 ⑥ 产出。
- 注册 / 加载结果只写入 `register_status` / `load_status`，失败不回滚任务。

## 5. 可配置项

`train.templates`、`register`/`auto_load` 默认值、`decision_threshold`、主指标、特征线默认算法集来自配置中心；超参与线由请求显式指定。

## 6. 状态持久化

- 任务 `kind=train`，五态；同步阈值 2000 行；`job.total = 行数 + 1`。
- 输入快照落 `temp/train_inputs/<hash>/request.json`，重试校验 checksum。
- 产物不可覆盖；成功写 `output_ref_json`（含 `models`、`testset`、`summary`）。

## 7. 验收

- 两条线各算法可训练，超参与线不匹配被拒绝。
- 每个 `.pkl` 可被 predict 直接加载并预测。
- 测试集标签非空、列符合契约。
- 每个算法的 `.pkl`、训练集、测试集与 manifest 齐全；不产出 ZIP 模型包；不产出比较 JSON、比较接口或评估报告。
- 训练集与测试集均为用户可下载产物。
- 相同输入与种子结果可复现（模型名/版本除外）。

## 8. 边界

训练模块只吃文件，不感知上游是否存在在线数据；模型注册与热加载是可选展示路径，未注册的 `.pkl` 同样可用 predict 的文件入口完成预测（外部交付包仍可为 ZIP）。


