# 接口 clean

## 1 POST /api/clean/import

上传 CSV / Excel 并校验表头。

- `Content-Type: multipart/form-data`，字段名 `file`。
- 仅接受 `.csv` / `.xlsx`；总大小上限 100MB。
- Excel 只读第一个工作表，首行作为表头。
- 文件落 `temp/uploads/<user_id>/<file_id>/`；页面重置或开始新清洗时清理，只作本次输入。

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "file_8f3a1c2d",
    "line": "expert",
    "row_count": 1200,
    "column_count": 21,
    "columns": ["project", "commit_id", "commit_time", "author_name", "author_email", "commit_message", "ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp", "bug"],
    "preview": []
  }
}
```

错误：

| code | 场景 | data |
|---|---|---|
| 40001 | 文件为空、格式不支持 | — |
| 41301 | 超过大小上限 | — |
| 42201 | 表头与字段契约不一致：缺列、多列、列序不符；提交哈希非 40 位小写十六进制或出现多个 `project` | `data.mismatch` 给出第一处不符列 |

- `line` 由表头自动识别为 `expert` 或 `semantic`；两者都不匹配时按 `42201` 返回第一处不符。

## 2 POST /api/clean/run

启动清洗任务。

请求：

```json
{
  "source": { "kind": "dataset", "id": "ds_..." },
  "operations": [
    { "op": "dedup", "params": { "key": "commit_hash" } },
    { "op": "missing", "params": { "mode": "drop", "columns": ["ns"] } }
  ]
}
```

- `source.kind` 取 `dataset` / `file`；`dataset` 时 `id=dataset_id`，`file` 时 `id=file_id`。
- `dataset` 来源仅接受 `git_repo` / `upload` / `clean`，测试集与预测结果不可作为清洗输入。
- `op` 取 `dedup` / `missing` / `outlier` / `label` / `balance`。
- `operations` 为空返回 `40001`；数组顺序即执行顺序；参数默认值见 [../功能点/03-数据清洗.md](../功能点/03-数据清洗.md) 第 4.1 节，未填参数按默认值补齐。
- 样本平衡只接受 `under`；传 `over` 或其他值返回 `40001`。
- 语义线只允许操作元数据列与 `bug`，向量列不可作为目标。

响应 `202`：

```json
{ "code": 0, "message": "ok", "data": { "job_id": "job_..." } }
```

错误：

| code | 场景 |
|---|---|
| 40001 | 操作未知、参数未知或越界、目标列不存在 |
| 40401 | 数据集或导入记录不存在、不属于当前用户 |
| 42901 | 当前用户已有运行中任务 |

## 3 GET /api/clean/results/{job_id}/steps

返回每步统计快照。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "steps": [
      { "op": "dedup", "before": 1200, "after": 1180, "changed": 20, "stats": { "pos": 170, "neg": 1010 } }
    ]
  }
}
```

- 每个操作一项，按执行顺序返回；无变化时 `changed` 为 0。

## 4 GET /api/clean/results/{job_id}/rows

分页预览清洗结果，字段同 [collect.md](collect.md) 第 4 节，只返回核心字段。

## 5 GET /api/clean/results/{job_id}/export

导出清洗结果。

| 参数 | 说明 |
|---|---|
| `filename` | 必填，不含扩展名 |
| `format` | `csv` / `excel` |

- 列名、顺序、数量与输入完全一致。

## 6 幂等与覆盖

- 未重置时重新执行覆盖当前结果；保存时按覆盖键定位：基于已保存数据集用 `clean|parent_dataset_id|ops_hash`，基于上传文件用 `upload|file_sha256|ops_hash`；键相同则覆盖原数据集，不同则新建。
- `file_sha256` 取导入文件在 `import.json` 中登记的哈希；`ops_hash` 为操作按名称排序并补齐默认参数后的 JSON 哈希。
- 覆盖不检查下游引用；已训练模型与预测结果保留。
- 保存数据集走 `POST /api/datasets`，`job_id` 幂等。
