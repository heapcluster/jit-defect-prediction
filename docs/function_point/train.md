# 模型训练（功能 4）

实现状态：目标契约（旧实现待改造）　期次：一期

## 一句话概述

独立的模型训练工具：上传清洗数据并划分训练/测试集，按 `algorithm` 表驱动的模型线、算法和超参执行多算法训练，隔离单项失败，交付可校验、可复现的模型包与带真标签的测试集；性能评估不在本模块，交由板块 ⑥。

## 1 职责与不负责范围

**负责**：

- 接收 `clean_dataset.csv`、模型线、模型特征集、一个或多个算法、超参、可配置划分方式与随机种子，复用两线训练实现生成模型；按划分产出带真标签的测试集供板块 ⑤ 预测。
- 在训练阶段**内部**按 `feature_set` 选择并生成模型特征：`expert` 使用 `kamei14`（内部从提交变更计算 Kamei 14 维），`semantic` 使用 `codebert768`（内部用数据集绑定的仓库快照/提交文本经冻结头 CodeBERT 抽取 768 维）。特征来源不对外暴露为 `feature_file` / `repo_source` 配置。
- 训练侧只使用训练集拟合 `log_transform`、`standardize`、`categorical_encode`、`feature_select`，并把特征顺序与 schema 固化进模型包。
- 从 `algorithm` 表读取算法启停、模型族和超参 schema，提供动态配置校验与训练模板；不在前端或请求处理代码写死算法清单。
- 一次任务内逐算法执行并隔离失败，保存子项状态与日志；不计算性能指标、不做多模型排序。
- 为每个成功算法生成带权重、特征顺序、元信息和 checksum 的模型包；切分出的测试集单独落盘，供板块 ⑤ 预测、板块 ⑥ 评估。可选登记资产并通知 predict 加载。

**不负责**：

- 数据采集、清洗、在线预测、模型运行时管理、XAI 或行级定位。
- 计算性能指标或做多模型比较；这些归板块 ⑥，本模块只产出模型包与测试集。
- 新算法研究、AutoML、分布式/GPU 集群调度或 CI 门禁执行。

## 2 独立运行入口

```bash
python -m pipelines.train run \
  --input clean_dataset.csv --line expert --algos lr,rf \
  --hyperparams hp.json --split-mode random --split-ratio 0.7 --seed 42 --out ./out
python -m pipelines.train algorithms --line expert
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python -m pipelines.train run/algorithms` | 输入文件与配置即可训练；算法注册信息来自同一算法元数据源 |
| 算法 API | `GET /api/algorithms` | 查询 `algorithm` 表中的模型线、算法、family、启停和超参 schema |
| 任务 API | `POST /api/train/run` | multipart 上传 CSV/XLSX 与训练配置，返回 `job_id`；可选 `dataset_id` 仅作便利输入 |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 五态、子项进度、日志、取消与重试 |
| 下载 | `GET /api/train/outputs/{job_id}/{name}` | 下载模型包、测试集、训练日志与 manifest |

所有 HTTP 端点（含工件下载）必须使用 `X-API-Key`。Web 训练页只组装配置和展示结果，不实现训练或性能计算。

## 3 输入契约

- 主输入遵循 [`../file-contracts.md`](../file-contracts.md) §3.2 `clean_dataset.csv`。该文件只有清洗后的提交元信息、标签和基础派生列，不含模型特征集、训练测试划分或训练侧变换结果。
- 本次训练配置包括 `line`、`feature_set`、`algos[]`、逐算法 `hyperparams`、`split`、`seed`、`auto_register`、`auto_load` 和 `template_id`；完整配置进入 job 与 manifest。**不接收** `feature_file` / `repo_source`。
- 模型特征是训练内部环节：`kamei14` 由训练模块根据数据集绑定的仓库快照/提交变更计算；`codebert768` 由训练模块用数据集绑定的仓库快照/提交文本经冻结头 CodeBERT 内部编码。内部来源缺失或编码失败时前置拒绝，不伪造向量。用户只需选择模型线，不需也不应提供特征来源。
- `(line, algo)` 必须在算法元数据中登记，超参按 schema 校验类型、范围与枚举；不兼容组合在创建任务前拒绝。禁用算法只有显式确认后才可实验，且不得改变默认课程模型清单。

### 两线与课程模型范围

| 模型线 | 默认算法 | 数量与输入 |
|---|---|---|
| expert | `lr / rf / xgb / lgbm / et / svm / mlp_deep / tabnet` | 8 个，`feature_set=kamei14`（Kamei 14 维变更度量） |
| semantic | 同八算法 | 8 个，`feature_set=codebert768`（冻结头 CodeBERT 768 维） |

合计 16 个默认启用模型。注册表另登记 `nb/dt/knn/mlp` 为默认不训（每线 12 个，共 24 注册 / 16 启用），`algorithm.family` 区分经典机器学习与神经网络（深度学习）两类；启用模型含 6 种经典（lr/rf/xgb/lgbm/et/svm）与 2 种深度（mlp_deep/tabnet），满足课程「至少 2 类、不少于 8 种」硬要求。`feature_set` 必须与 `line` 兼容（`expert`↔`kamei14`、`semantic`↔`codebert768`）；`codebert768` 内部编码失败或绑定来源不可用时 run 前置返回 40001，不伪造向量。

**划分方式用户可配置**：`split.mode=random`（默认，按 `seed` 固定随机划分）或 `split.mode=time_order`（按时间序前 70%/后 30%，保留「测试集最早时间 > 训练集最晚时间」断言）。默认比例 70/30，`seed` 默认 42。随机切分不再被禁止；非法 mode、越界比例或 `time_order` 下边界断言失败返回 40001。

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 模型包 | 每个成功算法一个 `train_<algo>_model_package_<job_id>.zip`；内容严格遵循 §3.3：权重（`.pkl`）、`feature_order.txt`、`feature_schema.json`、`model_meta.json`、`checksum.sha256` |
| 测试集 | `train_testset_<job_id>.csv/xlsx`：§3.3 定义的切分测试集，schema 同 §3.2 `clean_dataset` 且每行带非空真标签，供板块 ⑤ 作为预测输入 |
| 训练日志 | `train_log_<job_id>.md`：逐算法开始、结束、耗时和脱敏错误，失败子项不伪装成功 |
| manifest | 每个产物伴同名 `train_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录输入、配置、划分 mode/比例/时间边界、种子、测试集行数与 checksum |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`。`model_meta.json` 必须含模型名、线、算法、`feature_set`、version_key、特征版本、训练时间、超参、划分（mode + 比例/边界）和种子；`feature_schema.json` 记录字段名、类型、来源、版本和训练侧变换。predict/explain 加载前必须校验包 checksum 与特征列宽。

**不产出性能指标**：AUC/F1 等指标、混淆矩阵、多模型排序与对比图一律不属本模块产物，归板块 ⑥ 预测性能评估。选多个算法只为产出多个模型包供 ⑥ 对比，④ 本身不判断性能。训练集只用于拟合、不落交换文件；对外 handoff 的只有模型包与测试集。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| 算法、family、启停和超参 schema | `algorithm` 表 | 表驱动；API 表单和 CLI 校验共用同一元数据 |
| `train.templates` | `user_config` 命名空间键 | 保存模型线、算法、超参、划分、种子等模板，重启恢复 |
| `feature_set` | run 配置 | 按模型线选择特征集；特征生成在训练内部完成，不接收外部特征来源 |
| 训练侧特征变换 | run 配置 | `log_transform` / `standardize` / `categorical_encode` / `feature_select`，只在训练集拟合 |
| 划分方式 / 比例 / 时间边界 | run 配置 | `split.mode=random`（默认）或 `time_order`；默认 70/30；`time_order` 保留边界断言 |
| `seed` / 早停等算法参数 | run 配置 + 算法 schema | 默认 42 / 各算法登记值，完整入模型元信息 |
| `auto_register` / `auto_load` | run 配置 | 默认 false / false；auto_load 仅热加载本任务自产 expert 权重，通用工件加载属 W6 |

## 6 状态持久化

- 训练创建 `job.kind=train`，使用统一五态；job 保存入参、子项状态、当前算法、日志、输出引用与重试次数。同 kind 互斥，重启遗留 running 置 failed。
- 多算法逐项提交产物：单项失败只记录该子项，其他成功算法正常交付；任何失败都不能覆盖已有可用模型。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore。模型包先完成 checksum 与结构校验，才可标记可用或登记 `model_artifact`；`model` 行由工件派生。
- `train.templates` 落 `user_config` 并重启恢复；每次运行固化模板版本、算法元数据版本、数据/特征版本、代码版本和超参快照。
- 新包可由 predict 通过事件、轮询或显式 load 在不重启服务的情况下加载；训练模块本身不修改 predict 的运行时状态。

## 7 与其他模块边界

- 与 clean 的关系仅为 §3.2 schema 兼容；clean 不生成模型特征，train 在内部按 `feature_set` 生成并固化模型特征，不要求 clean 服务在线，也不从 run 入参接收特征文件/仓库路径。
- 与 predict/explain 的交付物是 §3.3 模型包，不是硬编码权重路径或内存对象；登记和自动加载都是可选编排。
- `algorithm` 表属于配置与资产元数据，不是训练数据总线；独立 CLI 可使用同一注册信息的快照完成校验和训练。

## 8 验收标准

fixtures 为测试内联合成的 AI 生成未审核小型数据与算法配置；不上传 collect 产物、不预置预测结果也能完成 CLI/API 独立训练。CLI 不执行 register/auto_load（仅 API 提供）。

- 选择一个输入文件、两个兼容算法并分别设置超参后可运行；不兼容组合、超参越界和非法划分配置在创建期拒绝。
- 两种划分模式（`random` / `time_order`）均可运行；同 seed 的随机划分可复现，`time_order` 下边界断言生效。
- 两算法一败一成时成功项模型包可下载，失败项有原因且旧模型不变；任务取消、重试、互斥和重启中断测试通过。
- 模型包逐项校验 §3.3 内容、checksum、特征顺序和元信息；predict fixture 能直接加载新包，无需重启。
- 切分产出带真标签的 `train_testset`（每行 `is_bug_inducing` 非空），无标签行不进入测试集；测试集 schema 与 §3.2 一致，可被板块 ⑤ 直接作为预测输入。
- 两线 16 模型清单满足课程类别和数量要求；性能指标与多模型排序由板块 ⑥ 完成，④ 不产出指标或对比图。
- 承接 TODO/04：算法多选、动态超参、训练状态、失败隔离、切分测试集、模型登记、热加载和前端交互均有自动化测试；CLI/API 同配置结果一致。
