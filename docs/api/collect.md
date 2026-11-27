# 数据收集 API（collect）

一句话：从 Git 仓库枚举分支并采集提交，或从公开数据集 URL 拉取已打标数据，统一交付一份核心「已标注数据集」文件；Excel 在下载时按需生成，不预生成冗余文件。

设计状态：目标契约（已实现）。仓库分支枚举、公开数据集 URL 拉取与下载时格式转换均按本文执行。

输入输出 schema 见 collected_commits 列契约；内部记录见 manifest 契约；功能点职责见 [`../function_point/collect.md`](../function_point/collect.md)。

## 1. 职责与不负责范围

- 负责仓库范围解析、远端分支枚举、提交采集、SZZ 打标、标签边界处理和核心数据集发布。
- 负责公开数据集 URL 拉取、许可证记录、字段映射与标签映射，并按同一 `collected_commits` 契约发布。
- 负责把 summary / audit / quality / manifest 作为内部记录写入任务引用，用于校验与复现；不把它们包装成用户结果文件。
- 不负责清洗、特征工程、训练、预测、评估、解释与定位；不写 `commit` / `commit_feature` 业务表（导入走 storage）。
- Web 页面暴露 Git 仓库与公开数据集两种模式；提交清单与 `dataset_id` 入口可作为 API / CLI 兼容能力保留，不进入页面。

## 2. 端点契约

### GET /api/collect/branches

枚举 Git 仓库的远端分支，供 `/collect` 的分支下拉使用。

| 参数 | 必填 | 契约 |
|---|---|---|
| `repo_source` | 是 | 绝对本地路径或 `https`/`git` URL；一期支持公开仓库或服务端已配置凭据的仓库；本地路径须在 `collect.allow_roots` 内；不允许账号密码、query、hash |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "repo_name": "repo-x",
    "branches": ["main", "develop", "release/1.2"],
    "default_branch": "main"
  }
}
```

约束：

- 分支列表不能为空；空列表返回 `40001`，页面提示“未找到可用分支，请检查仓库 URL 或权限”。
- `default_branch` 仅供展示排序参考；前端默认选中返回列表第一项，不插入“HEAD”之类的虚拟项。
- 刷新失败不返回空数组冒充成功；页面保持分支下拉禁用并允许重试刷新。

### POST /api/collect/source-columns

抓取公开数据集 URL 并返回列名，供字段映射下拉使用。

请求 JSON：`{source_url}`。响应 `data:{columns:[...]}`。

- 仅接受 `https`，按 `collect.protocol_whitelist` 校验；不允许账号密码、query、hash。
- 抓取失败或内容不是 CSV/XLSX 返回 `40001`；远端不可达返回 `40400`。

### POST /api/collect/run

`multipart/form-data`，不接受 query 参数。

| part | 必填 | 契约 |
|---|---|---|
| `config` | 否 | JSON 文本，默认 `{}`；只允许 1 份 |
| `files[]` | 否 | 提交清单 CSV，最多 1 个，单文件 ≤64MiB |

`config` 字段：

| 字段 | 必填 | 契约 |
|---|---|---|
| `source_type` | 否 | `git_repo`（默认）/ `public_dataset`；公开数据集模式忽略 Git 分支字段 |
| `repo_source` | Git 模式条件必填 | 绝对本地路径或 `https`/`git` URL；本地路径须在配置 `collect.allow_roots` 内 |
| `source_url` | 公开数据集模式必填 | 仅 `https`，不允许账号密码、query、hash |
| `license` | 否 | 公开数据集许可证，≤128 字符 |
| `field_mapping` | 公开数据集模式必填 | 提交哈希 / 提交时间 / 提交信息 / 作者等列映射 |
| `label_mapping` | 公开数据集模式必填 | 正样本值、负样本值映射为 1 / 0，其余为未标注 |
| `dataset_name` | 是 | ≤255 字符；同时作为数据集名称与下载文件基础名 |
| `branch` | Git 模式必填 | 安全 git ref，≤255；必须存在于 `GET /api/collect/branches` 返回的列表中；不允许留空 |
| `start_time` / `end_time` | 否 | 带时区 ISO8601，start ≤ end；按提交 `committed_at` 过滤；留空表示全量；结束日期包含当天 |
| `start_commit` / `end_commit` / `head_expect` | 否 | 40 位 hash |
| `mode` | 否 | `full` / `incremental`，默认 `incremental` |
| `fetch_remote` | 否 | bool，默认 true |
| `dedup` | 否 | 仅支持 `commit_hash` |
| `szz_method` | 否 | `szz_v1` / `szz_lite` |
| `dataset_id` | 否 | API / CLI 兼容入口；Web 页面不暴露 |

变更说明：`format` 从运行配置移除；收集任务不再同时落 CSV 与 XLSX。`split_ratio` 不属于收集阶段，禁止在 collect 配置中出现。

未知字段返回 `40001`。输入三态：上传清单 → 哈希列表；`dataset_id` → 已登记成员（未登记 40400，空成员 40001）；两者皆空 → 按 Git 仓库范围全量采集。

响应 `data:{job_id,status}`，`status` 恒为 `queued`。

### GET /api/collect/preview/{job_id}

读取 `collected_commits_<job_id>.csv`，返回数据集预览前 20 行：

```json
{"columns": ["..."], "preview": [{"commit_hash": "...", "...": null}]}
```

空串转 `null`；列不一致返回 `40001`；批次或文件未登记返回 `40400`。页面标题为“数据集预览”，不叫“提交预览”。

### POST /api/collect/resave/{job_id}

把成功的 collect 核心产物登记为数据集（幂等）：

- 前置：任务 `kind=collect` 且 `success`，产物含 `collected_commits_<job_id>.csv`。
- 校验登记大小与 SHA-256、列契约，不符返回 `40001`。
- `dataset_id = uuid5(NAMESPACE_URL, "collect-resave:" + job_id)`；dataset 状态 `ready`。
- 响应 `data:{job_id,dataset_id,status:"success"}`。

### GET /api/collect/outputs/{job_id}/{name}

下载核心数据集文件。

| 参数 | 必填 | 契约 |
|---|---|---|
| `name` | 是 | 产物名；页面固定为 `collected_commits_<job_id>` 或等价逻辑名 |
| `format` | 否 | `csv`（默认）/ `xlsx`；仅影响本次下载响应 |

- `format=csv`：直接返回规范主表 `collected_commits_<job_id>.csv`。
- `format=xlsx`：从同一规范 CSV 即时生成单 sheet XLSX 并返回；不写入产物目录、不登记为新产物、不生成同名 manifest。
- 响应 `Content-Disposition` 文件名为 `<dataset_name>_<job_id>.<ext>`；`dataset_name` 必须做文件名安全清洗。
- summary / audit / quality / manifest 不通过该端点作为用户结果文件下载。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 表单 / 未知字段、清单格式或哈希非法、配置非法、分支不存在、产物列或 checksum 不一致 |
| 40100 | 401 | 鉴权失败 |
| 40400 | 404 | 数据集未登记、仓库不存在、输出批次 / 文件不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 提交清单：单列 `commit_hash`，值 40 位十六进制。
- `dataset_id` 输入：使用已登记成员，缺失 `repo_source`/`branch` 时回填数据集值。
- 仓库范围：Web 页面固定选择 `branch`；API / CLI 还可用 `start_time/end_time`、`start_commit/end_commit`、`head_expect` 定位范围。
- 公开数据集：`source_type=public_dataset` 时从 `source_url` 拉取 CSV/XLSX，按 `field_mapping` / `label_mapping` 归一化为 `collected_commits`；`label_source=public_dataset`，不跑 SZZ。

### SZZ 判据（与实现同源）

- 修复提交判据（D4）：提交信息同时命中缺陷编号与修复语义词（词首边界）。
- 两套方法：`szz` 行级回溯（标准 SZZ，输出 `szz_v1`）；`szz_lite` 文件级回溯（输出 `szz_lite`），二者结果差异必须量化出示。
- 回溯未命中的修复提交（D5）不入样本集、不记 0，只在统计中单列。
- 正样本比例异常区间：`ABNORMAL_LOW=0.40`、`ABNORMAL_HIGH=0.60`；落在区间先复核打标逻辑。

## 4. 输出契约

用户可见核心产物只有一份：

```text
collected_commits_<job_id>.csv
```

内部记录（用于复现与任务审计，已登记在产物批次中，但不在收集页结果文件区展示）：

```text
<stem>.manifest.json
collect_summary_<job_id>.json
collect_audit_<job_id>.json
collect_quality_<job_id>.json
collect_quality_<job_id>.md
collect_repository_snapshot_<job_id>.json   # 内核提供快照时
```

`summary`：`rows, labeled_rows, positive_rows, negative_rows, unlabeled_rows, head_hash`。

`audit`：`deduplicated, skipped{merges,outside_output_range}, stage_errors[], head_check, fetch, cache{hit,strategy}, szz{...}, boundary`。

`quality.checks`：`missing_rate, duplicate_rows, skipped_rows, label_conflicts, time_anomalies, field_mapping, anomaly_samples, handling_note`。

禁止把 XLSX 作为 collect 任务的预生成产物；禁止把 summary / audit / quality / manifest 暴露到“结果文件”区。

## 5. 可配置项

- `collect.allow_roots`：本地仓库允许根目录。
- `collect.protocol_whitelist`：允许的 URL 协议。
- `collect` 默认模式来自配置中心 `page_prefs`；分支不从配置中心取默认值，页面必须刷新后选择。
- `SYNC_FETCH=0` 时跳过 `git fetch`，直接用本地 HEAD（离线演示）。

## 6. 状态持久化

- 任务 `kind=collect`，五态；进度阶段按“校验来源 / 拉取提交 / 缺陷标注 / 生成数据集 / 完成导出”呈现。
- `params` 记录 `input_ref`、`input_sha256`、归一化 `config`、已选 `branch`。
- `output_ref_json.outputs` 登记本批次全部产物（核心 CSV、manifest、summary / audit / quality、公开数据 metadata、仓库快照）；页面结果文件区只展示核心 CSV，其余内部记录不在用户界面混排。下载端点仍按 `outputs` 中的登记项校验，未登记文件不可下载。
- 失败 `error_log` 为脱敏文本（≤2000 字符），不含内部路径。
- 产物落 `temp/outputs/<job_id>/`，不可覆盖；`resave` 只登记数据集，不修改产物。

## 7. 验收

- 本地仓库路径、远端 URL、上传清单、`dataset_id` 四种入口都能独立跑通。
- 分支列表来自仓库；未知分支被拒绝；页面不提供手填分支。
- 产物列严格符合 collected_commits 列契约；未打标保持 null；SZZ 边界内标签不外溢。
- 任务只落一份规范 CSV；下载 CSV 直接返回该文件，下载 Excel 按请求即时生成且不落盘。
- 结果文件区只展示一个「已标注数据集」逻辑文件。
- 内部记录仅用于审计，不与核心文件混排。
- 非法清单、非法范围、非法 `repo_source`、跨模块产物下载均被拒绝。
- 同一仓库与参数重复运行，`summary` 计数一致（job_id 与耗时除外）。
- 公开数据集 URL 拉取、字段 / 标签映射与 Git 模式产物同契约；存储导入不再创建 `public_dataset`。

## 8. 边界

collect 是数据入口而不是流水线调度器：它不感知清洗 / 训练是否存在。数据集只是可选展示与入参来源，未 `resave` 也不影响产物下载与其他模块直接吃文件运行。



