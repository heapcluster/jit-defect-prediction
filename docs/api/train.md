# 模型训练 API（train）

一句话：独立接收 `clean_dataset.csv`、模型线与算法配置，在训练阶段**内部**生成模型特征并按用户配置的划分方式（`random` 默认 / `time_order`）训练一个或多个模型，交付带特征顺序、`feature_schema.json`、元数据与 checksum 的 `.pkl` 权重 `model_package.zip` 与带真标签的测试集。

实现状态：目标契约（旧实现待改造）　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.2、§3.3、§3.9；算法读端点与公共口径见本文及 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责训练配置校验、模型特征选择与生成、训练侧变换、多算法执行与失败隔离、可配置划分、测试集产出、模型工件打包和可选资产登记。
- 算法元数据来自 `algorithm` 表或独立内置注册快照；HTTP 表单通过 `/api/algorithms` 获取，不硬编码超参 schema。
- 不负责采集、清洗、在线预测、解释或性能评估；AUC/F1 等指标与多模型比较归板块 ⑥，本模块只产出模型包与带真标签的测试集。
- 文件工件是交付主路径；`model_artifact` 登记和派生 `model` 行是可选展示路径，不是预测加载的前置。

## 2. 端点契约

### GET /api/algorithms

查询参数：`line=expert|semantic`（可选）、`enabled_only=0|1`（默认 0）。响应 `data.algorithms[]`：

| 字段 | 含义 |
|---|---|
| `line` / `algo` / `family` | 模型线、算法标识与算法族 |
| `enabled` / `description` | 启用状态与说明 |
| `hyperparams_schema[]` | `{name,type,default,min,max,choices,description}` |
| `input_requirements` | 内部特征生成要求说明（Kamei 14 维 / CodeBERT 768 维） |

未知 line 或非法 enabled_only 返回 40001。

### POST /api/train/run

`multipart/form-data`：`files[]` 上传一个 §3.2 `clean_dataset` 表格；`config` 为 JSON part。**不接受** `feature_file` 等外部特征文件，也不接受 `repo_source` 配置。主表 ≤2000 行且算法均属 `{lr,nb,dt,knn,rf,et}` 时同步返回终态，否则创建 `kind=train` 异步 job。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入表格的便利选择；与上传文件二选一 |
| `line` | 是 | `expert` / `semantic`（仅两线） |
| `feature_set` | 是 | 与 line 兼容：`expert`→`kamei14`（Kamei 14 维）；`semantic`→`codebert768`（冻结头 CodeBERT 768 维） |
| `feature_transform` | 否 | 训练侧变换：`log_transform` / `standardize` / `categorical_encode` / `feature_select`，只在训练集拟合 |
| `algos[]` | 是 | 非空算法数组；逐项校验与 `(line, feature_set)` 的组合 |
| `hyperparams` | 否 | `{algo:{param:value}}`，按 algorithms schema 校验 |
| `template_name` | 否 | 引用 `train.templates` 中模板；显式配置优先 |
| `split` | 否 | `{mode:"random", ratio:0.7}`（默认）或 `{mode:"time_order", ratio:0.7, time_boundary:"..."}`；两种模式均允许用户配置 |
| `seed` | 否 | 默认 42；`random` 模式按 seed 固定划分 |
| `decision_threshold` | 否 | 缺省读 `user_config.decision_threshold`；训练不计算性能指标，阈值判定归 predict/evaluate |
| `register` | 否 | 默认 `false`；为 true 时校验成功后登记 model_artifact 并派生 model 行 |
| `auto_load` | 否 | 默认 `false`；是否加载到运行时，不改变当前选择 |

同步响应 `data`：`{job_id,status:"success",outputs[],models[],testset}`；异步返回 `{job_id,status:"queued"}`。`models[]` 每项为 `{algo,model_name,version_key,feature_version,status,error}`；单算法失败不抹掉其他算法输出，本模块不返回 metrics。`testset` 为切分出的测试集文件名（§3.3 `train_testset`），供板块 ⑤ 作为预测输入。

### GET /api/train/outputs/{job_id}/{name}

下载指定工件或 manifest，文件名必须在 job 输出登记中。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 表格/超参/算法组合非法、划分 mode 或比例非法、`time_order` 边界断言失败、特征不兼容、同 kind 冲突、非法下载名 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 可选 dataset、模板、job 或输出不存在 |
| 50000 | 500 | 未预期服务错误；单算法异常同时记入其子项状态 |

## 3. 输入契约

上传表格只采用 §3.2 `clean_dataset`：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 仓库名或数据集名 |
| repo_url | string | 否 | 来源 URL |
| author_name / author_email | string | 否 | 作者 |
| committed_at | datetime | 否 | 提交时间 UTC |
| message | string | 否 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| is_bug_inducing | int 空可 | 是 | 缺陷标签 1/0/空 |
| label_method | string | 否 | 标签方法 |
| label_source | string | 是 | `git_szz` / `public_dataset` |
| labeled_at | datetime | 否 | 打标时间 |
| fix_commit_hash | string(40) | 否 | SZZ 回溯修复提交 |
| source_type | string | 是 | `git_repo` / `public_dataset` |

`clean_dataset` 不含模型特征集、训练测试划分和训练侧变换结果。训练阶段按 `feature_set` **内部生成**模型特征：`kamei14` 由训练模块根据数据集绑定来源/提交变更计算 Kamei 14 维，`codebert768` 由训练模块使用数据集绑定的仓库快照/提交文本经冻结头 CodeBERT 编码为 768 维。`repo_source` / `feature_file` 不是 API 字段或上传文件；内部来源缺失或编码失败时前置返回 40001，不伪造向量。

上传执行大小、扩展名魔数、列 schema、类型、公式注入与空标签检查。训练仅使用已打标行计算监督目标，未打标 `is_bug_inducing` 不得当作 0。划分方式用户可配置：`split.mode=random`（默认，按 `seed` 固定随机划分）或 `split.mode=time_order`（时间序，保留「测试集最早时间必须晚于训练集最晚时间」断言）；默认比例 0.7。非法 mode、比例越界或 `time_order` 断言失败返回 40001；随机划分不再视为非法。`feature_transform` 只在训练集拟合 scaler/encoder，并随模型包固化。

## 4. 输出契约

每个成功算法交付一个独立模型包；文件名 `train_<algo>_model_package_<job_id>.zip`，同名 manifest 为 `train_<algo>_model_package_<job_id>.manifest.json`。另交付切分出的测试集 `train_testset_<job_id>.csv/xlsx`，同名 manifest。

[../file-contracts.md](../file-contracts.md) §3.3 逐字规定：

> zip 内含：权重文件均为 `.pkl`（expert=`kamei14` 14 维、semantic=`codebert768` 768 维，两线均用传统分类器）、`feature_order.txt`、`feature_schema.json`（字段名/类型/来源/版本/训练侧变换）、`model_meta.json`（model_name/line/algo/feature_set/version_key/feature_version/trained_at/超参快照/划分 mode/种子）、`checksum.sha256`。predict/explain MUST 校验 checksum 与特征列宽后再加载。
>
> `train_testset` schema 与 §3.2 `clean_dataset` 逐列一致，每行 MUST 带非空 `is_bug_inducing` 真标签，无标签行不进入测试集；MUST NOT 含 `is_test` 或模型特征列。供板块 ⑤ 作为评估预测输入。

- 不多算法混装为一个无法区分版本的包；失败算法不产 zip，也不覆盖已有可用工件。
- 本模块不产出 AUC/F1 等指标、混淆矩阵、比较 JSON 或对比图；性能评估归板块 ⑥。
- manifest 严格采用 §3.9，记录训练表格 checksum、算法与超参、划分 mode 与比例/时间边界、种子、包与测试集 checksum、代码版本。
- `model_meta.json` 的字段名称与顺序语义以 §3.3 为准，不另造模型元数据列。
- `register=true` 时登记包路径、checksum、大小、训练 job、版本和特征版本，并由工件派生 model 行；登记失败不影响已交付文件，但子项状态必须说明。`auto_load=true` 仅对本任务自产的 expert 权重做热加载（校验特征列宽后放入运行时，不重启、不改变当前选择）；通用已登记工件的加载端点属 predict/模型管理（W6）。同名模型已加载且权重 checksum 不同时，登记按 W2 安全规则拒绝并记入子项，不覆盖运行时。

## 5. 可配置项

- `train.templates`：`line`、`feature_set`、算法集合、逐算法超参、训练侧变换、划分 mode/比例/边界与种子的命名模板，落 `user_config` 并重启恢复。
- 单次运行：模板覆盖、模型线、特征集、训练侧变换、算法、超参、划分、种子、登记与加载开关。
- 算法清单和超参约束由 `/api/algorithms` 暴露；`.env` 只提供出厂默认，不能覆盖用户模板。
- 默认划分 `mode=random`、`ratio=0.7`、种子 42；性能指标与阈值配置归板块 ⑥，不在训练配置内。

## 6. 状态持久化

- 每次运行有 `job_id`，同步写终态，异步 kind=`train` 写五态；job 保存逐算法子项、进度、入参快照和脱敏错误。
- 同 kind 通过表条件更新互斥；重启遗留 running 置 failed，可 retry/cancel；已成功子项工件保留且可复验。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；模型包与 manifest 的 checksum 在写盘后复算。
- `model_artifact` 只承担可选资产登记，不作为下游运行前置；运行时不依赖训练进程内对象。

## 7. 验收

fixtures：`tests/fixtures/files/train/`，不调用 collect、clean、predict 或 evaluation 服务。

- **正常**：两个算法分别设置超参后得到两个 §3.3 包；权重、feature_order、model_meta、checksum 完整，加载校验通过，manifest 可复现。
- **边界**：单算法、一个算法失败一个成功、小样本两种划分模式、未打标行、CPU/GPU 可用性差异均保持失败隔离且不覆盖旧工件。
- **非法**：缺列、空算法、非法组合、超参越界、划分 mode/比例非法、`time_order` 断言失败、公式注入、伪造包或 checksum 不符返回 40001，不产半成品。
- 切分产出带真标签的 `train_testset`（每行 `is_bug_inducing` 非空），schema 与 §3.2 一致，可被 predict 直接作为输入；CLI/API 同 fixture 的包元数据与测试集一致。
- 本模块不返回或产出性能指标；多模型比较与指标数值在板块 ⑥ 验收。

## 8. 边界

训练要求输入 `clean_dataset` 满足 §3.2，模型特征由训练阶段内部按 `feature_set` 生成，输出满足 §3.3（模型包 + 测试集）；`dataset_id`、资产表和模型管理服务均为可选便利或展示能力。predict 通过模型包与 §3.3 测试集消费结果，evaluate 通过 predict 的 §3.4 文件评估性能；训练不调用它们，也不计算指标。
