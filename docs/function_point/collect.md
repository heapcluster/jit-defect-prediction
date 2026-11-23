# 缺陷数据收集（功能 2）

实现状态：已实现　期次：一期

W3 已实现 Git 收集与公开数据离线加载/质量工具；HTTP 使用持久队列，CLI 不连业务库。未获取符合字段与许可要求的公开 benchmark，本次仅完成真实来源探测及现有 Camel 文件加载自验，不宣称公网数据集或模型性能验收通过。

## 一句话概述

独立的数据采集工具：从用户指定的本地 Git 仓库或 URL 产出带 Kamei 特征、SZZ 标签和时间序划分的 `commits.csv`，并另行提供公开 JIT 缺陷数据集的离线加载与质量治理。

## 1 职责与不负责范围

**负责**：

- 接收仓库路径/URL、分支、提交或时间范围、拉取策略、数据集名称和去重策略，完成克隆或本地解析、提交采集、SZZ 标注、Kamei 14 维特征提取和时间序划分。
- 管理收集任务的进度、日志、取消和重试；重复运行按 `commit_hash` 去重，增量采集不破坏既有标注。
- 产出可下载的 CSV/XLSX 数据集、采集统计与 manifest；需要页面展示时再显式导入 storage。
- 维护 SZZ 判据单源、仓库路径与协议安全边界，以及公开数据集离线质量治理（§9）。

**不负责**：

- 可配置清洗处理链、训练、预测、评估、解释、定位或阈值管理。
- 完整源码浏览、第三方平台 OAuth、公开数据集入库或替换 Apache Camel 基线。
- 把某个环境变量、某个仓库或库中既有数据当作运行前提。

## 2 独立运行入口

```bash
python data_model/preparation/collect.py run \
  --repo /path/to/repo --branch main --name my-dataset \
  --start 2024-01-01T00:00:00Z --end 2024-12-31T23:59:59Z \
  --mode incremental --fetch-remote false --allow-root /path/to --out ./out
python data_model/preparation/collect.py export \
  --input ./out/<job_id>/collect_commits_<job_id>.csv --format xlsx --out ./out
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `python data_model/preparation/collect.py run/export`，或从 data_model 运行 `python -m preparation.collect` | 仓库、显式允许根目录与输出目录即可运行，不连业务库，与 API 共用采集实现 |
| 任务 API | `POST /api/collect/run` | 创建 `kind=collect` 任务并返回 `job_id`；可选 `dataset_id` 仅用于已导入数据的增量便利输入 |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 查询五态、进度与脱敏日志，重试或取消 |
| 下载 | `GET /api/collect/outputs/{job_id}/{name}` | 下载数据集、统计与 manifest |
| 展示导入 | `POST /api/storage/import` | 可选；导入后才由数据集查询与展示页读取 |

所有 HTTP 端点（含文件下载与后续展示读取）必须使用 `X-API-Key`。Git 调用使用参数数组，禁止把仓库、分支或范围拼入 shell。

## 3 输入契约

| 输入 | 必填 | 校验与语义 |
|---|---|---|
| `repo_source` | 是 | 本地路径须位于 `collect.allow_roots`；URL 须符合 `collect.protocol_whitelist`；URL 克隆到允许根目录内独立目录 |
| `branch` / `start_commit` / `end_commit` | 否 | 校验安全 ref 与祖先闭范围；缺省取仓库默认 HEAD |
| `start_time` / `end_time` | 否 | ISO 8601 UTC，仅限制输出提交，不截断历史特征所需前序历史 |
| `mode` / `dedup` | 否 | `full` / `incremental`，默认增量；按提交哈希幂等去重 |
| `fetch_remote` / `head_expect` | 否 | 可关闭联网以使用本地 HEAD；HEAD 不符明确拒绝；所有克隆在受控目录进行，不改用户检出 |
| `dataset_name`（CLI `--name`） | 是 | 输出数据集显示名，写入统计与 manifest |
| `dataset_id` | 否 | 仅 run 端点的已导入数据集便利选项；文件与仓库输入始终可独立使用 |
| `szz_method` | 否 | `szz` / `szz_lite`；复用本模块单源判据，输出列名仍为 label_method |

- 输出表格遵循 [`../file-contracts.md`](../file-contracts.md) §3.1 `commits.csv`，不自定义列名；CSV/XLSX 解析、UTF-8 BOM、公式注入防护、空标签与文件安全遵循 §1。
- SZZ v1 沿用原 02 判据：`CAMEL-数字` 且词首边界 `\b(fix|bug|patch)`；双方法分开报告。无匹配修复时全空标签，不把其他仓库无适配判据误作负样本；clean 的 `szz_label` 只能复用本实现。
- Kamei 14 维列序和 log 变换口径固定，`fix` 不做 log；时间序默认 70/30，禁止随机划分；`is_bug_inducing` 未打标保持空值，不能写成 0。

## 4 输出契约

| 输出 | 文件与内容 |
|---|---|
| 原始数据集 | `collect_commits_<job_id>.csv`，可选 `collect_commits_<job_id>.xlsx`；schema 逐字遵循 §3.1 |
| 采集统计 | `collect_summary_<job_id>.json`：仓库、分支、HEAD、范围、总数、成功/失败数、正负与未打标数、划分边界、SZZ 方法 |
| 字段与质量记录 | `collect_audit_<job_id>.json`：去重数、跳过原因、HEAD 校验、错误摘要；不包含凭证 |
| manifest | 每个产物伴同名 `collect_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录输入快照、配置、代码版本和 checksum |

所有文件命名遵循 `<module>_<artifact>_<job_id>.<ext>`。可选导入 storage 后可获得数据集记录与成员展示，但 `dataset_id` 不是文件交付的替代物。未打标样本不计入正样本或负样本；可选附加预测列只能来自已有 predictions 文件，缺失留空。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `collect.allow_roots` | `user_config` 命名空间键 | 本地仓库与克隆目录允许根；变更留审计并重启恢复 |
| `collect.protocol_whitelist` | `user_config` 命名空间键 | 仅允许显式登记的 https/git 协议 |
| `default_dataset` | `user_config` 全局键 | 仅作展示和便利选择，不是采集前置 |
| 仓库、分支、范围、HEAD、全量/增量、去重 | 本次 run 配置 | 每次任务独立指定，完整快照入 job 与 manifest |
| `label_method` 与 SZZ 参数 | 本模块判据注册表 + run 覆盖 | 双方法分别报告，关键词与词首边界不可另写副本 |
| 导出格式与字段范围 | run/export 参数 | CSV 默认、XLSX 可选；交换列仍以 §3.1 为准 |
| 时间序比例 | run 配置 | 默认 70/30，禁止随机，保留严格时间边界断言 |

## 6 状态持久化

- `job.kind=collect`，仅使用 `queued / running / success / failed / cancelled`；进度、入参快照、输出引用、重试次数和脱敏错误日志落 `job` 表。
- 同 kind 同时最多一个 running，以数据库条件更新实现；进程重启将遗留 running 置 failed，可从已持久化进度重试。
- 输出落盘 `backend/var/outputs/<job_id>/`，该目录整体加入 gitignore；相同仓库快照与相同配置重跑应得到等价数据文件，重复导入不会重复登记提交。
- 仓库配置、SZZ 判据版本、特征版本、采集范围、HEAD 和输出 checksum 写入配置快照与 manifest；`collect.*` 配置落 `user_config`，重启恢复。
- 数据集入库是可选的展示登记；未导入时，job 状态与文件仍可查询、下载和复现。

## 7 与其他模块边界

- clean/train 只需接收符合 §3.1/§3.2 的文件；predict/evaluate 等也只按各自输入 schema 握手。收集模块在线或 storage 有数据均不是它们运行的前提。
- SZZ 判据单源在本模块；clean 的 `szz_label` 复用判据，其他模块不得复制。Kamei 特征抽取同样复用唯一实现。
- 本模块输出可由 storage 可选导入，用于数据集列表和展示页；它不在模块之间承担消息转发。
- 原集中数据同步职责中的“导入库展示”归 storage；本模块只负责采集与文件交付，模型性能计算归 evaluate。

## 8 验收标准

fixtures 位于 `tests/fixtures/files/collect/`，含正常、边界、非法三类本地 Git 仓库与输入描述；CLI 和 API 各运行一次，不要求 clean/train 或库中已有数据。

- 页面或 CLI 指定仓库即可收集，无需修改环境变量；同一 fixture 的两种入口产生等价 §3.1 文件、统计与 manifest。
- 重复收集无重复提交，增量运行保留原标注；路径越界、协议越界、非法 ref、HEAD 不符和公式注入有明确错误，不产半成品。
- CSV/XLSX 可正常打开且中文不乱码；14 维列序与 log（`fix` 除外）、SZZ 双方法、时间序 70/30 禁随机、NULL 标签均逐值验证。
- 失败日志可读且脱敏，取消、重试、同 kind 互斥、重启 running 置 failed 均通过；可选导入后能查询数据集和样本，不导入不影响下载。
- 承接 TODO/02：仓库可配置、任务五态、失败重试、幂等、CSV/XLSX 导出和 Camel 采集能力均有独立测试；大数据量导出覆盖分页与筛选。

## 9 公开缺陷数据集加载与质量治理

> 承接 [`../../openspec/changes/public-dataset-quality/proposal.md`](../../openspec/changes/public-dataset-quality/proposal.md)、`design.md`、`tasks.md` 与 `specs/public-dataset/spec.md`。该变更目录只作为需求依据，不在本次文档重写中修改。

### 9.1 定位与独立入口

公开数据用于验证加载与处理能力、示范质量治理、提供与 Apache Camel 采集并列的对照素材；不用于宣称交付模型可跨仓库迁移，不替换 Camel 基线，不进入在线交付链。

```bash
python -m preparation.public_load \
  --name <dataset> --source <url|path> --license <spdx> \
  --out data_model/data/public/<dataset>
python -m preparation.public_quality \
  --name <dataset> --input data_model/data/public/<dataset> --out ./out
```

两个命令与收集服务复用字段映射口径，但使用独立离线入口，不新增业务 API、不改交付模型。加载器必须具有 commit 标识、标签和时间戳；缺任一项即指出缺列并终止，不用默认值补齐，不留下半成品。

### 9.2 独立文件、映射与元数据

- 原始/归一记录、字段映射和元数据落盘 `data_model/data/public/<name>/`；任务报告、下载副本与 manifest 同时写入 `backend/var/outputs/<job_id>/`，全部使用 `collect_public_<artifact>_<job_id>.<ext>` 命名。探测与质量报告另按 openspec 归档为 `data_model/preparation/reports/public_dataset_probe.md` 和 `public_dataset_quality.md`。
- 元数据至少记录来源、许可证、获取日期、原始体积、是否抽样、抽样方法与层级边界；字段映射表逐项记录公开字段到契约字段的关系，标签语义冲突显式列出，不静默对齐。
- 公开记录保持独立文件，不写 `dataset`、`dataset_commit` 或其他业务表；不改 §3.1 的 Kamei 14 维列名与顺序，不把公开数据训练的模型注册为交付模型。
- 数据过大时先探测体积再决定全量或抽样；抽样按 `committed_at` 分层等距执行，禁止随机，记录样本量守恒和各层边界。
- 变更文本需要构造时，复用语义特征线的同一文本表示；超限截断必须计数，不静默丢弃。

### 9.3 三维度质量报告

每个数据集输出机器可读明细与 Markdown 报告，数字必须来自本次运行，异常清单能定位到具体记录。

| 维度 | 必须产出 |
|---|---|
| 标签粒度 | 标明是否有缺陷类型；有则保留类型字段与分布，无则明确写“二值，无缺陷类型”，不得伪造 |
| 语种分布 | 按“数据集 × 语言 × 提交数 × 占比”报告，同时给出合并口径；OpenStack/Python、Qt/C++ 等非 Java 证据如实标注 |
| 数据质量 | 缺失率、重复率、字段一致性、时间序一致性，附异常样本和处置建议 |

同一 commit 的相反标签须单列“标签冲突”，不得静默去重保留一个；无法解析或违反仓库时间范围的记录单列“时间序不一致”，不得静默剔除。报告还须包含 `collect_public_probe_<job_id>.md` 的候选来源、可达性、体积、许可证和字段完备性结论。

### 9.4 Camel 并列、可选文献对照与网络降级

- 所有公开数据结论必须标注“基于公开数据集 X，与 Apache Camel 基线并列对照”；Camel 采集、14 维契约和现有接口不因本节改变。
- 只有获取到 DeepJIT/CC2Vec 等研究使用的标准 benchmark 时，才可做 AUC/F1 量级对照，并列明文献出处及工作量代理、划分、特征、模型差异；未获取时明确写不对照，不为凑数字选非标准数据集，也不宣称达到 SOTA。
- 可下载性必须先实测。网络代理、443、链接失效或许可证原因导致全部不可达时，交付“加载器 + 质量报告框架 + 用现有 Camel 数据自验”，报告与探测证据如实写明“未能获取公开数据集及原因”；不得把 Camel 自验冒充公开数据结果，不得虚构下载、字段或指标。

### 9.5 本节验收

- `tests/fixtures/files/collect/public/` 含完整、缺字段、标签冲突、非法时间、超大抽样、非 Java 与无缺陷类型 fixture；正常加载记录数与源一致，非法输入终止且无半成品。
- 字段映射、来源/许可证/日期元数据、三维报告和异常清单齐全；标签冲突不静默去重，时间异常不静默剔除，分层抽样各层守恒。
- 公开数据目录在测试前后不写业务库；Camel 基线文件、接口和 §3.1 列序不变，报告中的所有数字可由本次输出复算。
- 网络阻塞场景演练降级路径，探测报告包含真实错误与日期；标准 benchmark 不可用时报告明确原因且不做文献对照。
