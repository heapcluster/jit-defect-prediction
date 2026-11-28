# 接口 storage

数据存储页的资产、算法与配置端点。

## 1 GET /api/storage/files

当前用户已保存的数据集与模型。未保存的收集、清洗、训练结果不出现在此接口。

| 参数 | 说明 |
|---|---|
| `type` | `dataset` / `model`，可选 |
| `source_type` | 数据集来源：`git_repo` / `upload` / `clean` / `split` / `prediction`，可选 |
| `line` | 模型线：`expert` / `semantic`，可选；对数据集与模型都生效 |
| `status` | `ready` / `failed` / `available` / `missing`，可选 |
| `q` | 名称或任务编号关键字 |
| `page` / `page_size` | 分页，默认 1 / 20，最大 100 |

- 页面筛选中的「标签」对数据集对应 `source_type`，对模型对应 `line`；两者都通过本接口的对应参数过滤。
- `status=failed` 只用于异常或历史数据；正常保存的数据集为 `ready`。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "id": "ds_...", "type": "dataset", "name": "repo-main-expert", "badge": "git_repo", "source_job_id": "job_...", "created_at": "2026-11-27T10:00:00+08:00", "status": "ready" },
      { "id": "expert-xgb-8f3a1c2d", "type": "model", "name": "expert-xgb-8f3a1c2d", "badge": "expert", "source_job_id": "job_...", "created_at": "2026-11-27T10:00:00+08:00", "status": "available" }
    ],
    "total": 2,
    "page": 1,
    "page_size": 20
  }
}
```

- `badge`：数据集为 `source_type`，模型为模型线 `expert` / `semantic`。
- `total` 只统计数据集与模型，不统计未保存的产物。
- 列表按 `created_at` 倒序，同时间按 `id` 升序。

## 2 GET /api/storage/files/{id}/download

下载资产文件。

| 参数 | 说明 |
|---|---|
| `filename` | 数据集可填，不含扩展名；省略时用资产名 |
| `format` | 数据集取 `csv` / `excel`，默认 `csv`；模型忽略 |

- 数据集（非 prediction）：导出成员表，列名与顺序按字段契约。
- prediction 数据集：返回保存的结果表，导出列名使用外部契约 `commit_id`（Git 哈希），末尾含 `risk_score`、`predicted_label`、`threshold`。
- 模型：返回 `model_artifact.weight_path` 对应的模型文件，扩展名由 `format` 决定（`pkl` → `.pkl`，`pt` → `.pt`），不接受格式转换。
- 非本人资源返回 `40401`；模型文件缺失（`status=missing`）返回 `40901`。

## 3 GET /api/algorithms

系统只读算法清单。

| 参数 | 说明 |
|---|---|
| `line` | `expert` / `semantic`，可选 |
| `q` | 算法名关键字 |

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "line": "expert", "algo": "xgb", "family": "boosting", "enabled": true, "description": "梯度提升树",
        "defaults": { "n_estimators": 300, "learning_rate": 0.1, "max_depth": 6 } }
    ]
  }
}
```

- 清单由 [../数据库/algorithm.md](../数据库/algorithm.md) 固定定义，页面不可编辑。
- `defaults` 为 [../数据库/algorithm.md](../数据库/algorithm.md) 中的默认超参，训练页可直接作为初始值。

## 4 GET /api/config

当前用户配置。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": { "estimate_warn_minutes": 10, "estimate_danger_minutes": 30 },
    "updated_at": "2026-11-27T10:00:00+08:00"
  }
}
```

- 只返回已保存的配置；未保存项不出现。

## 5 PUT /api/config

保存当前用户配置。

```json
{ "items": { "estimate_warn_minutes": 15, "estimate_danger_minutes": 45 } }
```

- 只接受已登记的配置键；未知键返回 `40001`。
- 黄色阈值必须小于红色阈值，否则 `40001`。
- 保存后立即生效；响应返回写入后的完整配置。

## 6 DELETE /api/models/{model_name}

删除模型记录与模型文件（`.pkl` / `.pt`）。

- 删除后 `prediction.model_name` 与评估历史的 `model_name` 置空、`model_label` 保留；预测结果与评估历史不删除，解释不可再用。
- 非本人模型返回 `40401`。
- 成功返回 `{ "code": 0, "message": "ok", "data": { "deleted": true } }`。
