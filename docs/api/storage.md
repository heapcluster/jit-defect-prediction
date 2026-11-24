# 数据库存储与导入导出 API（storage）

一句话：把符合权威 schema 的交换文件按内容自动识别并幂等 upsert 到 12 表，同时按表导出 CSV/XLSX 与 manifest，承担展示导入、配置和资产登记而非模块间数据传递。

实现状态：已实现　期次：一期

W2 已实现文件导入、模型包/PNG 登记、12 表导出和产物下载。模型包只做结构/checksum 校验与不透明登记，不执行权重；已加载模型禁止被新包重标，后续加载管理由 W6 完成。

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1–§3.9；表字段以 [../database/README.md](../database/README.md) 与各表文档为准。

## 1. 职责与不负责范围

- 负责 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit` 12 表的导入、导出、展示查询支持与资产登记。
- 导入按文件 schema 自动识别目标，不要求调用方指定表；自然键幂等 upsert，重复导入不产生重复行。
- 配置和 job 状态仍持久化；模型包登记后派生 model 行，文件本体继续落输出目录。
- 不负责采集、清洗、训练、预测、评估、解释或定位计算，也不要求任何模块先导入才能运行。

## 2. 端点契约

### GET /api/storage/tables

响应 `{items:[{name,columns,filters}]}`，表与列取自真实 12 表定义；前端以该元数据渲染可用表及适用筛选，不另造白名单。所有端点含下载均要求 X-API-Key，上传鉴权和请求总大小在 multipart 解析前校验。

### POST /api/storage/import

同步 `multipart/form-data`：`files[]` 上传一个或多个交换文件，`config` 为可选 JSON part。

| config 字段 | 必填 | 契约 |
|---|---|---|
| `dataset_id` | 否 | 导入 collected_commits / clean_dataset 时关联既有 dataset；不存在返回 40400 |
| `create_dataset` | 否 | `{name,repo_source,branch,head_hash}`，需要新数据集时与 collected_commits / clean_dataset 同传 |
| `model_artifact_status` | 否 | 模型包登记初始状态，仅允许 `available` / `retired`，默认 available |
| `register_figures` | 否 | 默认 true；evaluate 图及 manifest 可登记 model_figure |

响应 `data`：`{items[],summary}`。每个文件项为 `{name,schema,target_tables[],status,inserted,updated,unchanged,rejected,errors[]}`；summary 汇总各状态数。单文件失败不影响其他合法文件，但同一文件的多表写入必须在一个事务内完成。

自动识别规则：

| 输入 | 权威 schema | 目标与约束 |
|---|---|---|
| collected_commits / clean_dataset | §3.1、§3.2 | dataset + dataset_commit；不写 commit_feature |
| train_testset | §3.3 | 测试集，按提交自然键登记 dataset_commit；每行带真标签 |
| predictions | §3.4 | prediction，按 `(commit_hash,model_name)` upsert；`is_bug_inducing` 透传真标签 |
| model_package | §3.3 | 校验后登记 model_artifact 并派生 model；checksum 不符拒绝 |
| evaluate 图及 manifest | §3.6、§3.9 | 按模型与 figure_type 登记 model_figure，路径只指允许输出根内文件 |
| metrics/confusion/report、explanations、localization/suggestions/patch | §3.6–§3.8 | 12 表无对应结果表，返回 40001 `unsupported_storage_schema`，不假装导入 |

### GET /api/storage/export

查询参数：`table=<12表之一>`（必填）、`format=csv|xlsx`（默认 csv）；可选 `dataset_id/model_name/start_time/end_time/limit` 只接受该表适用的筛选，未知、重复或不适用参数拒绝。同步返回 `data:{job_id,table,format,outputs[],manifest_name,columns,preview,row_count,total}`；preview 最多20行，limit 请求生成预览批次，完整下载重新请求不带 limit。job_id 只作导出批次标识，不新增 job kind。outputs 含主表与 manifest 的名称、字节数及 checksum。

### GET /api/storage/outputs/{job_id}/{name}

下载导出主表或 manifest；只允许导出批次登记的基础文件名。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | schema 无法识别、列/类型非法、自然键冲突、无目标表、checksum 失败、非法 table/format、公式注入 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括导出下载 |
| 40400 | 404 | dataset、导出批次或文件不存在 |
| 50000 | 500 | 数据库或未预期服务错误；事务回滚，不回显 SQL/连接串 |

## 3. 输入契约

所有交换列只接受 [../file-contracts.md](../file-contracts.md) §3.1–§3.8，不能通过增加别名绕过识别。关键 schema 逐字引用如下。

§3.1 collected_commits：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40 hex) | 是 | 提交标识（小写） |
| repo_name | string | 是 | 仓库名或数据集名 |
| repo_url | string | 否 | 来源 URL |
| author_name / author_email | string | 否 | 作者 |
| committed_at | datetime | 否 | 提交时间 UTC |
| message | string | 否 | 提交信息 |
| parent_hash | string(40) | 否 | 父提交 |
| is_bug_inducing | int 空可 | 是 | 缺陷标签 1/0/空 |
| label_method | string | 否 | `szz_v1` / `szz_lite` / `third_party` |
| label_source | string | 是 | `git_szz` / `public_dataset` |
| labeled_at | datetime | 否 | 打标时间 |
| fix_commit_hash | string(40) | 否 | SZZ 回溯修复提交 |
| source_type | string | 是 | `git_repo` / `public_dataset` |

§3.2 clean_dataset：列同 §3.1，可追加 `derive_basic_fields` 基础展示列；不得含 Kamei 14 维模型特征、`is_test` 或训练测试划分。必伴 `steps_stats.json` 与列统计/分布图，但统计和 png 不映射为数据库表。

§3.4 predictions：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40) | 是 | 提交 |
| model_name | string | 是 | 模型 |
| risk_score | float [0,1] | 是 | 概率（5 位小数） |
| predicted_label | int 0/1 | 是 | 按 decision_threshold 的二分类标签 |
| decision_threshold | float | 是 | 本次判定阈值 |
| model_version / feature_version | string | 是 | 版本元信息 |
| predicted_at | datetime | 是 | 预测时间 |
| is_bug_inducing | int 空可 | 否 | 透传真标签（来自 §3.3 `train_testset`，供 evaluate 算性能） |

§3.5 `labels.csv` 已废止：真标签统一由 §3.3 `train_testset` 提供并由 predict 透传进 §3.4 `predictions.csv`；storage 不再导入独立标签文件，导入 predictions 时按 hash 同步其透传标签，未打标保持 NULL。

§3.3：**“zip 内含：权重文件均为 `.pkl`（`expert`=Kamei 14 维、`semantic`=冻结头 CodeBERT 768 维）、`feature_order.txt`、`feature_schema.json`、`model_meta.json`（model_name/line/algo/feature_set/version_key/feature_version/trained_at/超参快照/划分 mode/种子）、`checksum.sha256`。`fused` / `e2e` 及其 safetensors 产物已取消。predict/explain MUST 校验 checksum 与特征列宽后再加载。”** storage 登记前同样校验 checksum。

安全要求：限制大小、扩展名与魔数、ZIP 解压大小和路径、列 schema、公式注入；存储路径限定允许输出根，文件名不拼接 shell。敏感配置、API Key、口令和 LLM Key 不允许通过 import 写入 user_config。

## 4. 输出契约

导入只返回 JSON 统计并写数据库，不创建新的交换文件；输入文件原有 manifest 不参与覆盖校验时不得伪造导入回执文件。

导出文件命名：

| 文件 | 命名 | 内容 |
|---|---|---|
| 表主文件 | `storage_<table>_<job_id>.csv`，或 `.xlsx` | table 对应数据库表契约的字段，按表定义顺序导出；不另造交换列名 |
| manifest | `storage_<table>_<job_id>.manifest.json` | 严格采用 §3.9，module=`storage`，config 记录 table/format，inputs 记录导出过滤条件，outputs 记录 checksum |

当导出内容用于模块交换时，必须选择并满足对应 §3.x，而不是把数据库内部字段改名后冒充交换文件：commit + commit_feature 的组合导出使用 §3.1，prediction 的交换导出使用 §3.4。单表原始导出只用于存储管理，不宣称可直接作为模块输入。

CSV 默认 UTF-8 BOM，XLSX 单 sheet，空标签和缺预测保持空值；公式注入转义。导出是同步批次，无独立 job kind，但文件仍落统一输出目录并必伴 manifest。

## 5. 可配置项

- storage 本身没有新增业务计算配置；table、format、dataset 关联和资产登记选项随请求给出并进入审计/manifest。
- 全局及模块命名空间配置统一经 [config.md](config.md) 读写；`.env` 仅提供出厂默认。
- 数据库连接、API Key 与其他密钥只走部署环境，禁止通过配置导入或导出接口读取。
- 导出行上限、文件大小与上传限制使用统一安全策略，不得为单表绕过。

## 6. 状态持久化

- 导入以单文件事务保证多表原子性；自然键 upsert 幂等，失败回滚该文件全部写入并返回可读 errors。
- 12 表持久保存展示数据、用户配置、六类 job 和资产；服务重启后配置与任务状态恢复。
- storage import/export 不新增 job kind；导出 job_id 是文件批次标识，不能用于 `/api/jobs/{id}`。
- 导出落 `backend/var/outputs/<job_id>/`（gitignore）；模型包可登记路径和 checksum，但权重文件内容不入库。

## 7. 验收

fixtures：`tests/fixtures/files/storage/`，包含各权威 schema、重复批次与非法文件，不要求任何业务模块先运行。

- **正常**：collected_commits、clean_dataset、train_testset、predictions、模型包分别自动识别到目标表；重复导入 inserted/updated/unchanged 统计合理，行数不重复；12 表均可导出并带 §3.9 manifest。
- **边界**：空标签、空预测、create_dataset、同事务多表写入、重复 model_name 版本均保持自然键与 NULL 语义；CSV BOM/XLSX 可打开。旧 `labels.csv` 必须被拒绝（40001），不得识别为标签输入。
- **非法**：未知 schema、无目标表、错列、checksum 失败、公式注入、非法 table/format、敏感配置导入均返回 40001；事务失败无部分写入。
- 模块在空库仍能独立运行；导入后 commits/trends 等展示端点可读；导出 checksum、命名和下载鉴权通过。

## 8. 边界

storage 是可选展示与持久化层，不是模块间总线。业务模块间仅依 §3.x 文件 schema 兼容；数据库有数据不是任何 run 端点的前置，dataset_id 也只是便利选择。模型行由 model_artifact 派生，配置与 job 单源仍由对应表承担。
