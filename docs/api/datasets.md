# 数据集查询与导出 API（datasets）

一句话：查询经 storage 导入的数据集及成员，并把成员按 commits 或 predictions 权威 schema 导出为 CSV/XLSX 与 manifest。

实现状态：已实现　期次：一期

W2 已实现列表、详情、成员过滤与 CSV/XLSX 交换导出；计数基于真实成员，未打标不计入正负比例。label_method 未存入当前表，导出留空并在 manifest 标注来源不可恢复，不补造方法。

文件契约唯一权威：[../file-contracts.md](../file-contracts.md) §3.1、§3.4、§3.9；导入见 [storage.md](storage.md)。

## 1. 职责与不负责范围

- 负责 dataset 列表、详情、成员分页、标签/划分/特征展示和文件导出。
- 仅读取 dataset、dataset_commit、commit、commit_feature、prediction 等已导入数据；查询不触发采集、清洗或预测。
- 不负责创建计算结果；collect/clean 的文件可先独立交付，再由 storage 可选导入形成数据集。
- dataset_id 在 run 端点只是便利输入，数据集接口不是任何模块运行前置。

## 2. 端点契约

### GET /api/datasets

参数：`page=1`、`size=20`（1≤size≤100）、`status=collecting|ready|failed|archived`、`q`。响应 `{total,page,size,items[]}`；每项：

`dataset_id,name,repo_source,branch,head_hash,time_start,time_end,mode,sample_count,pos_count,neg_count,status,job_id,created_at`。

### GET /api/datasets/{dataset_id}

响应字段同列表项，另含 `pos_rate`、`label_method`、`created_at`。pos_rate 只以已打标正负样本为分母，未打标不计入。

### GET /api/datasets/{dataset_id}/commits

参数：`page`、`size`、`is_test=0|1`、`with_features=0|1`（默认 1）、`start_time`、`end_time`。响应 `{total,page,size,items[]}`，成员包含：

- `commit_hash,repo_name,author_name,author_email,committed_at,message,parent_hash`；
- with_features=1 时包含 §3.1 的 `ns…sexp（14 列）` 与 `label_method`；
- `is_bug_inducing` 为 1/0/null，`labeled_at`、`is_test` 按 §3.1。

### GET /api/datasets/{dataset_id}/export

同步生成导出批次，参数：

| 参数 | 必填 | 契约 |
|---|---|---|
| `format` | 否 | `csv` / `xlsx`，默认 csv |
| `artifact` | 否 | `commits`（默认）/ `predictions` |
| `model_name` | predictions 时是 | 选择已导入预测模型 |
| `decision_threshold` | 否 | predictions 导出时用于生成本次文件标签，缺省读全局 decision_threshold |
| `is_test` | 否 | 0/1 成员筛选 |
| `start_time` / `end_time` | 否 | 提交时间闭区间 |

响应 `data:{job_id,dataset_id,artifact,format,outputs[]}`；job_id 仅为导出批次标识，不新增 job kind。

### GET /api/datasets/outputs/{job_id}/{name}

下载导出主表或 manifest，禁止未登记名称与路径穿越。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 分页/筛选/时间/format/artifact 非法，predictions 缺 model_name，下载名非法 |
| 40100 | 401 | 缺失或错误的 `X-API-Key`，包括下载 |
| 40400 | 404 | dataset、模型、导出批次或输出不存在 |
| 50000 | 500 | 未预期读取或导出错误，不回显 SQL/路径 |

## 3. 输入契约

查询输入为 dataset_id 和筛选参数；导出内容只读已导入行，不接收任意列选择或自定义 SQL。所有筛选共用同一解析逻辑，页面成员与导出结果一致。

commits 导出严格采用 §3.1：

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

predictions 导出严格采用 §3.4：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| commit_hash | string(40) | 是 | 提交 |
| model_name | string | 是 | 模型 |
| risk_score | float [0,1] | 是 | 概率（5 位小数） |
| predicted_label | int 0/1 | 是 | 按 decision_threshold 的二分类标签 |
| decision_threshold | float | 是 | 本次判定阈值 |
| model_version / feature_version | string | 是 | 版本元信息 |
| predicted_at | datetime | 是 | 预测时间 |
| is_bug_inducing | int 空可 | 否 | 透传真标签（便于 evaluate 单文件输入） |

导出执行 CSV 公式注入转义，缺预测或未打标保持空值，禁止填 0；14 维仍为 log 变换值（fix 除外）。predictions 导出的 predicted_label/decision_threshold 按本次导出阈值生成，model_version/feature_version 从登记模型取得，is_bug_inducing 从 commit_feature 透传；这些派生规则与阈值一并写入 manifest。

## 4. 输出契约

| artifact | 主文件 | manifest |
|---|---|---|
| commits | `datasets_commits_<job_id>.csv`，或 `.xlsx` | `datasets_commits_<job_id>.manifest.json` |
| predictions | `datasets_predictions_<job_id>.csv`，或 `.xlsx` | `datasets_predictions_<job_id>.manifest.json` |

列只能使用上述 §3.1/§3.4，不把两类列混成一张私有宽表。CSV UTF-8 BOM，XLSX 单 sheet；manifest 严格采用 §3.9，module=`datasets`，config 记录 dataset/artifact/model/筛选，inputs 记录源行版本，outputs 记录 checksum。

列表、详情和成员查询只返回 JSON，不创建文件；只有 export 创建输出批次，主文件必伴 manifest。

## 5. 可配置项

- `default_dataset` 只提供选择器默认值；显式 id 优先，空库不影响上传文件运行。
- 查询可配置分页、状态、关键字、is_test、时间、特征开关和导出 artifact/format/model。
- 页面页大小等偏好存 `page_prefs`，重启恢复；不得在查询中隐藏业务计算参数。
- `.env` 仅提供出厂默认，不指定唯一可用数据集。

## 6. 状态持久化

- dataset/dataset_commit 与展示行由 storage 持久化，服务重启后查询一致；归档只改变状态，不删除成员。
- export 同步执行，不创建第六类之外的 job；job_id 仅用于输出目录与下载，不能用于 jobs API。
- 输出落 `backend/var/outputs/<job_id>/`（gitignore）；导出完成后 checksum 与 manifest 一起持久化。
- 查询和导出不改 commit_feature/prediction，不补标签、不补预测，也不覆盖原始数据集。

## 7. 验收

fixtures：`tests/fixtures/files/datasets/`，以 commits/predictions 文件先经 storage 导入构造展示数据，同时验证空库查询不触发业务模块。

- **正常**：列表/详情/成员统计一致，commits 与 predictions 两种导出逐列满足 §3.1/§3.4，manifest/checksum/BOM/XLSX 通过。
- **边界**：空数据集、全空标签、缺预测、时间端点、is_test 筛选、大结果分页均无漏行/重行，空值不写 0。
- **非法**：未知 id/model、错误 format/artifact、非法时间、分页越界、下载路径穿越返回 40001/40400，不产半成品。
- 导出筛选与成员视图一致；不新增 job kind；所有查询与导出不调用 collect/predict/evaluate。

## 8. 边界

datasets 是展示导入后的读模型与导出面，不是运行数据源的唯一形态。模块间只依文件 schema 兼容；storage 导入可提供便利选择，但任何 run 都能直接上传输入，数据库与 dataset_id 均非前置。
