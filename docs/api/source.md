# 源码读取与缺陷定位 API（source / localize）

一句话：按提交读取仓库目录树与文件内容，并对提交给出可疑文件/行排序、证据与修复建议文件；同步执行，不建 job。

实现状态：已实现　期次：一期

定位文件契约见 localization 列契约；功能点职责见 [`../function_point/localization.md`](../function_point/localization.md)。

## 1. 职责与不负责范围

- 负责 Git 对象读取（tree/blob）、行窗口截断、可疑文件/行排序、证据汇总与建议生成。
- 不负责预测与解释计算：只消费既有特征/预测；不修改仓库、不执行仓库代码、不写库。
- 无可靠补丁时只交付建议，不伪造 diff。

## 2. 端点契约

### GET /api/source/tree

| 参数 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 40 位十六进制，出参归一小写 |
| `path` | 否 | 安全相对 POSIX 路径，默认 `''` |
| `search` | 否 | 非空字符串，≤4096，路径子串 |
| `repo_source` | 否 | 仓库路径/URL |
| `dataset_id` | 否 | 已登记数据集（与 `repo_source` 二选一） |

响应：

```json
{"commit_hash": "...", "path": "", "entries": [{"name": "a.py", "path": "a.py", "type": "blob", "size": 123, "mode": "100644"}], "truncated": false, "skipped": [{"path": "sub", "reason": "unsupported_gitlink"}]}
```

`entries` 最多 1000 条；`type ∈ tree|blob`。

### GET /api/source/file

| 参数 | 必填 | 契约 |
|---|---|---|
| `commit_hash` | 是 | 40 位十六进制 |
| `path` | 是 | 安全相对路径 |
| `start_line` | 否 | ≥1，默认 1 |
| `end_line` | 否 | ≥1；缺省窗口 2000 行 |
| `repo_source` / `dataset_id` | 否 | 仓库定位，同上 |

响应：

```text
commit_hash, path, status(ok|not_found|too_large|binary), content,
start_line, end_line, total_lines, size_bytes, encoding, reason
```

`reason`：`not_found|not_regular_blob|file_size_max|nul_or_non_utf8`；单文件上限取配置 `localization.file_size_max`（默认 1MiB，上限 16MiB）。

### POST /api/localize/run

`multipart/form-data`，同步执行，不创建 job。

| part | 必填 | 契约 |
|---|---|---|
| `config` | 是 | JSON 文本 |
| `files[]` | 否 | ≤4 个，合计 ≤64MiB（特征表/预测表/模型文件 `.pkl` 或 `.zip`/可选输入） |

`config` 字段：`weights`、`top_n{files,lines}`（1..1000）、`file_size_max`（1..16MiB）、`suggestion_sources ⊆ {template,llm,history}`、`patch_preview`(bool)、`format`(`csv|xlsx`)、`commit_hash`、`model_name`（与 `files[]` 模型文件二选一），以及 service 层取出的 `repo_source` / `dataset_id`。

响应：

```json
{"job_id": "...", "module": "localize", "status": "success", "outputs": [{"name": "...", "sha256": "...", "size_bytes": 1}], "manifest_name": "...", "summary": {}, "localization": [], "suggestions": []}
```

`localization` 只回前 20 行。

### GET /api/localize/outputs/{job_id}/{name}

产物：

```text
localization_localization_<job_id>.csv / .xlsx
localization_evidence_<job_id>.json
localization_suggestions_<job_id>.md
<stem>.manifest.json
```

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 哈希/路径/行范围/搜索非法、配置非法、上传字段重复或文件过多、仓库读取失败 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 提交/目录/数据集/输出批次不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 仓库定位：`repo_source` 优先；未给时必须给 `dataset_id`，两者皆缺 40001。
- 行窗口上限 2000 行；二进制或非 UTF-8 文件返回 `status=binary` 且 `content=null`。
- 定位输入为既有特征/预测或上传文件，不重算模型。

## 4. 输出契约

- 可疑文件/行按权重合成排序，`top_n` 截断；证据含提交、文件、行号与命中原因。
- 建议四段式：问题说明、建议修改、风险提示、参考依据；无可靠补丁时明确说明。
- 文件名不因模块内部状态变化，批次不可覆盖。

## 5. 可配置项

`localization.top_n`、`localization.weights`、`localization.file_size_max`、`suggestion_sources` 来自配置中心；请求可覆盖部分参数。

## 6. 状态持久化

- 同步执行，不写 `job` 表（返回的 `job_id` 仅用于产物命名与下载）。
- 产物落 `temp/outputs/<job_id>/`，含 manifest 与 `.index.json`。

## 7. 验收

- tree/file 对同一提交稳定返回，路径穿越与超长行窗口被拒绝。
- 定位结果只含可疑文件与行，附证据与建议；无补丁时明确提示。
- 产物可下载且列契约符合 localization 列契约。
- 不修改仓库、不执行仓库代码、不写数据库。

## 8. 边界

定位与解释归入预测页入口，但运行不依赖预测是否先跑；它是独立工具，输入文件齐备即可运行。


