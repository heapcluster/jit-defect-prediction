# 数据库存储与配置中心（功能 1）

实现状态：部分　期次：一期

## 一句话概述

独立的存储与配置工具：负责 12 表的展示导入与按表导出、用户配置、任务状态和资产登记，不为其他模块承担业务计算，也不充当模块间数据总线。

## 1 职责与不负责范围

**负责**：

- 维护 `commit / commit_feature / model / prediction / model_figure / user / user_config / job / algorithm / model_artifact / dataset / dataset_commit` 12 表；表结构真源为 [`../../infra/schema.sql`](../../infra/schema.sql)，字段契约见 [`../database/README.md`](../database/README.md)。
- 按交换文件 schema 自动识别导入目标，按自然键幂等 upsert；按单表导出 CSV/XLSX，供展示页读取与离线交接。
- 提供全局键与模块命名空间键的读取、单键更新、批量更新、删除和恢复默认值；配置写入后立即生效并在重启后恢复。
- 提供数据集、模型工件、算法、任务状态等资产查询，以及空库初始化、旧库升级和重复执行迁移。
- 统一仓库接口与 ORM 访问规则，避免业务模块散写 SQL。

**不负责**：

- 采集、清洗、训练、预测、评估、解释、定位与修复建议等计算。
- 替其他模块保存唯一交付物；模块交付以文件与 manifest 为准，导入库只是可选展示动作。
- 复杂组织权限、多租户、模型权重在线编辑或完整账号产品；凭证明文不入库。

## 2 独立运行入口

```bash
python infra/setup_mysql.py
python infra/migrate.py --database jit_demo
python -m app.cli storage import --file cleaned.csv
python -m app.cli storage export --table prediction --format csv --out ./out
python -m app.cli config get
python -m app.cli config put decision_threshold 0.3
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `storage import/export`、`config get/put/delete`、建库与迁移命令 | 可脱离 Web 单独执行，与 API 调用同一服务 |
| 导入 API | `POST /api/storage/import` | multipart 上传任一受支持的交换文件，同步返回识别结果、upsert 统计与操作标识 |
| 导出 API | `GET /api/storage/export?table=<table>&format=csv\|xlsx` | 仅按表导出，支持该表已声明的筛选与分页 |
| 配置 API | `GET/PUT /api/config`、`PUT/DELETE /api/config/{key}` | 单键与批量读写；批量更新原子生效 |
| 查询 API | `/api/datasets`、`/api/models`、`/api/algorithms`、`/api/jobs` 族 | 只读资产与任务状态 |
| Web | 数据管理与设置页 | 仅是导入、导出、配置与资产展示入口 |

所有 HTTP 端点（含导出下载）必须使用 `X-API-Key`；数据库口令、API Key、LLM Key 等凭证只从安全环境注入，不写入配置表、日志或导出文件。

## 3 输入契约

- 跨模块文件只接受 [`../file-contracts.md`](../file-contracts.md) §3.1–3.8 已定义的 schema：§3.1 `commits.csv`、§3.2 `cleaned.csv`、§3.3 `model_package.zip`、§3.4 `predictions.csv`、§3.5 `labels.csv`、§3.6 指标/混淆/报告与图、§3.7 `explanations.csv`、§3.8 定位/建议/补丁预览；manifest 遵循 §3.9。CSV/XLSX 的编码、空值和安全规则遵循 §1，不另设列名。
- 导入器依据列集合、工件内容与 manifest 识别类型和目标表；无法识别、schema 缺列、类型错误、checksum 不符或引用对象缺失时明确拒绝，不猜测映射、不产半批写入。
- 有表语义的文件按下列规则导入；没有对应表语义的解释、定位、建议和报告文件仍以原文件交付，不强行塞入其他表。

| 输入 | 目标与幂等口径 |
|---|---|
| §3.1 / §3.2 表格 | `commit`、`commit_feature` 按提交自然键 upsert；提供数据集元数据时同时登记 `dataset`、`dataset_commit` |
| §3.3 模型包 | 校验后登记 `model_artifact`，并派生 upsert `model` |
| §3.4 / §3.5 表格 | `prediction` 按提交与模型自然键 upsert；标签冲突按 §3.5 记录，未打标保持 NULL |
| §3.6 图形与报告索引 | `model_figure` 按模型与图类型 upsert；数值文件本身保留为交付文件 |
| 配置与资产元数据 | `user`、`user_config`、`algorithm`、`dataset`、`model_artifact` 的显式管理输入，按各表契约校验 |

- `labels.csv` 不独立创造提交或预测；只更新已存在样本的真标签。外键或登记引用不满足时返回可诊断错误。
- 导出输入是 12 表之一的表名、格式与筛选条件；禁止任意 SQL、任意表名和跨表拼接导出。

## 4 输出契约

| 输出 | 文件 / 结果 |
|---|---|
| 导入回执 | `storage_import_<job_id>.json`：识别 schema、目标表、插入/更新/跳过/失败计数、冲突与错误原因 |
| 按表导出 | `storage_export_<table>_<job_id>.csv`，可选同名 `.xlsx`；导出列为目标表 DDL 列，不冒充 §3.1–3.8 交换 schema |
| 配置快照 | API/CLI 返回生效键值、来源和更新时间；可导出脱敏配置快照，绝不包含凭证 |
| 资产与任务查询 | 数据集、模型工件、算法和六类任务状态，与数据库记录一致 |
| 迁移结果 | 初始化/升级/重复执行状态、结构校验与可读日志 |
| manifest | 每个导出或导入回执均伴 `storage_<artifact>_<job_id>.manifest.json`，记录输入输出 checksum、配置与代码版本，遵循 §3.9 |

命名统一为 `<module>_<artifact>_<job_id>.<ext>`；这里的 `job_id` 是同步导入/导出操作关联号，不新增第七种任务 kind。下载使用 `GET /api/storage/outputs/{job_id}/{name}`；表导出文件流也可直接由 export 端点返回。

## 5 可配置项

全局键的唯一持久化来源是 `user_config`；读取顺序为当前用户行 → `global` 行 → 配置服务内出厂默认值，前端和业务模块不得另建权威副本。

| 全局键 | 默认与约束 |
|---|---|
| `decision_threshold` | 0.5，开区间 (0,1) |
| `risk_high_threshold` / `risk_mid_threshold` | 0.5 / 0.2，均在 (0,1)，且 mid < high |
| `default_model` / `default_dataset` | 可为空；非空时须指向已登记资产 |
| `default_xai` | `shap`，须属于解释器注册表 |
| `metrics_selected` / `primary_metric` / `effort_enabled` | 六项基础指标 / `auc` / `true`；主指标须属于已选指标 |
| `page_prefs` | 白名单对象 |

模块命名空间键同样落入 `user_config`：`collect.allow_roots`、`collect.protocol_whitelist`、`clean.chain_templates`、`train.templates`、`predict.batch_size`、`predict.cache_ttl`、`predict.retry_max`、`explain.cache_ttl`、`explain.compare_enabled`、`localization.weights`、`localization.top_n`、`localization.file_size_max`、`localization.suggestion_sources`。二期 extension 的报告、门禁、失败策略和事件键也按该模块 §5 落入同一配置中心。未知键、类型错误、越界值与跨键约束违反均拒绝；恢复默认值通过删除用户覆盖实现。

## 6 状态持久化

- 12 表只承担展示导入、配置、任务状态和资产登记。`model` 行由 `model_artifact` 派生；`algorithm` 是算法与超参 schema 的登记源；数据集多版本属二期，一期不改变既有主键。
- `job` 只包含 `collect / clean / train / predict_batch / evaluate / explain` 六类，状态只包含 `queued / running / success / failed / cancelled`；同 kind 同时最多一个 running，启动时将遗留 running 置 failed 并保留进度。
- 导入采用事务与幂等 upsert；一批中校验失败时不得留下不可解释的半批状态。导出从已提交快照读取，重复导出内容一致。
- 配置批量更新原子生效；进程、容器异常关闭后重启，全局键、命名空间键、资产和任务状态均可恢复。
- 导入回执、导出文件和 manifest 落盘 `backend/var/outputs/<job_id>/`；`backend/var/outputs/` 必须整体加入 gitignore。数据库只保存引用与元数据，不替代文件交付。
- 建表真源、迁移脚本和 ORM 必须同步；空库初始化、旧库升级、重复执行均需结构一致且不破坏已有数据。

## 7 与其他模块边界

- 其他模块的独立运行只要求交换文件 schema 兼容，不要求本模块已有数据；需要库中便利输入时，由各模块 run 端点显式接收可选 `dataset_id`。
- 展示页读取导入后的表；业务模块不得通过读取展示表来代替自己的文件输入，也不得把其他模块的内存或服务存活当作前提。
- 原由集中数据同步页面承担的“导入库展示”职责归本模块；模型性能数值、图与报告的计算职责归 evaluate，本模块只保存展示索引。
- 公开 JIT 缺陷数据集按 collect §9 独立落盘，不进入 12 表。

## 8 验收标准

fixtures 位于 `tests/fixtures/files/storage/`（后端与模型线测试根目录按 file-contracts §1 映射），必须包含正常、边界、非法三类；无需先运行任何业务模块。

- 正常 fixture 能被自动识别到正确目标表，重复导入无重复行；非法 schema、checksum、未知配置键、越权与任意表导出均被拒绝且无半成品。
- CSV/XLSX 导出可打开、中文不乱码、筛选生效；导出列与目标表一致，manifest checksum 完整，大数据量分页导出通过。
- 建表与迁移在空库、旧库、重复执行三种场景通过；接口查询的数据集、模型工件和算法与库中记录一致。
- 保存全局键及全部命名空间键后，停止并异常重启后端，值仍可恢复；批量更新任一值非法则整批不写，恢复默认值生效。
- 六类五态、同 kind 互斥、重启 running 置 failed 均有测试；敏感信息扫描证明配置、日志、回执与导出不含凭证。
- 承接 TODO/01：前端读取持久化配置而非把常量作为唯一来源；迁移、配置读写、重启恢复和资产查询均有自动化测试。
