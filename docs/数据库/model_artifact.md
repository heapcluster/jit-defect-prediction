# model_artifact

## 用途

模型文件登记：文件路径、框架、格式、校验和、大小与训练任务关联。一个 `model` 对应一条 artifact 记录。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `artifact_id` | CHAR(36) | 否 | — | 主键 |
| `model_name` | VARCHAR(64) | 否 | — | 对应 `model.model_name`，唯一 |
| `line` | VARCHAR(16) | 否 | — | `expert` / `semantic` |
| `algo` | VARCHAR(64) | 是 | NULL | 算法标识 |
| `framework` | VARCHAR(16) | 否 | `sklearn` | `sklearn` / `pytorch` |
| `format` | VARCHAR(8) | 否 | `pkl` | `pkl` / `pt` |
| `version_key` | VARCHAR(64) | 否 | `''` | 版本键；训练模型为 `job_id`，导入模型为 `model_ref` |
| `weight_path` | VARCHAR(255) | 否 | — | 模型文件相对仓库根目录的路径，扩展名与 `format` 一致 |
| `checksum_sha256` | CHAR(64) | 否 | — | 文件校验和 |
| `size_bytes` | BIGINT | 否 | 0 | 文件大小 |
| `feature_version` | VARCHAR(32) | 是 | NULL | 特征版本，取值见 `约束/enums.md` |
| `train_job_id` | CHAR(36) | 是 | NULL | 产出该模型的任务 |
| `status` | VARCHAR(16) | 否 | `available` | `available` / `missing` |
| `trained_at` | DATETIME | 是 | NULL | 训练完成时间 |
| `created_at` | DATETIME | 否 | — | 登记时间 |

## 文件载体

- `framework=sklearn`、`format=pkl`：`lr`、`dt`、`rf`、`et`、`ada`、`gbdt`、`xgb`、`lgbm`、`svm`、`knn`、`mlp`。用 joblib 保存完整 Pipeline（预处理 + 模型）。
- `framework=pytorch`、`format=pt`：`dnn`、`tabnet`。单个 `.pt` 文件内保存字典：格式标记 `jit-pt-v1`、`state_dict`、`algo`、`line`、超参、特征顺序、特征版本与预处理 Pipeline。导入时自包含，不依赖同名附属文件。
- `format` 与 `framework` 必须匹配：`sklearn` 只能是 `pkl`，`pytorch` 只能是 `pt`。
- 导入模型：`.pt` 以文件内 `line` / `algo` / `feature_version` 为准，与请求不一致返回 `40001`；`.pkl` 无法读取 `feature_version` 时置 NULL，按声明模型线做特征数校验。

## 约束与索引

- 主键 `artifact_id`；`model_name` 唯一。
- 外键 `model_name` → `model.model_name`（`ON DELETE CASCADE`）；`train_job_id` → `job.job_id`。
- 索引：`ix_artifact_line (line)`。
- 文件缺失时置 `status=missing`，不自动删除记录；预测加载前校验 `status` 与 `sha256`。
- 下载扩展名由 `format` 决定，不统一为 `.pkl`。

## 删除语义

- 随 `model` 删除而删除，不单独提供删除入口。
- 删除前确认文件路径归属当前用户，不跨用户删除文件。

## 读写方

- 写入：`POST /api/train/save`、`POST /api/predict/save-model`。
- 读取：预测页加载模型、数据存储页模型文件下载、评估页历史详情。
- 校验：`sha256` 与文件大小比对，不一致时标记 `missing`。
