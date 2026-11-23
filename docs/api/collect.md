# 缺陷数据收集 API（collect）

一句话：把调用方指定的 Git 仓库转换为符合统一 schema 的 `commits.csv`，并交付 SZZ 标签、Kamei 特征、时间序划分标记与可复现 manifest。

实现状态：已实现　期次：一期

W3 已接入配置化收集、提交清单、任务五态、CLI、双格式输出、快照与同名 manifest。HTTP 仓库收集统一排队，CLI 同步运行；公网 URL 的实际联网验收受环境限制，传输边界使用受控替换传输 fixture 验证，不冒充远端下载实测。

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.9；公共鉴权、包络与任务口径见 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责仓库路径或 URL 校验、提交采集、SZZ 标注、Kamei 14 维特征提取、时间序 70/30 划分、文件交付与收集任务管理。
- SZZ 判据单源复用原 02 实现：v1 同时要求 `CAMEL-数字` 与词首边界 `\b(fix|bug|patch)`，支持 `szz` / `szz_lite`；无匹配修复或不完整回溯不伪造负样本，其他仓库无适配判据时可交付空标签。clean 的 `szz_label` 只复用该实现。
- 不负责清洗处理链、训练、预测、评估、解释、源码浏览或修复建议。
- 不隐式导入数据库；需要展示导入时，由调用方把产物提交给 [storage.md](storage.md)。

## 2. 端点契约

### POST /api/collect/run

`multipart/form-data`；通常只传 `config`。`files[]` 可选一个 CSV/XLSX，必须仅含 `commit_hash` 列。仓库规模与清单大小不等价，HTTP 统一创建 `kind=collect` 的异步 job；同步运行使用同实现的独立 CLI。

`config` JSON part：

| 字段 | 必填 | 类型 | 契约 |
|---|---|---|---|
| `repo_source` | 是 | string | 本地路径或仓库 URL；本地路径须位于允许根目录，URL 协议须在白名单内 |
| `branch` | 否 | string | 分支或 ref；缺省为仓库默认 HEAD |
| `dataset_name` | 是 | string | 写入 manifest 的数据集显示名 |
| `start_time` / `end_time` | 否 | datetime | 提交时间闭区间；仅限制输出样本，不截断历史特征所需前序提交 |
| `start_commit` / `end_commit` | 否 | string(40 hex) | 可检出的提交范围，可与时间范围组合 |
| `mode` | 否 | string | `full` / `incremental`，默认 `incremental` |
| `fetch_remote` | 否 | bool | 默认 `true`；`false` 使用本地 HEAD |
| `head_expect` | 否 | string(40 hex) | 指定期望 HEAD，不一致则拒绝 |
| `dedup` | 否 | string | 仅支持 `commit_hash`，默认该值 |
| `szz_method` | 否 | string | `szz` / `szz_lite`，默认 `szz` |
| `split_ratio` | 否 | float | 时间序训练侧比例，默认 `0.7`；禁止随机划分 |
| `format` | 否 | string | `csv` / `xlsx`，默认 `csv`；HTTP 同批交付双格式，CLI 按此格式交付 |
| `dataset_id` | 否 | string | 已登记仓库配置及提交集合的便利输入；显式仓库/分支和上传清单优先 |

响应 `data`：`{job_id,status:"queued"}`。通过 jobs 详情获取终态和 `output_ref_json`，其中含 `outputs[]`、`manifest_name`、`summary`、`columns`。`outputs[]` 元素为 `{name,size_bytes,sha256}`，`summary` 含 `rows`、`labeled_rows`、`positive_rows`、`negative_rows`、`unlabeled_rows`、`head_hash`、`train_rows`、`test_rows`。

### GET /api/collect/preview/{job_id}

返回 `{columns,preview}`，最多前 20 行；读取本次已登记、checksum 校验通过的 CSV，不把预览长文本写进 job 的 TEXT 快照。空标签返回 null，文件下载仍提供完整记录。

### GET /api/collect/outputs/{job_id}/{name}

下载该次运行的指定文件；`name` 必须是 manifest `outputs[]` 中登记的基础文件名，禁止路径分隔符与 `..`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 参数或时间范围非法、路径越界、协议不允许、HEAD 不符、提交不可检出、随机划分请求、同 kind 运行冲突 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括下载 |
| 40400 | 404 | 仓库、job 或登记输出不存在 |
| 50000 | 500 | 未预期的服务错误；运行期 Git/SZZ 失败同时写入 job 脱敏日志 |

## 3. 输入契约

输入是仓库配置而非上游服务。`dataset_id` 仅是读取已登记仓库与提交集合的便利项，显式 `repo_source` 优先；独立 CLI 不要求数据库，HTTP 只依赖配置/job 基础设施，不要求业务表已有样本。

安全硬要求：校验路径与 URL、仓库大小和超时；Git 调用使用参数数组，文件名和 ref 不拼接 shell；克隆目标限定在允许根目录。上传辅助文件时同样执行大小、扩展名与魔数校验。

`commits.csv` 的输入兼容性判定逐字采用 [../file-contracts.md](../file-contracts.md) §3.1：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 来源仓库名 |
| author_name / author_email | string | 是 / 否 | 作者 |
| committed_at | datetime | 是 | 提交时间 UTC |
| message | string | 是 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| ns…sexp（14 列） | float | 是 | Kamei 14 维 log 变换值（`fix` 为 0/1），列序固定 |
| is_bug_inducing | int 空可 | 否 | SZZ 真标签 1/0/空 |
| labeled_at | datetime | 否 | 打标时间 |
| is_test | int 0/1 | 是 | 时间序划分标记 |
| label_method | string | 否 | szz / szz_lite |

## 4. 输出契约

| 文件 | 命名 | 内容 |
|---|---|---|
| commits 主表 | `collect_commits_<job_id>.csv`，或 `.xlsx` | 严格使用上述 §3.1 全部列及固定列序 |
| 统计 | `collect_summary_<job_id>.json` | 行数、正/负/未标注、HEAD、训练/测试数 |
| 审计 | `collect_audit_<job_id>.json` | 去重/跳过、SZZ 未回溯原因、缓存命中与划分边界 |
| 仓库输入快照 | `collect_repository_snapshot_<job_id>.json` | 实际参与采集的仓库/HEAD/提交元信息，与 manifest.inputs 的快照 SHA 一致 |
| manifest | 每个基础产物同名 `.manifest.json` | 严格使用 §3.9；CSV/XLSX 共用同 stem 的 manifest；不回显缓存绝对路径 |

CSV 为 UTF-8 BOM；XLSX 仅一个主表 sheet，manifest 不写入 sheet。`is_bug_inducing` 未打标保持空值，禁止写 0。14 维列序与 log 变换口径固定，`fix` 不做 log；交换文件按 10 位小数编码，不对计算过程舍入。历史索引与 `committed_at` 统一使用提交者时间，严格排除未来提交；`is_test` 仅由时间序边界产生。

固定快照的 `labeled_at` 由 HEAD 提交时间钉定，作为标签版本基准，避免相同输入重跑时只因墙钟变化改变表格；实际执行时间以 job 的 started/finished 与 manifest.created_at 为准，不把版本基准时间冒充本次运行时间。

manifest 示例结构与字段以 [../file-contracts.md](../file-contracts.md) §3.9 为准，本模块不得另设版本字段或省略输入、配置、输出 checksum。

## 5. 可配置项

- 持久化命名空间：`collect.allow_roots`、`collect.protocol_whitelist`，经 [config.md](config.md) 读写，重启恢复。
- 单次运行：仓库、分支、时间/提交范围、HEAD、增量方式、远端拉取、SZZ 方法、时间序比例、输出格式。
- `.env` 仅提供出厂默认；不得以环境变量替代每次调用的仓库配置或覆盖已保存命名空间值。

## 6. 状态持久化

- 每次运行生成 `job_id`；同步运行落 `success` / `failed` 终态，异步运行落 `queued / running / success / failed / cancelled` 五态，kind 为 `collect`。
- 同 kind 仅允许一个 running，通过 job 表条件更新互斥；重启遗留 running 置 failed，进度与脱敏错误保留，可经 [jobs.md](jobs.md) 重试或取消。
- 文件落盘 `backend/var/outputs/<job_id>/`，该目录必须被 gitignore；job `output_ref_json` 只登记文件与 checksum，不把数据库当作模块间数据通道。
- 相同仓库快照与相同配置重跑保持表格内容一致；incremental 仅复用 source/HEAD/配置/清单/代码版本全部匹配且 checksum 正确的 JSON 缓存，HEAD 或参数变化重新计算；未知标签不改写为负样本。
- 重试从私有输入引用和 SHA 恢复原始配置/清单，重新校验当前允许根目录与协议；终态与进度更新均携带 retry_count，取消或旧 attempt 不得覆盖新任务。

## 7. 验收

fixtures：`tests/fixtures/files/collect/`，无需 clean、train 或数据库前置。

- **正常**：本地小仓库与固定 URL 快照分别产出 §3.1 全列文件和 §3.9 manifest；SZZ 双方法、checksum、CSV BOM 与 XLSX 单 sheet 均通过。
- **边界**：空提交范围、单提交、全空标签、历史特征跨界、增量重复运行、时间序 70/30 边界均有明确结果；未打标仍为空，划分无随机性。
- **非法**：越界路径、非白名单协议、伪造扩展名、不可检出 ref、HEAD 不符、随机划分请求均返回 40001，不产半成品；下载越权路径返回 40001 或 40400。
- 同配置重复执行无重复提交；重启遗留 running 被置 failed；CLI 与 API 对同一 fixture 的输出逐列一致。

## 8. 边界

模块间依赖仅为 §3.1 文件 schema 兼容：clean/train 可直接消费产物，但收集运行不调用它们，也不要求 storage、dataset 表或任何上游服务存在。源码读取属 localization，SZZ 实现共享不等于服务调用依赖。
