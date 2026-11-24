# 预测性能评估（功能 6）

实现状态：已实现　期次：一期

## 一句话概述

独立的评估工具台：上传 predictions 与可选 labels、可选 effort 来源（§3.1 commits / §3.2 cleaned，按 la/ld 还原真实 LOC），按阈值和指标配置计算数值、混淆矩阵、两类 effort 图及报告，不训练模型、不改变预测概率，也不要求库中已有记录。

## 1 职责与不负责范围

**负责**：

- 对一个或多个模型的预测文件与真实标签执行独立评估，支持阈值、指标组合、主排序指标和报告格式配置。
- 以新增的 `data_model/evaluation/metrics.py` 为所有基础与 effort-aware 指标公式单源，供 train 和 Web 共同复用。
- 产出指标长表、混淆矩阵、多模型比较、ROC/PR/校准/effort 等图和带不可用原因的报告。
- 保留默认 0.5 下与历史 `model_metrics.csv` 的逐值一致性验收线，自定义阈值只影响依赖阈值的指标。

**不负责**：

- 训练、预测、修改风险概率、解释质量评价或 CI 门禁。
- 把历史静态 CSV 当作计算服务，或在前端、后端、四线脚本中各写一套指标公式。
- 以标签缺失、样本不足等理由伪造 0 或空白数值；这些情况必须显式报告。

## 2 独立运行入口

```bash
python -m evaluation.evaluate run \
  --predictions predictions.csv --labels labels.csv \
  --threshold 0.5 --metrics auc,ap,f1,precision,recall,accuracy,popt \
  --primary-metric auc --format md --out ./out
python -m evaluation.evaluate metrics
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python -m evaluation.evaluate run/metrics` | 文件和评估配置即可运行，与 API 共用指标与绘图内核 |
| 指标 API | `GET /api/evaluate/metrics` | 返回指标键、说明、公式标识、是否依赖阈值和 effort 类型 |
| 任务 API | `POST /api/evaluate/run` | multipart 上传 predictions + 可选 labels 与配置，返回 `kind=evaluate` 的 `job_id` |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 进度、日志、重试与取消 |
| 下载 | `GET /api/evaluate/outputs/{job_id}/{name}` | 下载指标、混淆、图、报告和 manifest |

所有 HTTP 端点（含图像和报告下载）必须使用 `X-API-Key`；图片由鉴权 fetch 转 ObjectURL。run 的可选 `dataset_id` 仅用于选择已导入的等价文件，不是计算前提。

## 3 输入契约

- 必需主输入遵循 [`../file-contracts.md`](../file-contracts.md) §3.4 `predictions.csv`；若其中没有可用真标签，必须同时提供 §3.5 `labels.csv`。两者按提交哈希连接，冲突以 labels 为准并把冲突数写入 manifest。
- 可选 `dataset_id` 只选择已导入的 predictions/labels 文件；无库记录时上传文件即可完成评估。筛选时间、模型列表等条件只作用于本次输入快照。
- 本次配置包括 `threshold`、`metrics[]`、`primary_metric`、`effort_enabled`、`report_format` 和图选项；阈值在开区间 (0,1)，主排序指标必须属于已选指标。
- 可选 §3.7 `explanations.csv` 用于汇总特征重要性图；未提供时报告该项不可用原因，不从 predictions 反推特征贡献。
- 未打标记录保持 NULL 并从有监督指标样本中排除，同时报告数量；缺预测行不得补 0。测试集口径可由输入筛选或 §3.1/§3.2 的划分标记确定，并在 manifest 固化。

### 一期指标清单

| 类型 | 指标 | 是否依赖判定阈值 |
|---|---|---|
| 排序/概率 | `auc / ap` | 否 |
| 基础分类 | `f1 / precision / recall / accuracy` | 是 |
| effort-aware | `recall_at_20 / recall_at_50 / p_norm / popt` | 否 |

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 指标 | `evaluate_metrics_<job_id>.csv`：严格采用 §3.6 metrics 长表 schema，逐模型逐指标一行 |
| 混淆矩阵 | `evaluate_confusion_<job_id>.csv`：严格采用 §3.6 confusion schema，随本次阈值计算 |
| 多模型比较 | `evaluate_comparison_<job_id>.json`：按主指标排序，附样本数、正样本率、阈值、数据与模型版本 |
| 基础图 | `evaluate_roc_<job_id>.png`、`evaluate_pr_<job_id>.png`、`evaluate_confusion_<job_id>.png`、`evaluate_calibration_<job_id>.png` |
| effort 两类图 | `evaluate_effort_unaware_<job_id>.png` 与 `evaluate_effort_aware_<job_id>.png` 均为硬性产物，覆盖课程要求的两类评估视图 |
| 特征重要性 | 提供 explanations 时产 `evaluate_feat_importance_<job_id>.png`；否则在报告记录不可用原因 |
| 报告 | `evaluate_report_<job_id>.md`，可选 `.html`；含指标表、混淆、图引用、筛选口径和不可用原因清单 |
| manifest | 每个产物伴同名 `evaluate_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录输入 checksum、标签冲突和完整配置 |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`。缺标签、无预测、样本不足或模型输入不兼容时，对相应指标写入明确的不可用原因，不产伪数值。唯一公式实现是 `data_model/evaluation/metrics.py`；默认阈值 0.5 下与历史 `model_metrics.csv` 对应值逐项一致，绝对容差 1e-6。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `decision_threshold` | `user_config` 全局键或 run 覆盖 | 默认 0.5；与风险展示阈值分键 |
| `metrics_selected` | `user_config` 全局键或 run 覆盖 | 默认 AUC/AP/F1/Precision/Recall/Accuracy |
| `primary_metric` | `user_config` 全局键或 run 覆盖 | 默认 `auc`，须属于本次指标集 |
| `effort_enabled` | `user_config` 全局键 | 默认 true；控制 effort 指标选择，不删除课程要求的两类图留证 |
| `risk_high_threshold` / `risk_mid_threshold` | `user_config` 全局键 | 仅供风险展示页，不参与性能公式 |
| 报告格式与图选项 | run 配置 | Markdown 默认，可选 HTML；图选项不得绕过两类 effort 硬要求 |
| `default_dataset` | `user_config` 全局键 | 仅作输入下拉默认选项 |

配置写入 `user_config` 后重启保持；每次 run 的配置快照与版本进入 job 和 manifest，后续修改全局配置不改写历史报告。

## 6 状态持久化

- 评估创建 `job.kind=evaluate`，使用统一五态，持久化输入引用、配置、进度、错误日志和输出引用；同 kind 互斥，重启遗留 running 置 failed。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；所有报告与图均可脱离数据库重新下载和复核。
- 全局阈值与指标配置由 `user_config` 持久化并重启恢复；历史评估固化配置、输入 checksum、样本范围、模型/特征版本与公式代码版本。
- 缓存键至少包含输入 checksum、模型版本、阈值和指标集合；任一变化即重新计算相应结果，缓存不得覆盖新版本。
- 可选导入 storage 只登记图和展示索引；指标文件、报告和 manifest 仍是权威交付物。

## 7 与其他模块边界

- 与 predict 只要求 §3.4 文件兼容，与 collect/clean 只通过标签文件或预测内标签兼容；predict 服务不在场也能评估。
- train 调用同一指标单源生成训练摘要，但 evaluate 不依赖 train 任务记录；多模型比较由输入文件内模型标识区分。
- 原模型性能页面承担的指标、混淆、图与报告计算职责全部归本模块；趋势展示只读 storage 中已导入的提交与预测，不另算性能指标。
- storage 提供可选展示导入和配置/任务持久化，不作为评估的数据前置；CI 阈值门禁归 extension。

## 8 验收标准

fixtures 位于 `tests/fixtures/files/evaluate/`，含正常、边界、非法三类 predictions/labels；在无 predict 服务、空库环境中，CLI 与 API 各完成一次评估并逐列断言 §3.6 输出。

- 修改阈值后，F1/Precision/Recall/Accuracy 与混淆矩阵按新阈值计算，AUC/AP 不被篡改；多指标勾选与主排序生效。
- 两个及以上模型可在同一比较结果中排序；报告包含样本数、正样本率、阈值、数据/模型版本和计算时间。
- 默认 0.5 下与历史 `model_metrics.csv` 逐值一致（1e-6）；公式单元测试证明 train/evaluate 共用 `data_model/evaluation/metrics.py`。
- effort-unaware 与 effort-aware 两类图各至少一张且数据可复算；ROC/PR/混淆/校准图与报告引用完整。
- 缺标签、无预测、样本不足、未知指标、阈值越界和标签冲突均有明确语义；NULL 不当 0，缺行不补 0，失败不留半成品。
- 承接 TODO/06：阈值、指标、多模型比较、配置重启恢复、恢复默认值和异常场景均有测试；配置保存后重新启动仍保持。
