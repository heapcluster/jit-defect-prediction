# prediction

## 用途

预测明细。每一行是一次预测任务中「提交 × 模型」的结果，归属于一条 `source_type=prediction` 的数据集资产。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `dataset_id` | CHAR(36) | 否 | — | 预测数据集，主键之一 |
| `commit_hash` | CHAR(40) | 否 | — | 提交哈希，主键之一 |
| `commit_id` | CHAR(36) | 是 | NULL | 关联 `commit.commit_id`；新写入必须补齐 |
| `model_name` | VARCHAR(64) | 是 | NULL | 已保存模型；导入模型未保存时为 NULL |
| `model_label` | VARCHAR(128) | 是 | NULL | 模型展示名，导入模型必填 |
| `risk_score` | DECIMAL(6, 5) | 否 | — | 缺陷概率，0–1 |
| `predicted_label` | TINYINT | 否 | — | 0 正常 / 1 缺陷 |
| `threshold` | DECIMAL(4, 3) | 否 | 0.500 | 本次预测使用的概率阈值 |
| `actual_label` | TINYINT | 是 | NULL | 输入数据自带的 `bug` 值，无标签时为 NULL |
| `feature_version` | VARCHAR(32) | 是 | NULL | 输入数据集或模型的特征版本 |
| `predicted_at` | DATETIME | 否 | — | 预测时间 |

## 约束与索引

- 主键 `(dataset_id, commit_hash)`；同一模型对同一提交在不同预测中分别保留。
- 外键 `dataset_id` → `dataset.dataset_id`（`ON DELETE CASCADE`）；`commit_id` → `commit.commit_id`（`ON DELETE SET NULL`）；`model_name` → `model.model_name`（`ON DELETE SET NULL`，可空）。
- 索引：`ix_prediction_model (model_name)`、`ix_prediction_dataset (dataset_id)`。
- `commit_id` 允许为空，只为兼容历史或异常数据；正常保存时按输入行的 `project` + `commit_hash` 幂等补齐 `commit` 行并写入；同一预测数据集只允许一个 `project`。不建立 `commit_hash` 外键。
- `model_label` 与 `actual_label` 为展示用冗余：模型被删除后仍可显示原名，输入自带标签时保留真值。

## 删除语义

- 随预测数据集删除；不单独提供删除入口。
- 删除预测数据集时，同事务删除其全部 `prediction` 行与结果文件。
- 模型删除不影响预测结果：`model_name` 置空，`model_label` 保留，解释不可再用。

## 读写方

- 写入：`POST /api/predict/save`。
- 读取：`GET /api/predict/results/{job_id}/rows`、数据存储页预测数据集抽屉、详情页、后续评估；提交说明、作者与提交时间通过 `commit_id` 关联 `commit` 获取。
- 已保存结果在临时目录清理后仍可读，不依赖任务产物文件。
