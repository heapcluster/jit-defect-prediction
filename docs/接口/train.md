# 接口 train

字段契约见 [../功能点/02-数据收集.md](../功能点/02-数据收集.md) 第 4 节；训练口径见 [../功能点/04-模型训练.md](../功能点/04-模型训练.md)；任务轮询与取消见 [conventions.md](./conventions.md)。

## 1 POST /api/train/import

上传 CSV / Excel 并校验表头。文件只作输入，不登记为数据集。

请求：`multipart/form-data`，字段 `file`。

- 文件落 `temp/uploads/<user_id>/<file_id>/`；页面重置或开始新训练时清理，只作本次输入。

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "file_8f3a1c2d",
    "line": "expert",
    "columns": ["project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp", "bug"],
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "time_start": "2019-01-03T10:00:00+08:00",
    "time_end": "2022-11-20T18:30:00+08:00"
  }
}
```

错误：

| code | 场景 |
|---|---|
| 40001 | 未选择文件、扩展名不支持 |
| 41301 | 文件超过 100MB |
| 42201 | 表头与专家线、语义线均不匹配，或缺列、多列、列序不符；`data.mismatch` 给出第一处不符列；提交哈希重复、非 40 位小写十六进制或出现多个 `project` |

## 2 POST /api/train/precheck

校验本人已保存数据集并返回可训练信息与默认算法。

请求：

```json
{ "dataset_id": "ds_..." }
```

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "line": "expert",
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "time_start": "2019-01-03T10:00:00+08:00",
    "time_end": "2022-11-20T18:30:00+08:00",
    "suggested_ratios": { "train": 70, "valid": 15, "test": 15 },
    "algorithms": [
      { "algo": "xgb", "family": "boosting", "defaults": { "n_estimators": 300, "learning_rate": 0.1, "max_depth": 6 } }
    ]
  }
}
```

错误：`40001` 参数缺失、数据源为测试集或预测结果、`40401` 不存在或不属于当前用户、`42201` 缺少 `bug` 列或特征列不完整。

## 3 POST /api/train/run

启动训练任务。

请求：

```json
{
  "source": { "kind": "dataset", "id": "ds_..." },
  "algorithms": [
    { "algo": "xgb", "params": { "n_estimators": 300, "learning_rate": 0.1 } },
    { "algo": "rf", "params": { "n_estimators": 200 } }
  ],
  "split": { "mode": "time", "ratios": { "train": 70, "valid": 15, "test": 15 } }
}
```

- `source.kind` 取 `dataset` / `file`；`dataset` 时 `id=dataset_id`，`file` 时 `id=file_id`。
- `split.mode` 取 `time` / `random`；`random` 固定使用种子 `42`，请求不接受 `seed`。
- 时间序按 `commit_time` 升序、时间相同按 `commit_hash` 升序；训练 = `floor(n × train% / 100)`，验证 = `floor(n × valid% / 100)`，测试 = 剩余行。
- `algorithms` 至少 1 个，同一模型线，不得重复 `algo`；参数只接受 `数据库/algorithm.md` 登记的键。

响应 `202`：

```json
{ "code": 0, "message": "ok", "data": { "job_id": "job_...", "total": 2 } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | 算法为空或重复、比例非正、三比例之和不为 100、算法参数未知或类型不符 |
| 40901 | 数据源在预检后被修改或删除 |
| 42201 | 任一段缺少正样本或负样本 |
| 42901 | 当前用户已有运行中任务 |
| 50301 | 模型依赖不可用 |

## 4 GET /api/jobs/{job_id}

训练进度轮询，响应结构同 [../约束/job-state.md](../约束/job-state.md)；`current_stage` 为当前算法名，`total` 为算法数。

## 5 POST /api/jobs/{job_id}/cancel

取消训练。取消后本轮模型与测试集全部丢弃，不可保存。

## 6 GET /api/train/results/{job_id}

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "line": "expert",
    "split_counts": { "train": 840, "valid": 180, "test": 180 },
    "models": [
      {
        "model_name": "expert-xgb-8f3a1c2d",
        "algo": "xgb",
        "status": "success",
        "params": { "n_estimators": 300, "learning_rate": 0.1 },
        "metrics": {
          "train": { "accuracy": 0.91, "precision": 0.88, "recall": 0.84, "f1": 0.86, "auc": 0.93, "mcc": 0.71 },
          "valid": { "accuracy": 0.82, "precision": 0.79, "recall": 0.75, "f1": 0.77, "auc": 0.85, "mcc": 0.58 }
        },
        "framework": "sklearn",
        "format": "pkl",
        "file": { "name": "expert-xgb-8f3a1c2d.pkl", "size_bytes": 1048576, "sha256": "..." }
      }
    ],
    "failed": [],
    "test_set": { "name": "source-test-8f3a1c2d", "rows": 180, "pos": 27, "neg": 153, "file": "test.csv" }
  }
}
```

- `framework` / `format` 由算法决定：`lr`…`mlp` 为 `sklearn` / `pkl`，`dnn` / `tabnet` 为 `pytorch` / `pt`；`file.name` 的扩展名与 `format` 一致。
- 指标无法计算时返回 `null`，前端显示 `—`。
- 非本人任务返回 `40401`；未结束返回 `40901`。

## 7 POST /api/train/save

保存选中的模型与测试集。

请求：

```json
{ "job_id": "job_...", "model_names": ["expert-xgb-8f3a1c2d"], "save_test": true, "test_name": "repo-test-v1" }
```

响应：

```json
{ "code": 0, "message": "ok", "data": { "saved_models": ["expert-xgb-8f3a1c2d"], "test_dataset_id": "ds_..." } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | `model_names` 为空且 `save_test=false`；测试集名非法（长度 1–128，字符规则同数据集名称） |
| 40401 | 任务或模型不存在 |
| 40901 | 结果已被丢弃 |

- 模型写入 `model` 与 `model_artifact`，artifact 记录 `framework` 与 `format`：sklearn 算法为 `sklearn` / `pkl`，`dnn` / `tabnet` 为 `pytorch` / `pt`；测试集写入 `dataset`（`source_type=split`）与 `dataset_commit`。
- 重复调用幂等：已保存的模型不重复登记；测试集名称允许重复，每次保存独立成条。

## 8 GET /api/train/outputs/{job_id}/{name}

下载模型文件，扩展名由 `model_artifact.format` 决定（`.pkl` / `.pt`）。非本人任务返回 `40401`；结果已丢弃返回 `40901`。

## 9 GET /api/train/results/{job_id}/test-set/export

导出测试集二维表。

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名 |
| `format` | `csv` / `excel` |

- 列名与顺序按字段契约，与源数据集一致。
- 非本人任务返回 `40401`；结果已丢弃或未生成测试集返回 `40901`。

## 10 页面进度

`GET/PUT /api/page-state/train`，见 [page-state.md](./page-state.md)。保存数据源、算法与超参、切分配置与最近任务 `job_id`。
