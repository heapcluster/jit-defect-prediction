# model

## 用途

训练产出的模型登记，归属具体用户；记录模型线、算法、训练与测试数据集、超参与指标。模型文件本身在 `model_artifact`。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `model_name` | VARCHAR(64) | 否 | — | 主键；训练模型为 `{line}-{algo}-{job_id 去掉 job_ 前缀后的前 8 位}`，导入模型为 `{line}-{name}-{model_ref 后 8 位}` |
| `owner_user_id` | CHAR(36) | 否 | — | 归属用户 |
| `line` | VARCHAR(16) | 否 | `expert` | `expert` / `semantic` |
| `algo` | VARCHAR(64) | 是 | NULL | 算法标识，与 `algorithm.algo` 一致 |
| `version_key` | VARCHAR(64) | 否 | `''` | 版本键；训练模型为 `job_id`，导入模型为 `model_ref` |
| `train_dataset_id` | CHAR(36) | 是 | NULL | 训练数据来源数据集 |
| `test_dataset_id` | CHAR(36) | 是 | NULL | 对应测试集数据集 |
| `params_json` | TEXT | 是 | NULL | 训练时使用的超参 |
| `metrics_json` | TEXT | 是 | NULL | 指标快照，结构见下 |
| `trained_at` | DATETIME | 是 | NULL | 训练完成时间 |
| `feature_version` | VARCHAR(32) | 是 | NULL | 特征版本，取值见 `约束/enums.md` |

## 约束与索引

- 主键 `model_name`，全局唯一；命名由系统生成，用户不能直接指定完整名称。
- 外键 `owner_user_id` → `user.user_id`；`train_dataset_id`、`test_dataset_id` → `dataset.dataset_id`（`ON DELETE SET NULL`）。
- 索引：`ix_model_owner (owner_user_id)`、`ix_model_line (line)`。
- `metrics_json` 固定结构：`{"train": {...}, "valid": {...}}`，指标为 accuracy / precision / recall / f1 / auc / mcc，无法计算时为 `null`。

## 删除语义

- 独立删除；`model_artifact` 随模型删除；`prediction` 行与评估历史的 `model_name` 置空，但结果与历史保留。
- 允许删除时，同事务删除对应 `model_artifact` 记录与文件。

## 读写方

- 写入：`POST /api/train/save`、`POST /api/predict/save-model`（导入模型保存）。
- 读取：`GET /api/storage/files?type=model`（预测页模型下拉与数据存储页模型区）。
- 删除：`DELETE /api/models/{model_name}`（数据存储页触发）。
