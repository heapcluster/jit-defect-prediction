# 模型图集 API（figures）

一句话：只读汇总某个模型或某次评估批次的指标、图文件登记与缺失原因，供模型性能页与评估页结果区渲染；不重算指标、不生成图、不写文件。

实现状态：已实现　期次：一期

## 1. 职责与不负责范围

- 负责按模型或评估批次读取指标快照与图登记，返回可直接用于展示的图路径、批次清单与缺失清单。
- 不负责重新计算指标、不重新生成 PNG、不修改 `model_figure`。
- 不把缺失图转换成 500，缺失通过 `missing[]` 表达。

历史 `model_figure` 中的 `effort` 行读取时按 `effort_unaware` 归一，不写库迁移；只传 `job_id` 时从登记行推导模型名。

## 2. 端点契约

### GET /api/figures

| 参数 | 必填 | 契约 |
|---|---|---|
| `model_name` | 条件必填 | 必须已登记；与 `job_id` 至少传一个 |
| `figure_type` | 否 | `roc/pr/confusion/calibration/effort_unaware/effort_aware/feat_importance`，其他 40001 |
| `job_id` | 条件必填 | 指定来源评估批次；与 `model_name` 至少传一个，可单独按批次查询图集 |

未知或重复 query → 40001。

响应：

```json
{
  "model_name": "...",
  "line": "expert",
  "source_job_id": "...",
  "batches": [{"job_id": "...", "created_at": "...", "testset_ref": "...", "figures_count": 6}],
  "metrics": [{"model_name": "...", "line": "expert", "metric": "auc", "value": 0.81, "threshold": 0.5, "n": 100, "pos_rate": 0.2, "dataset_version": "...", "model_version": "...", "computed_at": "..."}],
  "metrics_unavailable": null,
  "figures": [{"figure_type": "roc", "effort_kind": null, "title": "...", "figure_name": "evaluate_<job_id>_roc.png", "file_path": "/api/storage/outputs/{job_id}/{name}", "checksum_sha256": "...", "source_job_id": "..."}],
  "missing": [{"figure_type": "pr", "file_path": "...", "reason": "file_missing"}]
}
```

- 只传 `model_name` 时返回该模型全部已登记批次 `batches[]`，并以最新批次填充 `figures[]`；传 `job_id` 时只返回该批次，`batches[]` 仅含该批次。
- `metrics_unavailable` 取值：`evaluate_batch_missing`、`invalid_job_id`、`metrics_file_missing`、`metrics_checksum_mismatch`、`metrics_file_unreadable`、`metrics_schema_mismatch`、`model_metrics_missing`、`metrics_not_in_registry`。
- `missing[].reason`：`file_missing`、`checksum_mismatch`、`invalid_path`、`file_unreadable`、`invalid_png`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知/重复参数、`figure_type` 不在契约内、`model_name` 与 `job_id` 均缺失 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 模型或批次不存在、无任何图登记 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 无文件输入；数据来自 `model`、`model_figure` 与已导入的指标产物。
- `job_id` 对应评估任务批次，可单独用于定位该次评估的每张图；`model_name` 为模型维度过滤，并返回该模型的批次清单供模型性能页选择。

## 4. 输出契约

- `file_path` 对外改写为 `/api/storage/outputs/{job_id}/{name}`，页面需带 `X-API-Key` fetch 后转 ObjectURL。
- 每个 `(job_id, model_name, figure_type)` 至多一条登记；同模型不同批次的同类型图各自保留，不被覆盖；缺失项必须出现在 `missing[]`，不能静默省略。
- `figure_name` 为后端标准命名，与 zip 内文件名、文件夹保存名一致。
- 指标值来自已导入快照，不按当前阈值重算。

## 5. 可配置项

`risk_high_threshold` 等展示阈值不影响本接口的指标值；图来源由 evaluate / storage 导入时决定。

## 6. 状态持久化

- 只读，不写库、不创建 job、不落文件。
- 重新导入指标或图后立即可见；checksum 不符的图归入 `missing`。

## 7. 验收

- 有完整图集的模型或批次返回全部类型，`file_path` 可直接下载。
- 缺图返回 `missing` 且 HTTP 200。
- 非法 `figure_type`、未知参数、`model_name` 与 `job_id` 均缺失返回 40001；未登记模型或批次返回 40400。
- 同模型不同批次的同类型图不互相覆盖，可按 `job_id` 查询完整图集。
- 只传 `model_name` 返回批次清单，模型性能页可先选批次再取图。
- 本接口不触发任何计算。

## 8. 边界

figures 是展示读模型，图由 evaluate / storage 产生；它不参与训练、预测或评估的业务链路。
