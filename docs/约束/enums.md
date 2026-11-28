# 枚举与值域

本文件是全系统枚举取值的唯一真源；其它文档只引用，不重复列值。

## 1 用户

| 枚举 | 取值 |
|---|---|
| 用户状态 `user.status` | `active` / `disabled` |

## 2 任务

| 枚举 | 取值 |
|---|---|
| 任务类型 `job.kind` | `collect` / `clean` / `train` / `predict` / `evaluate` |
| 任务状态 `job.status` | `queued` / `running` / `success` / `failed` / `cancelled` |
| 预估档位 `warn_level` | `none` / `yellow` / `red` |

## 3 数据集

| 枚举 | 取值 |
|---|---|
| 模型线 `dataset.line` | `expert` / `semantic` |
| 来源类型 `dataset.source_type` | `git_repo` / `upload` / `clean` / `split` / `prediction` |
| 数据集状态 `dataset.status` | `ready` / `failed` |
| 平台 `platform` | `github` / `gitee` |
| 上传角色 `role` | `data` / `model` |
| 特征版本 `feature_version` | `kamei14-v1`（专家线） / `codebert768-v1`（语义线） |

- 特征口径或列顺序变更时递增版本号；同一版本内字段顺序固定，跨版本数据不得混训。
- `clean` / `split` 继承父数据集版本；`prediction` 取输入数据集或模型的特征版本。

## 4 清洗

| 枚举 | 取值 |
|---|---|
| 操作 `op` | `dedup` / `missing` / `outlier` / `label` / `balance` |
| 去重键 | `full`（完全重复行） / `commit_hash` |
| 缺失值方式 | `drop` / `mean` / `mode` |
| 异常值方式 | `iqr_clip` / `iqr_drop` |
| 平衡方式 | `under`（只提供欠采样） |

- `missing` 使用 `mean` 时目标列必须是数值列，使用 `mode` 时目标列必须是类别列。
- 语义线只允许把元数据列与 `bug` 作为目标列。

## 5 导出

| 枚举 | 取值 |
|---|---|
| 导出格式 | `csv` / `excel` |

## 6 页面

| 枚举 | 取值 |
|---|---|
| 页面进度 `user_page_state.page` | `collect` / `clean` / `train` / `predict` / `evaluate` / `storage` |

## 7 配置键

| 键 | 类型 | 默认 |
|---|---|---|
| `estimate_warn_minutes` | 正整数 | 10 |
| `estimate_danger_minutes` | 正整数 | 30 |

## 8 模型

| 枚举 | 取值 |
|---|---|
| 模型文件状态 `model_artifact.status` | `available` / `missing` |
| 模型框架 `model_artifact.framework` | `sklearn` / `pytorch` |
| 模型文件格式 `model_artifact.format` | `pkl` / `pt` |

- `framework=sklearn` 只允许 `format=pkl`；`framework=pytorch` 只允许 `format=pt`。

## 9 算法

| 枚举 | 取值 |
|---|---|
| 算法类别 `algorithm.family` | `linear` / `tree` / `ensemble` / `boosting` / `svm` / `neighbor` / `neural` |

## 10 预测

| 枚举 | 取值 |
|---|---|
| 解释技术 `technique` | `shap` / `lime` / `permutation` |
| 预测标签 `predicted_label` | `0` 正常 / `1` 缺陷 |

## 11 评估

| 枚举 | 取值 |
|---|---|
| 评估来源 `evaluation.source_kind` | `dataset` / `file` |
| 评估图类型 `evaluation_figure.figure_type` | `roc` / `pr` / `confusion` / `bar` |
| 评估指标 | `accuracy` / `precision` / `recall` / `f1` / `auc` / `ap` / `mcc` |
