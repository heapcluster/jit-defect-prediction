# 预测性能评估 API（evaluate）

一句话：独立接收板块 ⑤ 对测试集预测产出、已透传真标签的 predictions（§3.4），按指定阈值和指标计算 metrics、混淆矩阵、多模型对比、图形与报告，不训练模型、不改变预测概率、不接受独立标签文件。

实现状态：已实现　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.4（predictions 输入）、§3.3（train_testset 作 effort 来源）、§3.6、§3.9；旧 §3.5 `labels.csv` 已废止。指标公式单源为 `data_model/evaluation/metrics.py`。

## 1. 职责与不负责范围

- 负责阈值与指标配置、逐模型指标、混淆矩阵、多模型排序对比、ROC/PR/校准/effort 等图形及报告交付。
- 负责不可用原因披露：无有效预测、样本不足、模型元信息不兼容不得伪造数值；缺真标签的输入在入口前置拒绝。
- 不负责采集、清洗、训练、预测或 XAI；不读取展示页状态作为计算依据。
- 不接受独立标签文件（旧 `labels.csv` 已废止）：真标签 MUST 已由板块 ⑤ 从 §3.3 `train_testset` 透传在 predictions 内。
- 历史 `model_metrics.csv` 仅作默认 0.5 的数值口径对照基线，不是运行输入或唯一数据来源。

## 2. 端点契约

### GET /api/evaluate/metrics

无请求参数。响应 `data.metrics[]` 每项 `{key,name,description,formula,threshold_dependent,effort_aware}`；另返回 `defaults:{metrics_selected,primary_metric,effort_enabled}`。

一期至少登记 `auc`、`ap`、`f1`、`precision`、`recall`、`accuracy`、`recall_at_20`、`recall_at_50`、`p_norm`、`popt`。公式说明由统一指标模块导出，前端不另写公式。

### POST /api/evaluate/run

`multipart/form-data`：`files[]` 必须含 predictions 表格（§3.4，须自带真标签），可再含一个 effort 来源表格（§3.3 `train_testset`）；`config` JSON part。不再接受 labels 表格。小文件同步，大文件创建 `kind=evaluate` job。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入 predictions 的便利选择；显式上传优先 |
| `model_names[]` | 否 | 限定模型；缺省评估 predictions 内全部模型 |
| `threshold` | 否 | 开区间 (0,1)，缺省读 `decision_threshold` |
| `metrics[]` | 否 | 缺省读 `metrics_selected`，逐项须在注册表 |
| `primary_metric` | 否 | 缺省读 `primary_metric`，须属于本次 metrics |
| `effort_enabled` | 否 | 缺省读同名配置；控制 effort-aware 指标与图 |
| `report_format` | 否 | `md` / `html`，默认 `md` |
| `format` | 否 | 表格输出 `csv` / `xlsx`，默认 `csv` |

同步响应 `data`：`{job_id,status:"success",outputs[],summary}`；异步为 `{job_id,status:"queued"}`。summary 含 `models`、`rows`、`unavailable[]`、`primary_metric`、`effort:{provided,matched}`；unavailable 项为 `{model_name,reason_code,message}`，原因码包括 `missing_effort`、`no_predictions`、`insufficient_samples`、`incompatible_model`。缺真标签的输入在入口直接 40001 拒绝，不生成 job。

### GET /api/evaluate/outputs/{job_id}/{name}

下载指标、混淆、图、报告或 manifest；所有文件都要求 `X-API-Key`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | schema/阈值/指标/排序配置非法、缺真标签、公式注入、同 kind 冲突、非法下载名 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 可选 dataset、job 或输出不存在 |
| 50000 | 500 | 未预期服务错误；运行期失败写脱敏 job 日志 |

## 3. 输入契约

predictions 逐字采用 [../file-contracts.md](../file-contracts.md) §3.4：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40) | 是 | 提交 |
| model_name | string | 是 | 模型 |
| risk_score | float [0,1] | 是 | 概率（5 位小数） |
| predicted_label | int 0/1 | 是 | 按 decision_threshold 的二分类标签 |
| decision_threshold | float | 是 | 本次判定阈值 |
| model_version / feature_version | string | 是 | 版本元信息 |
| predicted_at | datetime | 是 | 预测时间 |
| is_bug_inducing | int 0/1 | 是 | 透传真标签（来自 §3.3 `train_testset`，评估必填） |

真标签已由板块 ⑤ 透传在 §3.4 `predictions.csv` 的 `is_bug_inducing` 列，**每行 MUST 非空**；本端点不再接受独立标签文件（旧 §3.5 `labels.csv` 废止）。缺真标签在入口直接 40001 拒绝，不生成 job、不产半成品。

- 评估按本次 threshold 从 risk_score 重新推导评估用标签，不依赖输入 predicted_label 的旧阈值；输入 predicted_label 仍须通过 schema 校验。
- 真标签来自 §3.3 `train_testset`，无未打标样本；缺预测行不补 0。
- effort-aware 指标需真实 LOC 工作量：可选上传一个 §3.3 `train_testset` 表格作为 effort 来源，按 `la/ld`（log1p）反变换还原 `LOC = round(expm1(la)+expm1(ld))`，按 commit_hash join。缺 effort 来源时 effort-aware 指标披露 `missing_effort`，两类 effort 图仍交付（aware 图标注无工作量输入）。summary 含 `effort:{provided,matched}` 登记来源行数与命中行数；CLI 以 `--effort <train_testset>` 提供同源输入。
- 上传校验大小、扩展名魔数、列 schema、概率范围、真标签非空与 CSV 公式注入；缺 predictions、伪造文件或缺真标签返回 40001。

## 4. 输出契约

§3.6 的列定义逐字如下，不另造评估列：

- **metrics**：`model_name,line,metric,value,threshold,n,pos_rate,dataset_version,model_version,computed_at`（长表，逐模型逐指标一行）。
- **confusion**：`model_name,threshold,tp,fp,fn,tn`。
- **report**：md/html 含指标表 + 混淆 + 图引用 + 不可用原因清单。
- **图 png**：roc/pr/confusion/calibration/effort/feat_importance（effort 两类课程硬要求）。

| 文件 | 命名 |
|---|---|
| metrics | `evaluate_metrics_<job_id>.csv`，或 `.xlsx` |
| confusion | `evaluate_confusion_<job_id>.csv`，或 `.xlsx` |
| report | `evaluate_report_<job_id>.md`，或 `.html` |
| 各图 | `evaluate_<figure_type>_<job_id>.png`；effort-aware 与 effort-unaware 分别以 artifact 名区分 |
| manifest | `evaluate_metrics_<job_id>.manifest.json` |

report 中引用相对基础文件名，不引用本机绝对路径。没有有效数值时对应 metrics 行不写 0，原因进入 report；样本数、正样本率、阈值、数据集版本和模型版本随结果给出。

manifest 严格采用 §3.9，记录输入 checksum、真标签来源（train_testset）、阈值、指标集合、effort 开关、输出 checksum 和代码版本。CSV UTF-8 BOM，XLSX 单 sheet。默认 0.5 下与历史 `model_metrics.csv` 对应指标逐值一致，容差 1e-6，是口径验收线。

## 5. 可配置项

- 全局：`decision_threshold`、`metrics_selected`、`primary_metric`、`effort_enabled`；`risk_high_threshold` / `risk_mid_threshold` 仅用于风险展示，不混入指标公式。
- 单次运行：模型子集、阈值、指标、主排序、effort 开关、报告与表格格式。
- 指标注册和计算均来自 `data_model/evaluation/metrics.py`；后端和前端不得复制公式。
- `.env` 仅提供出厂默认，用户配置重启恢复。

## 6. 状态持久化

- 同步运行写终态，异步 kind=`evaluate` 写五态；同 kind 条件更新互斥，重启遗留 running 置 failed，可 retry/cancel。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore），job 登记全部产物与不可用项。
- 相同 predictions、阈值与指标配置重跑一致；`computed_at` 除外，数值与图形数据必须一致。
- 评估文件是否登记 model_figure 由 storage 决定，运行本身不依赖数据库已有模型或预测行。

## 7. 验收

fixtures：`tests/fixtures/files/evaluate/`，不上传模型、不调用 predict 也可运行。

- **正常**：上传带透传真标签的 predictions 产出 §3.6 全部所选结果、报告、manifest；多模型按主指标排序，默认 0.5 对照容差不超过 1e-6。
- **边界**：阈值边界、单模型、全正/全负、样本不足和无法计算 AUC 时给出原因，不伪造 0；缺真标签前置 40001；effort-aware 与 effort-unaware 两类图均存在。
- **非法**：缺 predictions、概率越界、未知指标、primary_metric 未选、重复键无法判定、伪造 XLSX、公式注入均返回 40001，不产半成品。
- 改阈值只影响阈值相关结果，不重训也不改 risk_score；CLI/API 数值一致，输出下载鉴权，重启后配置与 job 可恢复。

## 8. 边界

evaluate 只要求 §3.4 文件兼容（须含透传真标签），与 predict/train 的服务是否在线无关；输出可供 figures 登记展示，但展示导入不是计算前置。共享指标公式是代码依赖，不是数据库或上游服务依赖。
