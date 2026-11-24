# dataset / dataset_commit

`实现状态：部分　期次：一期`

W2 已实现文件展示导入、数据集成员关联、真实样本统计、只读查询与交换导出；一期仍为单版本展示库，采集/清洗生产任务随 W3/W4 接入。

**一句话**：数据集元数据表 + 数据集与提交关联表；把仓库快照变成可登记、可查询、可导出的数据集，是收集（TODO/02）、清洗（TODO/03）、批量预测（TODO/05）、评估（TODO/06）的共同输入。

分期：一期单版本（`dataset_commit` 联合主键幂等）；二期多版本时 `dataset_commit` 增加 `feature_version` 列并进入主键，承载同一提交在不同处理链版本下的特征。

**公开数据集不入库**：课程附加功能 (3) 的公开 JIT 缺陷数据集落盘 `data_model/data/public/<name>/` 独立文件 + 来源/许可证/获取日期元数据，**不写 `dataset` / `dataset_commit` 表**；本表只登记 Git 采集（功能 2）与清洗 apply（功能 3）产出的数据集。加载与质量治理契约见 [`../function_point/collect.md`](../function_point/collect.md) §9。

**角色降级（文件化主叙事）**：本表是「导入 / 登记供展示与便利选择」的资产台账，**不是模块间 handoff 通道**——train/predict/evaluate 等模块独立运行吃交换文件（[`../file-contracts.md`](../file-contracts.md)），`dataset_id` 仅作 run 端点的可选便利输入；模块验收不依赖本表有记录。

## dataset 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| dataset_id | VARCHAR(36) | NOT NULL | 主键 | 数据集标识 |
| name | VARCHAR(128) | NOT NULL | — | 显示名 |
| repo_source | VARCHAR(255) | NOT NULL | — | 仓库本地路径或 URL（经安全校验） |
| branch | VARCHAR(128) | 可空 | — | 分支 / ref |
| head_hash | CHAR(40) | 可空 | — | 采集时 HEAD |
| time_start | DATETIME | 可空 | — | 采集时间范围起（可空 = 全量） |
| time_end | DATETIME | 可空 | — | 采集时间范围止 |
| mode | VARCHAR(16) | NOT NULL DEFAULT 'full' | — | `full` / `incremental` |
| sample_count | INT | NOT NULL DEFAULT 0 | — | 样本数 |
| pos_count | INT | NOT NULL DEFAULT 0 | — | 正样本数（打标成功口径） |
| neg_count | INT | NOT NULL DEFAULT 0 | — | 负样本数（打标成功口径） |
| status | VARCHAR(16) | NOT NULL DEFAULT 'collecting' | — | `collecting` / `ready` / `failed` / `archived` |
| job_id | VARCHAR(36) | 可空 | 外键 → `job.job_id` | 产出该数据集的收集任务 |
| created_at | DATETIME | NOT NULL | — | 创建时间 |

## dataset_commit 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| dataset_id | VARCHAR(36) | NOT NULL | 联合主键 + 外键 → `dataset.dataset_id` | 所属数据集 |
| commit_hash | CHAR(40) | NOT NULL | 联合主键 + 外键 → `commit.commit_hash` | 成员提交 |

## 主键与约束理由

- `dataset_id` 自然主键；`job_id` 外键可空（交付导入的数据集可无收集任务）。
- `dataset_commit` 联合主键 `(dataset_id, commit_hash)`：一个提交在同一数据集内一行，重复收集幂等；双外键保证成员必须是已登记提交。
- 一期 `is_test` 与 14 维特征仍读 `commit_feature`（一个提交一行特征）；数据集只承载成员关系与元数据。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 收集服务（`job.kind=collect`）、清洗 apply（`job.kind=clean`，产出新 dataset 行） | 登记数据集与成员 |
| 读取 | 数据集列表 / 详情 / 导出 API、批量预测目标选择、评估输入、风险列表按数据集筛选 | 数据集选择与展示 |
| 展示 | 数据集列表（名称 / 来源 / 时间范围 / 样本数 / 正负比 / 状态）、详情（成员样本 + 特征 + 标签 + is_test）、导出按钮 | 数据集可见可导 |

## 口径

- **默认数据集** = Apache Camel `camel-4.23.0` 快照（HEAD `b2329103df8f5d1edfca2ad262be09e3be95ee68`）的登记行；默认数据集可经 `user_config.default_dataset` 配置。
- **仓库安全校验**：本地路径限定配置允许的根目录内；URL 仅 https / git 协议白名单；MUST NOT 把用户输入拼进 shell 字符串。
- **增量与去重**：`mode=incremental` 只补差集，不破坏已有标注；同配置重复收集 MUST NOT 产生重复成员。
- **正负样本口径**：`pos_count / neg_count` = 打标成功样本中的正 / 负数；未打标 `NULL` 不计入任何一方。
- **导出**：CSV / XLSX，字段含提交元信息、14 维、标签、可选预测结果；CSV 带 UTF-8 BOM（Excel 中文不乱码）；XLSX 依赖 `openpyxl` 锁版进入 `data_model/environment.yml`；响应带正确 `Content-Disposition`。
- 清洗 apply 生成新 dataset 行承载处理结果，原数据集不被覆盖；完整处理配置与输入输出关系随任务入参快照（`job.params_json`）与产出引用可追溯。

## 验收

- 页面输入仓库发起收集 → `dataset` 行 + 成员行落库，状态与样本数可查询。
- 同配置重复收集：成员数不变、无重复行。
- 导出 CSV / XLSX 字段完整、中文不乱码、筛选条件生效。
- 清洗 apply 后原数据集不被覆盖；`pos_count + neg_count ≤ sample_count`，未打标样本不计入正负。