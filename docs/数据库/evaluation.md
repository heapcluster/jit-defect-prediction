# evaluation

## 用途

一次预测性能评估的登记。记录输入来源、阈值、所选指标与样本统计；只进入评估页的历史，不属于数据存储页资产。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `evaluation_id` | CHAR(36) | 否 | — | 主键 |
| `owner_user_id` | CHAR(36) | 否 | — | 归属用户 |
| `name` | VARCHAR(128) | 否 | — | 评估名称，用户可改 |
| `source_kind` | VARCHAR(16) | 否 | — | `dataset` / `file` |
| `source_label` | VARCHAR(255) | 否 | — | 来源展示名：数据集名或导入文件显示名 |
| `dataset_id` | CHAR(36) | 是 | NULL | 来源预测结果数据集；文件来源为空 |
| `model_name` | VARCHAR(64) | 是 | NULL | 关联模型；外部文件或模型已删除时为空 |
| `model_label` | VARCHAR(128) | 是 | NULL | 模型展示名；来源为外部文件时为空，模型删除后保留 |
| `threshold` | DECIMAL(4, 3) | 否 | 0.500 | 本次评估使用的分类阈值 |
| `metrics_json` | JSON | 否 | — | 所选指标及值，如 `{"auc":0.93,"f1":0.82}` |
| `sample_count` | INT | 否 | 0 | 参与评估的样本数 |
| `pos_count` | INT | 否 | 0 | 真实正样本数 |
| `neg_count` | INT | 否 | 0 | 真实负样本数 |
| `created_at` | DATETIME | 否 | — | 生成时间 |

## 约束与索引

- 主键 `evaluation_id`。
- 外键 `owner_user_id` → `user.user_id`；`dataset_id` → `dataset.dataset_id`（`ON DELETE SET NULL`）；`model_name` → `model.model_name`（`ON DELETE SET NULL`）。
- 索引 `ix_evaluation_user_created (owner_user_id, created_at)`；唯一键 `uq_evaluation_user_name (owner_user_id, name)`。
- `metrics_json` 只保存所选指标；未选择的指标不写键。

## 删除语义

- 独立删除；删除后同事务删除其 `evaluation_figure` 行与图片文件。
- 删除不影响来源预测结果数据集、模型或其他评估记录。
- 来源数据集或模型被删除时，本表对应字段置空，`model_label` 与历史指标、图片保留。

## 读写方

- 写入：`POST /api/evaluate/save`。
- 读取：评估页历史列表、历史详情、指标表导出（`GET /api/evaluate/history/{evaluation_id}/export`）。
