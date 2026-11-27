## ADDED Requirements

### Requirement: 图集可按评估批次查询

`GET /api/figures` SHALL 接受 `model_name` 与 `job_id`，二者至少提供一个。只传 `job_id` 时返回该评估批次的图集，`batches[]` 仅含该批次；只传 `model_name` 时返回全部已登记批次并以最新批次填充 `figures[]`。

图类型 SHALL 为 `roc`、`pr`、`confusion`、`calibration`、`effort_unaware`、`effort_aware`、`feat_importance`；历史 `effort` 行读取时按 `effort_unaware` 展示，不迁移库。

每张图 SHALL 返回 `figure_name`，与图集 zip 内文件名、单独保存名一致。

#### Scenario: 按批次取图

- **WHEN** 前端携带 `model_name` 与 `job_id` 请求 `GET /api/figures`
- **THEN** 只返回该批次登记的图，`batches[]` 只包含该批次，`file_path` 指向 `/api/storage/outputs/{job_id}/{name}`

#### Scenario: 只传批次

- **WHEN** 请求只携带 `job_id`
- **THEN** 接口从已登记行推导模型名并返回图集与指标；批次对应多个模型时返回 40400

#### Scenario: 缺图不报错

- **WHEN** 某类型未登记或文件 checksum 不符
- **THEN** HTTP 200，缺失项进入 `missing[]`，不转成 500
