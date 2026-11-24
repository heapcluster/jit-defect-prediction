# 缺陷数据收集（功能 2）

实现状态：目标契约　期次：一期

> 旧实现中存在 14 维特征提取、70/30 切分和“可选导入库”口径；本文已按最新板块 2 定义重写，旧口径废止。本轮只修改设计文档，`infra/schema.sql`、ORM、服务和页面实现后续按本文同步。

## 一句话概述

独立的数据收集工具：用户指定 Git 仓库或公开标注数据集，系统完成仓库拉取或数据集导入，生成带缺陷标签的二维表，页面展示，默认保存数据库，并支持导出 CSV/XLSX。

## 1 职责与不负责范围

**负责**：

- Git 仓库模式：接收仓库路径/URL、分支、时间或提交范围、采集模式、SZZ 方法、数据集名称，完成拉取/读取、提交采集、SZZ 打标和二维表生成。
- 公开数据集模式：接收数据集文件/URL、许可证、来源说明、字段映射和标签值映射，把第三方已打标数据统一转换为本系统二维表。
- 生成统计信息和 manifest。
- 默认把二维表保存到数据库；数据库保存失败时保留文件产物并给出明确状态。
- 提供二维表预览、CSV/XLSX 导出、manifest 下载和数据集列表展示。
- 维护仓库路径/协议安全边界、数据集来源与许可证信息、SZZ 判据单源。

**不负责**：

- Kamei 14 维特征计算。
- 训练/测试集切分，`is_test` 不在本模块产出。
- 清洗处理链、标准化、归一化或特征变换。
- 训练、预测、评估、解释、定位、修复。
- 把数据库或环境变量中的固定仓库当作运行前提。
- 把公开数据集伪装成 SZZ 打标结果。

## 2 独立运行入口

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python data_model/preparation/collect.py git ...` | Git 仓库采集；默认保存数据库，可用 `--no-save` 关闭 |
| CLI | `python data_model/preparation/collect.py public ...` | 公开标注数据集导入；默认保存数据库 |
| 任务 API | `POST /api/collect/run` | `source_type=git_repo` 或 `public_dataset`，创建 `job.kind=collect` |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 五态、进度、脱敏日志、重试、取消 |
| 预览 | `GET /api/collect/preview/{job_id}` | 返回列名和前 20 行 |
| 下载 | `GET /api/collect/outputs/{job_id}/{name}` | 下载二维表、统计、质量报告、manifest |
| 数据集列表 | `GET /api/datasets` | 查看已保存数据集 |
| 重新保存 | `POST /api/collect/resave/{job_id}` | 文件已生成但数据库保存失败时重试保存，不重新采集 |

CLI 与 API 调用同一采集实现。CLI 可脱离 Web 页面运行；API 运行在统一任务与配置基础设施之上，但不要求上游模块先运行。

## 3 数据来源模式

### 3.1 Git 仓库模式

输入：

| 输入 | 必填 | 契约 |
|---|---|---|
| `repo_source` | 是 | 本地路径或 Git URL；本地路径须在允许根目录内，URL 协议须在白名单内 |
| `branch` | 否 | 分支/ref，缺省为仓库默认 HEAD |
| `start_time` / `end_time` | 否 | ISO 8601 UTC，限定输出提交范围 |
| `start_commit` / `end_commit` | 否 | 可检出的提交范围，可与时间范围组合 |
| `mode` | 否 | `full` / `incremental`，默认 `incremental` |
| `fetch_remote` | 否 | 默认 `true`；`false` 用本地 HEAD |
| `head_expect` | 否 | 期望 HEAD，不一致则拒绝 |
| `dedup` | 否 | 当前仅 `commit_hash` |
| `szz_method` | 否 | `szz_v1` / `szz_lite`，默认 `szz_v1` |
| `dataset_name` | 是 | 展示和保存用名称 |
| `save_to_db` | 否 | 默认 `true` |

处理链：

```text
仓库校验 → 拉取/读取仓库 → 采集提交 → SZZ 打标 → 生成二维表
→ 生成统计信息 → 默认保存数据库 → 生成 manifest → 提供导出
```

SZZ 输出只写标签字段，不写 Kamei 14 维，不生成 `is_test`。

### 3.2 公开标注数据集模式

输入：

| 输入 | 必填 | 契约 |
|---|---|---|
| `dataset_name` | 是 | 展示和保存用名称 |
| `source_url` 或上传文件 | 是 | CSV/JSON/ZIP，或可访问的数据集 URL |
| `license` | 是 | SPDX 标识或原始许可证说明 |
| `source_note` | 是 | 论文、项目主页、下载地址等来源说明 |
| `field_mapping` | 是 | 提交标识、时间、标签字段到系统字段的映射 |
| `label_mapping` | 是 | 原始标签值到 `1/0/null` 的映射 |
| `save_to_db` | 否 | 默认 `true` |

处理链：

```text
文件/URL 校验 → 字段映射 → 标签归一化 → 质量校验 → 生成二维表
→ 生成统计信息 → 默认保存数据库 → 生成质量报告和 manifest → 提供导出
```

公开数据集已有标签，本模式**不执行 SZZ**。标签来源记为 `public_dataset`。

公开数据集至少必须具备可映射的提交标识字段和标签字段；时间字段建议必填，缺失时在质量报告中明确标注，并禁止进入依赖时间排序的后续演示。

## 4 输出契约

### 4.1 二维表

文件名：

```text
collected_commits_<job_id>.csv
collected_commits_<job_id>.xlsx
```

列定义：

| 列 | 类型 | 必填 | 含义 |
|---|---|---|---|
| `commit_hash` | string(40 hex) | 是 | 提交标识，小写 |
| `repo_name` | string | 是 | 仓库名或数据集名 |
| `repo_url` | string | 否 | 仓库 URL 或数据集来源 URL |
| `author_name` | string | 否 | 作者 |
| `author_email` | string | 否 | 作者邮箱 |
| `committed_at` | datetime | 否 | 提交时间，UTC ISO 8601 |
| `message` | string | 否 | 提交信息 |
| `parent_hash` | string(40) | 否 | 父提交 |
| `is_bug_inducing` | int 空可 | 是 | 标签：1/0/空 |
| `label_method` | string | 否 | `szz_v1` / `szz_lite` / `third_party` |
| `label_source` | string | 是 | `git_szz` / `public_dataset` |
| `labeled_at` | datetime | 否 | 打标时间或来源时间 |
| `fix_commit_hash` | string(40) | 否 | SZZ 回溯到的修复提交 |
| `source_type` | string | 是 | `git_repo` / `public_dataset` |

硬约束：

- 不出现 Kamei 14 维特征列（`ns,nd,nf,entropy,la,ld,lt,fix,ndev,age,nuc,exp,rexp,sexp`）。
- 不出现 `is_test`。
- 未打标 `is_bug_inducing` 保持空值，MUST NOT 写 0。
- CSV 使用 UTF-8 BOM；XLSX 单 sheet；表头 ASCII snake_case。

### 4.2 统计信息

```text
collect_summary_<job_id>.json
```

至少包含：

- `source_type`、`source_url`、`dataset_name`。
- `label_source`、`szz_method` 或第三方标签说明。
- `total_rows`、`positive_rows`、`negative_rows`、`unlabeled_rows`。
- `duplicate_rows`、`skipped_rows`。
- Git 模式的分支、HEAD、时间/提交范围。
- 公开数据集模式的许可证、来源、字段映射摘要。
- `save_db_status`、`dataset_id`。

### 4.3 质量报告

公开数据集模式额外生成：

```text
collect_quality_<job_id>.json
collect_quality_<job_id>.md
```

至少包含：

- 缺失率。
- 重复提交数。
- 标签冲突数。
- 时间异常数。
- 字段映射表。
- 异常样本示例和处置建议。

### 4.4 manifest

每个主产物同名 manifest：

```text
collected_commits_<job_id>.manifest.json
```

字段遵循 file-contracts §3.9，并补充：

- `source_type`
- `label_source`
- `license`（公开数据集）
- `source_url`
- `save_db_status`
- `dataset_id`

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `collect.allow_roots` | `user_config` | Git 本地路径与克隆目录允许根 |
| `collect.protocol_whitelist` | `user_config` | 默认只允许 https/git |
| `default_dataset` | `user_config` | 仅便利选择，不是运行前提 |
| Git 采集参数 | 本次 run | 完整快照入 `job.params_json` 与 manifest |
| 公开数据集字段映射 | 本次 run | 必须显式声明，不允许静默猜测 |
| 标签值映射 | 本次 run | 必须覆盖输入中出现的所有原始标签值 |
| `save_to_db` | 本次 run | 默认 `true` |
| 输出格式 | 本次 run | CSV 默认，XLSX 可选/同批生成 |

## 6 状态与持久化

- `job.kind=collect`，五态 `queued / running / success / failed / cancelled`。
- 进度阶段：拉取/导入、采集/映射、SZZ 或标签归一化、生成二维表、保存数据库、生成导出文件。
- 同 kind 同一时刻最多一个 running。
- 进程重启遗留 running 置 failed，保留进度和脱敏日志，可重试。
- 输出落 `backend/var/outputs/<job_id>/`。
- 默认保存数据库：成功后写 `dataset` 与 `dataset_commit`。
- 若文件生成成功但数据库保存失败：
  - `job.status=failed`；
  - `error_log` 写明保存失败原因；
  - 文件产物仍可下载；
  - 页面提供“重新保存”入口。
- 相同输入与配置重跑应产生等价二维表；同一数据集内按 `commit_hash` 幂等。

## 7 与其他模块边界

- clean/train 后续只消费本模块产出的 `collected_commits.csv`，不再假设其中包含 Kamei 14 维和 `is_test`。
- 板块 3 负责特征提取、清洗和预处理；切分训练/测试集归板块 4 训练配置。
- 本模块不调用 clean/train/predict/evaluate/explain/localization。
- storage 只是本模块默认落库的实现支撑，不替代文件产物；公开数据集也必须落盘文件与 manifest。
- 数据集列表是保存结果展示，不参与模块间文件 handoff。

## 8 验收标准

- 用户可填写任意合法本地仓库路径或 Git URL 并发起收集，不修改环境变量。
- 系统完成拉取、提交采集和 SZZ 打标，输出二维表不含 14 维特征和 `is_test`。
- 未打标样本保持空值，不被写成 0。
- 公开数据集可通过字段映射导入，标签来源标记为 `public_dataset`，不执行 SZZ。
- 二维表默认保存数据库，数据集列表可查询；保存失败时文件仍可下载且可重试保存。
- CSV/XLSX 可打开、中文不乱码，内容与数据库二维表一致。
- summary、quality（公开数据集）、manifest 均可下载，checksum 一致。
- 同配置重复运行无重复成员；仓库越界、协议非法、字段缺失、标签映射不完整、HEAD 不符均有明确错误。
- job 五态、取消、重试、重启中断恢复均通过。
