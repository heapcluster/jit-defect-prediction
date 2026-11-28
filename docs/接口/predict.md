# 接口 predict

字段契约见 [../功能点/02-数据收集.md](../功能点/02-数据收集.md) 第 4 节；结果口径见 [../功能点/05-模型预测.md](../功能点/05-模型预测.md)；任务轮询与取消见 [conventions.md](./conventions.md)。

## 1 POST /api/predict/import

上传待预测 CSV / Excel 并校验表头。文件只作输入，不登记。

请求：`multipart/form-data`，字段 `file`。

- 文件落 `temp/uploads/<user_id>/<file_id>/`；页面重置或开始新预测时清理，只作本次输入。
- 导入文件在 `import.json` 中登记 `page=predict`、`role=data`。

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "file_8f3a1c2d",
    "line": "expert",
    "has_label": true,
    "columns": ["project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp", "bug"],
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020
  }
}
```

- `has_label=false` 时 `pos`、`neg` 为 `null`。
- 有 `bug` 与无 `bug` 两种表头都接受。

错误：`40001` 未选择文件或格式不支持、`41301` 超过 100MB、`42201` 除 `bug` 外缺列/多列/列序不符、两线均不匹配（`data.mismatch` 给出第一处不符列）、`commit_id` 列存在重复值、不是 40 位小写十六进制或出现多个 `project`。

## 2 POST /api/predict/precheck

校验本人已保存数据集。

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
    "has_label": true,
    "sample_count": 1200,
    "pos": 180,
    "neg": 1020,
    "repo_available": true
  }
}
```

- `repo_available=true` 表示该数据集继承了仓库来源且 `temp/repos` 缓存可用；上传文件来源没有仓库地址，固定为 `false`，前端禁用缺陷定位。
- `source_type=prediction` 的数据集不能作为待预测数据。

错误：`40001` 预测结果数据集、`40401` 不存在或不属于当前用户、`42201` 缺少特征列、提交哈希重复或出现多个 `project`。

## 3 POST /api/predict/import-model

导入模型文件，必须声明模型线。接受 `.pkl`（sklearn 兼容）与本项目导出的 `.pt`（PyTorch，自包含）。

请求：`multipart/form-data`，字段 `file`、`line`。

响应：

```json
{ "code": 0, "message": "ok", "data": { "model_ref": "mdl_8f3a1c2d", "label": "my-xgb", "line": "expert", "n_features": 14, "framework": "sklearn", "format": "pkl" } }
```

- `label` 取上传文件名（不含扩展名），作为预测结果的 `model_label` 展示名。
- `.pkl` 只接受 sklearn 兼容模型；带 Pipeline 时直接使用。`.pkl` 不含列序元数据，按当前模型线契约的列顺序解释特征；需要自定义列序时使用 `.pt`。
- `.pt` 必须带格式标记 `jit-pt-v1`，内含算法、超参、特征顺序、特征版本与预处理 Pipeline；标记缺失或结构不符时拒绝。
- 文件落 `temp/uploads/<user_id>/<file_id>/`；特征数与声明线不一致时拒绝。
- 模型上传在 `import.json` 中登记 `page=predict`、`role=model`，与数据文件的上传目录并存。

错误：`40001` 未选择文件或模型线非法、`41301` 超过 200MB、`42201` 无法加载 / 格式标记不符 / 特征数不符、`50301` 依赖缺失。

## 3.1 POST /api/predict/save-model

把导入的模型保存为当前用户的模型资产，后续解释依赖它；保存预测结果不依赖模型是否已保存。

```json
{ "model_ref": "mdl_8f3a1c2d", "name": "my-xgb" }
```

```json
{ "code": 0, "message": "ok", "data": { "model_name": "expert-my-xgb-8f3a1c2d" } }
```

- `model_name` 由系统生成 `{line}-{name 归一化}-{model_ref 后 8 位}`，全局唯一；`name` 省略时用导入模型的 `label`；非法字符合并为 `-`，长度 1–40，超长截断。
- 模型文件复制到 `temp/models/<user_id>/<model_name>/`，扩展名按 `framework` 决定；登记 `sha256`、大小、模型线、`framework`、`format` 与 `feature_version`；`model_artifact.status=available`。
- 同一 `model_ref` 重复调用幂等，返回已保存的 `model_name`。
- 非本人 `model_ref` 返回 `40401`；`name` 为空或归一化后为空返回 `40001`；模型文件缺失返回 `40901`。

## 4 POST /api/predict/run

启动预测任务。

请求：

```json
{
  "source": { "kind": "dataset", "id": "ds_..." },
  "model": { "kind": "saved", "name": "expert-xgb-8f3a1c2d" },
  "threshold": 0.5
}
```

- `source.kind` 取 `dataset` / `file`；`dataset` 时 `id=dataset_id`，`file` 时 `id=file_id`；`model.kind` 取 `saved` / `uploaded`，导入模型用 `model_ref`。
- `threshold` 取 0–1，省略时默认 `0.5`。

响应 `202`：

```json
{ "code": 0, "message": "ok", "data": { "job_id": "job_...", "total": 1200 } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | 阈值越界、模型线不一致、数据集为预测结果 |
| 40901 | 数据源在预检后被修改或删除 |
| 42201 | 模型特征数与数据列数不符、输入存在重复 `commit_hash` |
| 42901 | 当前用户已有运行中任务 |
| 50301 | 模型文件缺失或依赖不可用 |

## 5 GET /api/predict/results/{job_id}/rows

分页读取预测结果。

| 参数 | 说明 |
|---|---|
| `page` / `page_size` | 默认 1 / 20，最大 100 |
| `result` | `all` / `defect` / `normal`，默认 `all` |

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "commit_hash": "8f3a1c2d...",
        "commit_message": "fix: null check",
        "author_name": "Zhang",
        "commit_time": "2024-05-01T10:00:00+08:00",
        "bug": 1,
        "risk_score": 0.82,
        "predicted_label": 1
      }
    ],
    "total": 1200,
    "page": 1,
    "page_size": 20
  }
}
```

- `bug` 在无标签数据中为 `null`。
- 未保存结果按输入行顺序返回；已保存任务按 `prediction.commit_hash` 升序返回。
- 接口结果字段统一用 `commit_hash` 表示 Git 提交哈希；导出文件仍使用外部契约列名 `commit_id`。
- 非本人任务返回 `40401`。
- 已保存为预测数据集的任务通过其 `job_id` 读取 `prediction` 表，临时目录清理后仍可访问。

## 6 GET /api/predict/results/{job_id}/export

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名 |
| `format` | `csv` / `excel` |

- 原始列保持契约英文名与顺序，末尾追加 `risk_score`、`predicted_label`、`threshold`。
- 无标签数据不补 `bug` 列。

## 7 POST /api/predict/save

保存本次预测为资产。

```json
{ "job_id": "job_...", "name": "repo-test-predict-8f3a1c2d" }
```

```json
{ "code": 0, "message": "ok", "data": { "dataset_id": "ds_..." } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | 名称为空、非法或超过 128 字符（字符规则同数据集名称） |
| 40401 | 任务不存在或不属于当前用户 |
| 40901 | 结果已丢弃 |

- 每次保存独立成条，不覆盖历史；预测数据集名称不要求全局唯一，允许重名。
- 明细写入 `prediction` 表，主键 `(dataset_id, commit_hash)`；不写 `dataset_commit`。
- 写入前按每行 `project` + `commit_hash` 幂等补齐 `commit` 行并写库内 `commit_id`；详情页通过该 `commit_id` 取提交说明、作者与提交时间，临时目录清理后仍可读。
- 模型未保存时 `model_name` 为空，`model_label` 保留展示名；该结果的解释不可用。

## 8 GET /api/predict/results/{job_id}/commits/{commit_hash}

详情页预测信息。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "commit_hash": "8f3a1c2d...",
    "commit_message": "fix: null check",
    "author_name": "Zhang",
    "commit_time": "2024-05-01T10:00:00+08:00",
    "line": "expert",
    "model": "expert-xgb-8f3a1c2d",
    "threshold": 0.5,
    "risk_score": 0.82,
    "predicted_label": 1,
    "actual_label": 1,
    "repo_available": true
  }
}
```

- `line` 为本次预测使用的模型线别（`expert` / `semantic`），详情页据此决定可用解释技术与贡献图形态。
- `model` 取保存模型的 `model_name`；模型未保存时取导入模型的展示名。

## 9 POST /api/predict/explain

按需计算解释，不落库。

```json
{ "job_id": "job_...", "commit_hash": "8f3a1c2d...", "technique": "shap" }
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "technique": "shap",
    "items": [
      { "feature": "ns", "contribution": 0.18, "direction": "positive" }
    ],
    "note": null
  }
}
```

- `technique` 取 `shap` / `lime` / `permutation`。
- 语义线使用 `shap` 返回 `40001`；使用 `lime` / `permutation` 时特征名为 `f_0001`–`f_0768`，只返回贡献最大的前 10 项。
- 模型未保存、模型文件缺失或 `model_name` 为空时返回 `40901`，`data.reason` 为 `model_unavailable`。
- 非本人任务返回 `40401`。

## 10 POST /api/predict/localize

返回 diff、可疑行与修复建议。

```json
{ "job_id": "job_...", "commit_hash": "8f3a1c2d..." }
```

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "files": [
      {
        "path": "src/parser.py",
        "suspicious_score": 0.87,
        "lines": [
          { "no": 41, "type": "context", "content": "def parse(self, raw):", "suspicious": false, "suggestion": "" },
          { "no": 42, "type": "added", "content": "    return raw.strip()[0]", "suspicious": true, "suggestion": "先判空或使用切片，避免空字符串取下标。" }
        ]
      }
    ]
  }
}
```

- `type` 取 `added` / `removed` / `context`；`context` 为 hunk 内上下文行，不参与可疑度计算，`suspicious` 固定 `false`、`suggestion` 为空串。
- 每个文件最多返回前 200 行 hunk；`suspicious_score` 只按新增 / 删除行计算。
- 仅对有仓库来源且缓存可用的提交开放。
- 外部导入数据集或缓存缺少该提交时返回 `40901`，`data.reason` 取 `no_repo` / `commit_missing`。
- 建议由规则模板生成，不调用外部模型。

## 11 页面进度

`GET/PUT /api/page-state/predict`，见 [page-state.md](./page-state.md)。保存数据源、模型、阈值与最近任务 `job_id`。
