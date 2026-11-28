# 接口 evaluate

输入格式见 [../功能点/06-预测性能评估.md](../功能点/06-预测性能评估.md) 第 2 节；指标与阈值见第 3 节；任务轮询与取消见 [conventions.md](./conventions.md)。

## 1 POST /api/evaluate/import

导入带标签的预测结果文件。

请求：`multipart/form-data`，字段 `file`、`label`（显示名，可空）。

- 文件落 `temp/uploads/<user_id>/<file_id>/`；页面重置或开始新评估时清理，只作本次输入。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "file_8f3a1c2d",
    "label": "外部预测结果",
    "line": "expert",
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "threshold": 0.5
  }
}
```

- 表头必须为原始数据集列（含 `bug`）+ `risk_score`、`predicted_label`、`threshold`。
- `bug` 必须全为 0 / 1；存在空值或其他取值时拒绝。
- `threshold` 为文件中的记录值；多值混合时返回 `null`，评估仍以页面设置为准。

错误：`40001` 未选择文件、`41301` 超过 100MB、`42201` 缺列/多列/列序不符、标签非法、提交哈希重复、非 40 位小写十六进制或出现多个 `project`（`data.mismatch` / `data.invalid_rows`）。

## 2 POST /api/evaluate/precheck

校验本人预测结果数据集。

```json
{ "dataset_id": "ds_..." }
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "line": "expert",
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "model_label": "expert-xgb-8f3a1c2d",
    "threshold": 0.5
  }
}
```

- 仅接受 `source_type=prediction` 且全部 `actual_label` 非空的数据集。
- `pos` / `neg` 为真实标签的正负样本数，不是预测结果的正负条数。
- `threshold` 为数据集中记录的预测阈值，仅供展示；评估阈值以请求参数为准。

错误：`40001` 非预测结果数据集、`40401` 不存在或不属于当前用户、`42201` 存在空标签（`data.invalid_rows`）。

## 3 POST /api/evaluate/run

```json
{
  "source": { "kind": "dataset", "id": "ds_..." },
  "metrics": ["accuracy", "precision", "recall", "f1", "auc", "ap"],
  "threshold": 0.5
}
```

- `source.kind` 取 `dataset` / `file`；`dataset` 时 `id=dataset_id`，`file` 时 `id=file_id`。
- `metrics` 至少 1 项，取值 `accuracy` / `precision` / `recall` / `f1` / `auc` / `ap` / `mcc`；`ap` 使用 `average_precision_score`，不是 PR 曲线面积积分。
- `threshold` 取 0–1，省略默认 `0.5`。

响应 `202`：

```json
{ "code": 0, "message": "ok", "data": { "job_id": "job_...", "total_figures": 4 } }
```

- 图表按勾选条件生成，`total_figures` 为实际生成数量：`bar` 始终生成；勾选 `auc` 才生成 `roc`；勾选 `ap` 才生成 `pr`；勾选 `accuracy` / `precision` / `recall` / `f1` / `mcc` 任一项才生成 `confusion`。
- 上例勾选了阈值类指标与 `auc` / `ap`，因此为 4 张。

错误：`40001` 指标为空或阈值越界、`42201` 单类别却请求 AUC / AP、`42901` 已有运行中任务。

## 4 GET /api/evaluate/results/{job_id}

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "threshold": 0.5,
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "metrics": {
      "accuracy": 0.91,
      "precision": 0.86,
      "recall": 0.79,
      "f1": 0.82,
      "auc": 0.93,
      "ap": 0.88,
      "mcc": 0.78
    },
    "figures": [
      { "type": "roc", "url": "/api/evaluate/results/job_.../figures/roc" },
      { "type": "pr", "url": "/api/evaluate/results/job_.../figures/pr" },
      { "type": "confusion", "url": "/api/evaluate/results/job_.../figures/confusion" },
      { "type": "bar", "url": "/api/evaluate/results/job_.../figures/bar" }
    ]
  }
}
```

- `metrics` 只返回本次勾选的指标。
- `figures` 只返回实际生成的图；示例为勾选阈值类指标与 `auc` / `ap` 的全量情况。

## 5 GET /api/evaluate/results/{job_id}/export

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名 |
| `format` | `csv` / `excel` |

- 每次评估导出为一行；列名为所选指标英文名，末尾追加 `threshold`。

## 6 GET /api/evaluate/results/{job_id}/figures/{figure_type}

- `figure_type` 取 `roc` / `pr` / `confusion` / `bar`。
- 返回 PNG 文件流；文件缺失返回 `40901`。

## 7 POST /api/evaluate/save

```json
{ "job_id": "job_...", "name": "evaluate-8f3a1c2d" }
```

```json
{ "code": 0, "message": "ok", "data": { "evaluation_id": "eva_..." } }
```

- 每次保存独立成条，不覆盖历史；名称长度 1–128，字符规则同数据集名称，同一用户内不可重名。
- 保存指标、阈值、样本统计与图片文件。

错误：`40001` 名称为空、非法或超过 128 字符、`40401` 任务不存在、`40901` 名称重复或结果已失效。

## 8 GET /api/evaluate/history

| 参数 | 说明 |
|---|---|
| `q` | 名称关键字，可选 |
| `page` / `page_size` | 默认 1 / 20，最大 100 |

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "evaluation_id": "eva_...",
        "name": "evaluate-8f3a1c2d",
        "source_kind": "dataset",
        "source_label": "repo-test",
        "model_label": "expert-xgb-8f3a1c2d",
        "threshold": 0.5,
        "sample_count": 1200,
        "metrics": { "auc": 0.93, "f1": 0.82 },
        "created_at": "2026-11-27T10:00:00+08:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  }
}
```

- 列表按 `created_at` 倒序，同时间按 `evaluation_id` 升序。

## 9 GET /api/evaluate/history/{evaluation_id}

返回完整指标、样本统计与图片列表，结构同第 4 节，另含 `name`、`source_kind`、`source_label`、`model_label`、`created_at`。

- 非本人记录返回 `40401`。
- `figures` 的 `url` 指向第 10 节的历史图端点。

## 10 GET /api/evaluate/history/{evaluation_id}/figures/{figure_type}

- `figure_type` 取 `roc` / `pr` / `confusion` / `bar`。
- 返回已保存的 PNG 文件流；文件缺失返回 `40901`。
- 非本人记录返回 `40401`。

## 11 GET /api/evaluate/history/{evaluation_id}/export

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名 |
| `format` | `csv` / `excel` |

- 按保存的指标与阈值导出，列名规则同第 5 节。
- 非本人记录返回 `40401`。

## 12 DELETE /api/evaluate/history/{evaluation_id}

```json
{ "code": 0, "message": "ok", "data": { "deleted": true } }
```

- 独立删除；不影响预测结果数据集、模型或图片之外的任何资产。
- 非本人记录返回 `40401`。

## 13 页面进度

`GET/PUT /api/page-state/evaluate`，保存输入来源、指标、阈值与最近任务 `job_id`。
