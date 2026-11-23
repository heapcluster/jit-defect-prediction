# 模型训练 API（train）

一句话：独立接收 commits/cleaned 表格和算法配置，按时间序训练一个或多个模型，交付带特征顺序、元数据与 checksum 的 `model_package.zip`。

实现状态：已实现　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.2、§3.3、§3.9；算法读端点与公共口径见本文及 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责训练配置校验、多算法执行与失败隔离、时间序划分、模型工件打包、训练摘要和可选资产登记。
- 算法元数据来自 `algorithm` 表或独立内置注册快照；HTTP 表单通过 `/api/algorithms` 获取，不硬编码超参 schema。
- 不负责采集、清洗、在线预测、解释或独立性能报告；训练摘要的指标公式复用 `data_model/evaluation/metrics.py`。
- 文件工件是交付主路径；`model_artifact` 登记和派生 `model` 行是可选展示路径，不是预测加载的前置。

## 2. 端点契约

### GET /api/algorithms

查询参数：`line=expert|semantic|fused|e2e`（可选）、`enabled_only=0|1`（默认 0）。响应 `data.algorithms[]`：

| 字段 | 含义 |
|---|---|
| `line` / `algo` / `family` | 模型线、算法标识与算法族 |
| `enabled` / `description` | 启用状态与说明 |
| `hyperparams_schema[]` | `{name,type,default,min,max,choices,description}` |
| `input_requirements` | 所需特征或文本输入说明 |

未知 line 或非法 enabled_only 返回 40001。

### POST /api/train/run

`multipart/form-data`：`files[]` 上传一个 §3.1 commits 或 §3.2 cleaned 表格；`config` 为 JSON part。主表 ≤2000 行且算法均属 `{lr,nb,dt,knn,rf,et}` 时同步返回终态，否则创建 `kind=train` 异步 job。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入表格的便利选择；与上传文件二选一 |
| `line` | 是 | `expert` / `semantic` / `fused` / `e2e` |
| `algos[]` | 是 | 非空算法数组；逐项校验与 line 的组合 |
| `hyperparams` | 否 | `{algo:{param:value}}`，按 algorithms schema 校验 |
| `template_name` | 否 | 引用 `train.templates` 中模板；显式配置优先 |
| `split` | 否 | `{ratio:0.7}` 或 `{time_boundary:"..."}`；只允许时间序 |
| `seed` | 否 | 默认 42 |
| `decision_threshold` | 否 | 缺省读 `user_config.decision_threshold`，仅用于训练摘要标签 |
| `register` | 否 | 默认 `false`；为 true 时校验成功后登记 model_artifact 并派生 model 行 |
| `auto_load` | 否 | 默认 `false`；是否加载到运行时，不改变默认模型配置 |

同步响应 `data`：`{job_id,status:"success",outputs[],models[]}`；异步返回 `{job_id,status:"queued"}`。`models[]` 每项为 `{algo,model_name,version_key,feature_version,status,metrics,error}`；单算法失败不抹掉其他算法输出，metrics 数值由统一指标实现计算。

### GET /api/train/compare?job_id=<id>

仅成功 train 任务可用，读取已登记比较 JSON，返回 `{job_id 隐含,primary_metric,models[]}`；`models` 按 `user_config.primary_metric` 降序排序，指标缺失（含失败子项 `metrics:null`）排末尾，不重新训练。失败子项保留 status/error，不导致端点报错。

### GET /api/train/outputs/{job_id}/{name}

下载指定工件或 manifest，文件名必须在 job 输出登记中。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 表格/超参/算法组合非法、随机划分、特征不兼容、同 kind 冲突、非法下载名 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 可选 dataset、模板、job 或输出不存在 |
| 50000 | 500 | 未预期服务错误；单算法异常同时记入其子项状态 |

## 3. 输入契约

上传表格只能采用以下两种权威 schema。

§3.1 commits：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 来源仓库名 |
| author_name / author_email | string | 是 / 否 | 作者 |
| committed_at | datetime | 是 | 提交时间 UTC |
| message | string | 是 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| ns…sexp（14 列） | float | 是 | Kamei 14 维 log 变换值（`fix` 为 0/1），列序固定 |
| is_bug_inducing | int 空可 | 否 | SZZ 真标签 1/0/空 |
| labeled_at | datetime | 否 | 打标时间 |
| is_test | int 0/1 | 是 | 时间序划分标记 |
| label_method | string | 否 | szz / szz_lite |

§3.2 cleaned 逐字为：**“列同 3.1；另必伴 `steps_stats.json`（每步 rows_before/after/removed/label_dist/elapsed_ms/excluded_samples）与特征前后分布图 png。处理链配置快照入 manifest。”** 作为训练输入时只需要 cleaned 主表，统计和图不是训练计算前置。

上传执行大小、扩展名魔数、列 schema、类型、公式注入与空标签检查。训练仅使用已打标行计算监督目标，未打标 `is_bug_inducing` 不得当作 0。时间序 70/30 禁随机，测试集最早时间必须晚于训练集最晚时间。semantic/fused/e2e 所需输入不满足 `input_requirements` 时前置返回 40001，不伪造向量或文本。

## 4. 输出契约

每个成功算法交付一个独立模型包；文件名 `train_<algo>_model_package_<job_id>.zip`，同名 manifest 为 `train_<algo>_model_package_<job_id>.manifest.json`。

[../file-contracts.md](../file-contracts.md) §3.3 逐字规定：

> zip 内含：权重文件（expert/semantic/fused 为 `.pkl`；e2e 为 safetensors 目录）、`feature_order.txt`、`model_meta.json`（model_name/line/algo/version_key/feature_version/trained_at/超参快照/划分/种子）、`checksum.sha256`。predict/explain MUST 校验 checksum 与特征列宽后再加载。

- 不多算法混装为一个无法区分版本的包；失败算法不产 zip，也不覆盖已有可用工件。
- manifest 严格采用 §3.9，记录训练表格 checksum、算法与超参、时间序划分、种子、包 checksum、代码版本。
- `model_meta.json` 的字段名称与顺序语义以 §3.3 为准，不另造模型元数据列。
- `register=true` 时登记包路径、checksum、大小、训练 job、版本和特征版本，并由工件派生 model 行；登记失败不影响已交付文件，但子项状态必须说明。`auto_load=true` 仅对本任务自产的 expert 权重做热加载（校验特征列宽后放入运行时，不重启、不改默认模型配置）；通用已登记工件的加载端点属 predict/模型管理（W6）。同名模型已加载且权重 checksum 不同时，登记按 W2 安全规则拒绝并记入子项，不覆盖运行时。

## 5. 可配置项

- `train.templates`：模型线、算法集合、逐算法超参、时间序划分与种子的命名模板，落 `user_config` 并重启恢复。
- 单次运行：模板覆盖、算法、超参、划分、种子、训练摘要阈值、登记与加载开关。
- 算法清单和超参约束由 `/api/algorithms` 暴露；`.env` 只提供出厂默认，不能覆盖用户模板。
- 默认划分比例 0.7、种子 42、决策阈值读全局配置；禁止请求随机划分。

## 6. 状态持久化

- 每次运行有 `job_id`，同步写终态，异步 kind=`train` 写五态；job 保存逐算法子项、进度、入参快照和脱敏错误。
- 同 kind 通过表条件更新互斥；重启遗留 running 置 failed，可 retry/cancel；已成功子项工件保留且可复验。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；模型包与 manifest 的 checksum 在写盘后复算。
- `model_artifact` 只承担可选资产登记，不作为下游运行前置；运行时不依赖训练进程内对象。

## 7. 验收

fixtures：`tests/fixtures/files/train/`，不调用 collect、clean、predict 或 evaluation 服务。

- **正常**：两个算法分别设置超参后得到两个 §3.3 包；权重、feature_order、model_meta、checksum 完整，加载校验通过，manifest 可复现。
- **边界**：单算法、一个算法失败一个成功、小样本时间边界、未打标行、CPU/GPU 可用性差异均保持失败隔离且不覆盖旧工件。
- **非法**：缺列、空算法、非法组合、超参越界、随机划分、公式注入、伪造包或 checksum 不符返回 40001，不产半成品。
- 训练摘要与统一指标实现一致；默认 0.5 下与历史 `model_metrics.csv` 对应值逐值一致，容差 1e-6；CLI/API 同 fixture 的包元数据一致。

## 8. 边界

训练只要求输入文件满足 §3.1/§3.2，输出满足 §3.3；`dataset_id`、资产表和模型管理服务均为可选便利或展示能力。predict/explain 通过模型包消费结果，训练不调用它们，指标共享仅为代码单源而非服务前置。
