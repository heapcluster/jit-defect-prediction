# 模型训练（功能 4）

实现状态：已实现　期次：一期

## 一句话概述

独立的模型训练工具：上传清洗数据并按 `algorithm` 表驱动的模型线、算法和超参执行多算法训练，隔离单项失败，交付可校验、可复现的 `model_package.zip` 与比较报告。

## 1 职责与不负责范围

**负责**：

- 接收 `cleaned.csv`、模型线、一个或多个算法、超参、时间序划分和随机种子，复用四线训练实现生成模型。
- 从 `algorithm` 表读取算法启停、模型族和超参 schema，提供动态配置校验与训练模板；不在前端或请求处理代码写死算法清单。
- 一次任务内逐算法执行并隔离失败，保存子项状态、日志、基础指标和多模型比较结果。
- 为每个成功算法生成带权重、特征顺序、元信息和 checksum 的模型包；可选登记资产并通知 predict 加载。

**不负责**：

- 数据采集、清洗、在线预测、模型运行时管理、XAI 或行级定位。
- 另写指标公式；训练摘要和比较指标统一调用 evaluate 的 `data_model/evaluation/metrics.py`。
- 新算法研究、特征重设计、AutoML、分布式/GPU 集群调度或 CI 门禁执行。

## 2 独立运行入口

```bash
python -m pipelines.train run \
  --input cleaned.csv --line expert --algos lr,rf \
  --hyperparams hp.json --split-ratio 0.7 --seed 42 --out ./out
python -m pipelines.train algorithms --line expert
python -m pipelines.train compare --job <job_id>
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python -m pipelines.train run/algorithms/compare` | 输入文件与配置即可训练；算法注册信息来自同一算法元数据源 |
| 算法 API | `GET /api/algorithms` | 查询 `algorithm` 表中的模型线、算法、family、启停和超参 schema |
| 任务 API | `POST /api/train/run` | multipart 上传 CSV/XLSX 与训练配置，返回 `job_id`；可选 `dataset_id` 仅作便利输入 |
| 比较 API | `GET /api/train/compare?job_id=<id>` | 返回逐算法状态、指标与排序，不重新训练 |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 五态、子项进度、日志、取消与重试 |
| 下载 | `GET /api/train/outputs/{job_id}/{name}` | 下载模型包、指标、比较图与 manifest |

所有 HTTP 端点（含工件和图片下载）必须使用 `X-API-Key`。Web 训练页只组装配置和展示结果，不实现训练或指标计算。

## 3 输入契约

- 主输入遵循 [`../file-contracts.md`](../file-contracts.md) §3.2 `cleaned.csv`；需要提交原文或变更文本的模型线可同时接收 §3.1 `commits.csv`。Kamei 列序、标签空值和时间序语义不得修改。可选 `dataset_id` 只用于选择已导入的等价输入文件。
- 本次训练配置包括 `line`、`algos[]`、逐算法 `hyperparams`、`split`、`seed`、训练决策阈值、`auto_register`、`auto_load` 和 `template_id`；完整配置进入 job 与 manifest。
- `(line, algo)` 必须在算法元数据中登记，超参按 schema 校验类型、范围与枚举；不兼容组合在创建任务前拒绝。禁用算法只有显式确认后才可实验，且不得改变默认课程模型清单。

### 四线与课程模型范围

| 模型线 | 默认算法 | 数量与输入 |
|---|---|---|
| expert | `lr / rf / xgb / lgbm / et / svm / mlp_deep / tabnet` | 8 个，使用专家特征 |
| semantic | 同八算法 | 8 个，使用语义特征 |
| fused | 同八算法 | 8 个，使用融合特征 |
| e2e | `codebert_e2e` | 1 个，使用端到端文本 |

合计 25 个默认启用模型。注册表另登记 `nb/dt/knn/mlp` 为默认不训（每线 12 个，共 37 注册 / 25 启用），`algorithm.family` 区分经典机器学习与神经网络（深度学习）两类。semantic/fused/e2e 所需嵌入向量或文本数据集不在当前表格上传契约内，run 前置返回 40001，不伪造向量或文本；expert 线可由 §3.1/§3.2 表格完整训练。划分默认时间序前 70%/后 30%，禁止随机，保留测试集最早时间晚于训练集最晚时间的断言。

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 模型包 | 每个成功算法一个 `train_<algo>_model_package_<job_id>.zip`；内容严格遵循 §3.3：权重、`feature_order.txt`、`model_meta.json`、`checksum.sha256` |
| 训练指标 | `train_metrics_<job_id>.csv`，采用 §3.6 metrics 长表 schema；默认阈值下记录逐模型指标 |
| 多模型比较 | `train_comparison_<job_id>.json`：模型线、算法、超参摘要、特征/数据版本、指标、子项状态和排序 |
| 对比图 | `train_roc_<job_id>.png`、`train_pr_<job_id>.png`、`train_confusion_<job_id>.png`、`train_metric_bars_<job_id>.png` |
| 训练日志 | `train_log_<job_id>.md`：逐算法开始、结束、耗时和脱敏错误，失败子项不伪装成功 |
| manifest | 每个产物伴同名 `train_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录输入、配置、种子、代码版本和 checksum |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`。`model_meta.json` 必须含模型名、线、算法、version_key、特征版本、训练时间、超参、划分和种子；predict/explain 加载前必须校验包 checksum 与特征列宽。基础指标默认 0.5 时与历史 `model_metrics.csv` 同口径，数值容差 1e-6。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| 算法、family、启停和超参 schema | `algorithm` 表 | 表驱动；API 表单和 CLI 校验共用同一元数据 |
| `train.templates` | `user_config` 命名空间键 | 保存模型线、算法、超参、划分、种子等模板，重启恢复 |
| 划分比例或时间边界 | run 配置 | 默认 70/30，禁止随机，时间边界断言不可移除 |
| `seed` / 早停等算法参数 | run 配置 + 算法 schema | 默认 42 / 各算法登记值，完整入模型元信息 |
| 训练决策阈值 | run 配置或 `decision_threshold` | 默认 0.5；与风险展示阈值分键 |
| `auto_register` / `auto_load` | run 配置 | 默认 false / false；auto_load 仅热加载本任务自产 expert 权重，通用工件加载属 W6 |
| `primary_metric` / `metrics_selected` | `user_config` 全局键 | 控制比较排序和摘要指标，不复制指标公式 |

## 6 状态持久化

- 训练创建 `job.kind=train`，使用统一五态；job 保存入参、子项状态、当前算法、日志、输出引用与重试次数。同 kind 互斥，重启遗留 running 置 failed。
- 多算法逐项提交产物：单项失败只记录该子项，其他成功算法正常交付；任何失败都不能覆盖已有可用模型。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore。模型包先完成 checksum 与结构校验，才可标记可用或登记 `model_artifact`；`model` 行由工件派生。
- `train.templates` 落 `user_config` 并重启恢复；每次运行固化模板版本、算法元数据版本、数据/特征版本、代码版本和超参快照。
- 新包可由 predict 通过事件、轮询或显式 load 在不重启服务的情况下加载；训练模块本身不修改 predict 的运行时状态。

## 7 与其他模块边界

- 与 clean 的关系仅为 §3.2 schema 兼容；也可直接接收符合 §3.1 且满足所选模型线需要的训练文件，不要求 clean 服务在线。
- 与 predict/explain 的交付物是 §3.3 模型包，不是硬编码权重路径或内存对象；登记和自动加载都是可选编排。
- `algorithm` 表属于配置与资产元数据，不是训练数据总线；独立 CLI 可使用同一注册信息的快照完成校验和训练。
- 指标计算唯一来源为 evaluate 的 `data_model/evaluation/metrics.py`，训练页不自行实现第二套公式。

## 8 验收标准

fixtures 为测试内联合成的 AI 生成未审核小型数据与算法配置；不上传 collect 产物、不预置预测结果也能完成 CLI/API 独立训练。CLI 不执行 register/auto_load（仅 API 提供）。

- 选择一个输入文件、两个兼容算法并分别设置超参后可运行；不兼容组合、超参越界和随机切分在创建期拒绝。
- 两算法一败一成时成功项模型包可下载，失败项有原因且旧模型不变；任务取消、重试、互斥和重启中断测试通过。
- 模型包逐项校验 §3.3 内容、checksum、特征顺序和元信息；predict fixture 能直接加载新包，无需重启。
- 多模型指标可按 AUC/F1 排序，ROC/PR/混淆/柱状图齐全；默认 0.5 与历史指标逐值一致（1e-6），四线 25 模型清单满足课程类别和数量要求。
- 承接 TODO/04：算法多选、动态超参、训练状态、失败隔离、模型登记、热加载、多模型比较和前端交互均有自动化测试；CLI/API 同配置结果一致。
