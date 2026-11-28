# 产物路径与文件交换

本文件是产物目录、清单、保留与下载的唯一真源。

## 1 目录结构

```text
temp/
├── repos/<platform>-<owner>-<repo>/        # 仓库克隆缓存，按仓库共享
├── uploads/<user_id>/<file_id>/            # 导入文件临时区
│   ├── source.csv | source.xlsx | source.pkl | source.pt
│   └── import.json
├── outputs/<user_id>/<job_id>/             # 任务临时产物
│   ├── manifest.json
│   ├── data.csv
│   └── steps.json
├── datasets/<dataset_id>/                  # 已保存的数据集资产
│   ├── manifest.json
│   └── data.csv
├── models/<user_id>/<model_name>/          # 已保存的模型资产
│   ├── <model_name>.pkl | <model_name>.pt
│   └── meta.json
└── evaluations/<user_id>/<evaluation_id>/  # 已保存评估的 PNG
```

- 克隆缓存按仓库共享，多个用户收集同一仓库复用同一份，只读。
- 上传临时区按用户与 `file_id` 隔离；超出大小上限或表头校验失败时立即删除，不残留。
- 任务产物按用户与任务分目录，禁止跨用户读取。
- 模型保存时把 `outputs/` 中的模型文件复制到 `temp/models/`；扩展名由 `model_artifact.format` 决定：`sklearn` 为 `.pkl`，`pytorch` 为 `.pt`。
- 数据集保存时，产物复制到 `temp/datasets/`；`outputs/` 保留到本页重置或下一轮任务，保证保存后本轮结果仍可预览、导出与下载。
- 评估保存时，指标写入 `evaluation` 表，PNG 复制到 `temp/evaluations/<user_id>/<evaluation_id>/`；未保存的评估随页面重置删除。
- 库内 `manifest_path` / `weight_path` / `file_path` 一律存相对仓库根目录的 POSIX 路径（如 `temp/datasets/...`），不以绝对路径入库。

## 2 import.json

```json
{
  "file_id": "file_...",
  "user_id": "u_...",
  "page": "clean",
  "role": "data",
  "original_name": "dataset.csv",
  "stored_name": "source.csv",
  "size": 0,
  "sha256": "...",
  "line": "expert",
  "columns": [],
  "row_count": 0,
  "created_at": "2026-11-27T10:00:00+08:00"
}
```

- `columns` 为校验通过的完整表头，顺序与字段契约一致。
- `page` 取 `clean` / `train` / `predict` / `evaluate`，由导入端点按所属页面写入。
- `role` 取 `data` / `model`：预测页的数据文件为 `data`、模型文件为 `model`，其余页面只有 `data`。
- 导入文件只作本次输入，不登记为数据集或模型资产。
- 同一用户同一页面再次导入同一 `role` 时，先删除该角色此前的上传目录；同一页面的 `data` 与 `model` 可并存。页面重置按 `page` 清理该页全部上传目录。

## 3 manifest.json

```json
{
  "job_id": "job_...",
  "kind": "collect",
  "user_id": "u_...",
  "created_at": "2026-11-27T10:00:00+08:00",
  "line": "expert",
  "columns": [],
  "row_count": 0,
  "files": [{ "name": "data.csv", "size": 0, "sha256": "..." }]
}
```

- `columns` 与导出表头一致，用于校验与预览。
- 每个文件登记大小与 `sha256`，下载前校验；哈希统一为 64 位小写十六进制。

## 4 保留与清理

- 未保存的任务产物保留到该页面的进度被重置，或同一页面发起新一轮任务。
- 导入文件（`uploads/`）在页面重置、开始新流程、`DELETE /api/page-state/{page}` 时清理；导入校验失败时立即清理。
- 业务数据只在用户点击「保存到数据库」时写入；产物先留在 `temp/`，预览、导出与刷新都不入库。
- 保存为数据集后产物复制到 `temp/datasets/`；保存为模型后文件复制到 `temp/models/`；副本不再受页面重置影响，`outputs/` 原件仍按本节清理。
- 删除数据集时移除其 `temp/datasets/<dataset_id>/` 目录；共享仓库缓存、`commit` / `commit_feature` 与已保存模型不清理。
- 已保存的模型是单文件：`.pkl` 为 sklearn Pipeline，`.pt` 为自包含字典（含结构、超参、特征顺序、特征版本与预处理）。
- 克隆缓存不随任务清理，按仓库长期复用。

## 5 下载

- 统一走 `GET /api/storage/files/{id}/download` 或模块导出端点。
- 下载前校验归属，非本人返回 `40401`。
- 数据集与导出表支持指定文件名与 CSV / Excel；模型按 `model_artifact.format` 返回 `.pkl` / `.pt`，不接受格式转换。
- 只允许下载 manifest / 资产登记中存在的文件名，不接受任意路径。

## 6 文件交换

- 模块之间只通过产物文件与 manifest 交接，不共享内存状态。
- 下游模块读取上游产物时先校验 `sha256` 与列契约。
