# 数据清洗与预处理 API（clean）

一句话：独立接收 `commits.csv`，按可排序、可启停、可调参的处理链执行 preview 或 apply，交付 `cleaned.csv`、逐步统计、特征分布图和 manifest。

实现状态：已实现　期次：一期

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.2、§3.9；公共口径见 [README.md](README.md)。

## 1. 职责与不负责范围

- 负责操作注册表、处理链校验、preview/apply、逐步样本与标签统计、排除原因、指定特征前后分布及文件交付。
- 复用 collect 的 SZZ 判据；`szz_label` 不维护第二套关键词或匹配规则。
- 不负责 Git 采集、训练、预测、阈值评估或自动展示导入。
- preview 不生成 cleaned 主表；apply 生成新文件，不覆盖输入文件，也不要求创建数据库数据集版本。

## 2. 端点契约

### GET /api/clean/operations

无请求参数。响应 `data.operations[]`：

| 字段 | 含义 |
|---|---|
| `op` / `name` / `description` | 操作标识、显示名与用途 |
| `input_schema` / `output_schema` | 输入与输出契约引用 |
| `params_schema[]` | `{name,type,default,min,max,choices,description}` |
| `order_constraints[]` | 前置、后置与互斥约束 |
| `supports_preview` | 是否支持预览 |

一期注册 `merge_filter`、`szz_label`、`d5_exclude`、`anomaly_exclude`、`label_validate`、`feature_align`、`log_transform`、`standardize`、`time_split`。

### POST /api/clean/run

`multipart/form-data`：`files[]` 上传一个 CSV/XLSX commits 主表，可附同 stem `.manifest.json`；`config` 为 JSON part。合计上传最多 64MiB，重试用的归一化 JSON 快照也最多 64MiB。主表不超过 2000 行且上传不超过 1MiB 时同步执行，其他输入创建 `kind=clean` 异步 job。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 已导入数据集的便利选择；显式上传优先，不读取被覆盖的 dataset_id |
| `template` | 否 | 已保存的命名模板；本次显式字段覆盖模板，执行时固化快照 |
| `mode` | 是 | `preview` / `apply` |
| `steps[]` | 是 | 有序数组，元素 `{op,enabled=true,params={}}` |
| `features[]` | 否 | 缺省为 Kamei 14 项；显式指定时至少含一个有效特征，空数组或未知特征返回 40001；preview/apply 均必须生成前后分布图 |
| `seed` | 否 | 默认 42；不得用于随机时间划分 |
| `split_ratio` | 否 | 默认 0.7，只允许时间序切分 |
| `format` | 否 | `csv` / `xlsx`，默认 `csv` |

同步响应 `data`：`{job_id,status,mode,outputs[],summary,error_log}`，状态为 success/failed；同类执行冲突时可转 queued。异步为 `{job_id,status:"queued"}`。`summary` 含 input_rows/output_rows、label_dist（positive/negative/null）、enabled_steps（启用操作列表）和 warnings；preview 的 output_rows 是模拟结果，不代表已生成 cleaned 文件。配置与输入校验失败在创建 job 前返回 40001；运行期时间边界或方法证据冲突记录 failed。

### GET /api/clean/preview/{job_id}

仅成功 apply 任务提供 `{columns,preview[]}`，最多 20 行，空标签为 null；preview 模式无主表，返回 40001。

### GET /api/clean/outputs/{job_id}/{name}

下载 manifest 登记文件；图片和 manifest 同样需要 `X-API-Key`，下载前复核 owner、大小和 checksum。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知操作、参数越界、顺序冲突、非法 schema、公式注入、随机切分、同 kind 冲突、文件名非法 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 可选 dataset、job 或输出不存在 |
| 50000 | 500 | 未预期错误；运行期失败写 job 脱敏日志 |

## 3. 输入契约

输入主表严格引用 [../file-contracts.md](../file-contracts.md) §3.1：

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

CSV/XLSX 解析为同一内部记录结构。校验大小、扩展名与魔数、精确列序、类型、40 位小写 hash、UTC 时间和公式注入；缺列、重复 hash、非法时间拒绝。输入 manifest 如提供必须同 stem、checksum 一致并声明 feature_version；未提供时只按本契约的 v1/log_v1 处理，并记录缺少来源版本证据的警告。merge_filter 仅识别 parent_hash 中多个有效父哈希，不从提交信息猜合并；未过滤的多父记录不得进入 apply 主表。

SZZ 操作只复核、复用文件已有方法标签，不运行 Git blame、不重打标签；方法不匹配拒绝，缺方法证据保留已有真标签并警告。D5 使用原 02 脚本判据，只排除同方法、NULL 的修复候选；原因明确为文件缺回溯证据，不冒称本次 SZZ 实测。原有正标签修复提交保留。

log_transform 对本契约已变换的输入报告跳过，禁止二次 log 或有损逆变换。standardize 不受图特征选择影响，始终处理 fix 之外 13 项；仅用最终过滤后的时间序训练部分拟合，完整 scaler、训练哈希与边界写入 manifest，结果登记独立 v1-standardized 版本。注册表要求 feature_align 先于 log/standardize，标准化后不再删行，time_split 最后；同秒跨边界拒绝，0/1 行分别记录空数据/仅训练侧警告，不假造测试样本。

## 4. 输出契约

§3.2 逐字规定：**“列同 3.1；另必伴 `steps_stats.json`（每步 rows_before/after/removed/label_dist/elapsed_ms/excluded_samples）与特征前后分布图 png。处理链配置快照入 manifest。”** 因而 apply 主表完整保留 §3.1 列，不自创清洗列。

| 模式 | 文件 | 命名 |
|---|---|---|
| preview | 逐步统计 | `clean_steps_stats_<job_id>.json` |
| preview / apply | 特征统计与直方图数据 | `clean_feature_stats_<job_id>.json` |
| preview / apply | 指定特征前后分布图 | `clean_feature_distribution_<feature>_<job_id>.png` |
| preview / apply | manifest | 每个基础产物同 stem `.manifest.json`；CSV/XLSX 共用同一份 |
| apply | cleaned 主表 | `clean_cleaned_<job_id>.csv` 和 `.xlsx`；format 决定优先格式 |
| apply | 逐步统计与分布图 | 命名同 preview，全部登记在同一 manifest |

`steps_stats.json` 每步必须含 `rows_before/after/removed/label_dist/elapsed_ms/excluded_samples`；`excluded_samples` 记录 hash 与原因。preview/apply 均至少输出一组指定特征的前后分布图，省略 `features[]` 时默认覆盖 Kamei 14 项；清洗后无样本时图中明确标注空数据，不伪造分布值。manifest 严格符合 §3.9，记录完整处理链、种子、特征版本、输入输出 checksum 和代码版本。CSV UTF-8 BOM，XLSX 单 sheet，未打标保持空值。

## 5. 可配置项

- `clean.chain_templates`：命名处理链模板，包含步骤顺序、启停与参数，持久化于 `user_config`。
- 单次运行可覆盖模板、模式、指定特征、种子、时间序比例和输出格式；跨键与操作参数按 operations schema 校验。
- SZZ 关键词不作为 clean 第二份配置；仅选择复用 collect 的 `szz` / `szz_lite` 方法。
- `.env` 仅提供出厂默认；模板写入后重启恢复。

## 6. 状态持久化

- 同步和异步运行均生成 `job_id` 并记录终态或五态生命周期，kind 为 `clean`；同 kind 通过 job 表条件更新互斥。
- 重启遗留 running 置 failed，保留完成步骤与脱敏日志，可 retry/cancel；preview 与 apply 均不得留下可被误认为成功的半成品。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；job `output_ref_json` 登记文件、模式与 checksum。
- 输入、模板与种子进入 manifest；同输入同配置的主表、PNG 与数值结果一致，elapsed_ms、执行时间和 job_id 是真实运行元信息，不要求跨运行字节一致。展示导入由调用方另调 storage。

## 7. 验收

验收夹具为测试内联合成的 AI 生成未审核数据（`data_model/tests/test_clean.py`、`backend/tests/test_clean_api.py`、`test_clean_real.py`），数据库为空且 collect 未运行也可验收。

- **正常**：上传标准 commits 文件，preview 得到逐步统计和分布图；apply 得到 §3.2 主表、统计、图、manifest，列序和 checksum 完整。
- **边界**：空标签、全正/全负、重复处理链、禁用全部可选步骤、70/30 小样本边界均如实统计；preview 不产 cleaned，未打标不变 0。
- **非法**：缺列、错类型、公式注入、超限文件、伪装 XLSX、未知 op、顺序冲突、随机切分、空 features 数组或未知特征均返回 40001，不保留半成品；省略 features 时默认生成 Kamei 14 项前后图。
- 默认参数下 14 维口径与 SZZ 结果不变；CLI/API 同 fixture 等价；输出下载鉴权，重启后配置和 job 状态可恢复。

## 8. 边界

clean 与 collect/train 的关系仅为 §3.1/§3.2 schema 兼容。`dataset_id` 是可选便利输入，不构成数据库前置；本模块不调用训练服务，也不依赖上游服务进程或内存。
