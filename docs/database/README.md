# 数据库契约索引与数据链路

`实现状态：部分　期次：一期`

## 1 文档形态与权威关系

- **文档形态**：本目录是 12 张表的目标契约。每篇头部单行标注 `实现状态`（已实现 / 部分 / 未实现）与 `期次`（一期 / 二期）；未实现部分即验收目标，验收以契约为准。
- **权威关系**：需求权威为 [`../../TODO/00-重构说明与开发执行要求.md`](../../TODO/00-重构说明与开发执行要求.md) 至 `TODO/09`（八功能点各自可独立运行 / 配置 / 验收）；**模块间数据 handoff 的单一权威为 [`../file-contracts.md`](../file-contracts.md)（交换文件 schema / manifest），比本目录表契约更前置**；`infra/schema.sql` 是当前 DDL 基线，`backend/app/models.py` 是对应 ORM。本文与 `dataset.md` 中标注“目标契约”的新字段是板块 2 的设计真源，DDL/ORM 须在后续实现波次同步；迁移完成前 MUST NOT 宣称字段已逐字对齐。表的角色 = 展示导入 + 配置 + 任务状态 + 资产登记，**不是模块间总线**：模块独立运行不依赖库里有上游数据。结构变更 MUST 同步 schema.sql 与 ORM，缺一即契约不完整。
- **访问纪律**：其他模块只经仓库接口（`backend/app/services/` + ORM）访问数据，不散写 SQL、不依赖他模块内存状态。
- **敏感信息**：API Key、口令等 MUST NOT 入库；鉴权沿用 `X-API-Key` 固定令牌（`.env` / 环境变量持有）。

## 2 表清单（12 张）

| 表 | 职责 | 实现状态 | 期次 | 契约文档 |
|---|---|---|---|---|
| `commit` | 提交元信息，全库锚点 | 已实现 | 一期 | [commit.md](commit.md) |
| `commit_feature` | Kamei 14 维 + `is_test` + SZZ 真标签 | 已实现 | 一期 | [commit_feature.md](commit_feature.md) |
| `model` | 模型注册表（线 / 算法 / 版本键），行由工件派生 | 已实现 | 一期 | [model.md](model.md) |
| `prediction` | 逐提交逐模型概率，联合主键幂等 | 已实现 | 一期 | [prediction.md](prediction.md) |
| `model_figure` | 逐模型性能图索引 | 已实现 | 一期 | [model_figure.md](model_figure.md) |
| `user` | 系统用户（非提交作者），预置 `global` 行 | 部分 | 一期 | [user.md](user.md) |
| `user_config` | 阈值 / 默认数据集 / 默认 XAI / 指标勾选唯一权威（模型不设默认值） | 部分 | 一期 | [user_config.md](user_config.md) |
| `job` | 六类任务五态生命周期 + 进度 + 日志 + 产出引用 | 部分 | 一期 | [job.md](job.md) |
| `algorithm` | 算法库：线算组合 / 超参 schema / 启用状态 | 未实现 | 一期 | [algorithm.md](algorithm.md) |
| `model_artifact` | 权重路径 / checksum / 大小 / 训练任务 / 状态 / 特征版本 | 部分 | 一期 | [model_artifact.md](model_artifact.md) |
| `dataset` | 数据集元数据：来源类型 / 来源地址 / 许可证 / 标签来源 / 时间范围 / 样本统计 / 状态 | 目标契约 | 一期 | [dataset.md](dataset.md) |
| `dataset_commit` | 数据集成员二维表：提交元信息 + 缺陷标签 + 来源信息，联合主键幂等 | 目标契约 | 一期单版本 / 二期多版本 | [dataset.md](dataset.md) |

单源约束：`model` 行由 `model_artifact` 登记派生；`model_registry` 读表并校验文件存在与 checksum，MUST NOT 扫目录形成第二本账。

## 3 数据链路口径

`实现状态：部分　期次：一期`

- **板块 2 产物**：collect 产出 `collected_commits.csv/xlsx + manifest + summary`（公开数据集另产 quality 报告），字段见 [`../file-contracts.md`](../file-contracts.md) §3.1；不产出 Kamei 14 维、不产出 `is_test`、不做训练/测试切分。
- **两种来源**：Git 仓库模式由任务入参提供仓库路径 / URL、分支、时间或提交范围、采集模式、SZZ 方法；公开数据集模式由任务入参提供文件/URL、许可证、来源说明、字段映射和标签映射。两者都默认保存数据库；`SOURCE_REPO` 不再是运行前提。
- **文件 handoff 优先**：collect 的文件产物是后续模块的手off 契约；`dataset` / `dataset_commit` 是板块 1 提供的保存与查询服务，不替代文件。公开数据集同样落盘并入库，MUST NOT 仅入库不落盘。
- **安全校验**：仓库/数据文件路径限定配置允许根目录；URL 仅 https / git 协议白名单；MUST NOT 把用户输入拼进 shell 字符串；公开数据集必须显式映射字段与标签值，MUST NOT 静默猜测。
- **服务化边界**：`01_extract_commits`、`02_szz_labeling` 及 SZZ 判据封装为 collect 服务；`03_extract_features`、`04_build_dataset`、`05_split_dataset` 不再属于板块 2，归后续板块重构。CLI / API 调用同一 collect 实现；每一步记录退出码、产物路径、样本数与 commit SHA。
- **任务化与保存**：收集写 `job`（kind=collect）。文件生成后默认写 `dataset` + `dataset_commit`；保存失败保留文件、5 分钟后可重试保存，MUST NOT 因数据库失败删除产物。同一数据集内按 `commit_hash` 幂等。
- **导出**：数据集支持 CSV / XLSX，字段为 §3.1 的已打标二维表；CSV 带 UTF-8 BOM 兼容 Excel 中文；XLSX 依赖 `openpyxl` 须锁版进入 `data_model/environment.yml`；响应带正确 `Content-Disposition`。

## 4 SZZ 判据与历史基准

`实现状态：已实现　期次：一期`

- **判据（D4 双命中）**：候选修复提交须同时含缺陷编号 `CAMEL-<数字>` 与修复语义词；语义词按大小写不敏感**词首边界** `\b(fix|bug|patch)` 匹配——保留 `fixes / fixed / patching` 等词形与拼写错误的真修复，排除 `dispatch / debug / prefix` 这类同词内嵌（实现：`data_model/preparation/02_szz_labeling.py`）。
- **双方法分别报告**：`szz_v1`（标准行级回溯，自研实现，旧称 `szz`）与 `szz_lite`（文件级回溯简化版）各打一次标，差异量化出示（分歧率 = 不一致数 ÷ 两法正样本并集），不静默取其一；训练主标签为 `szz_v1`，`label_method` 合法枚举统一为 `szz_v1 / szz_lite / third_party`。
- **D5 排除**：回溯未命中的修复提交既不入样本也不记负样本，只在统计中单列数量。
- **质量自检**：正样本比例落在 40%–60% 为异常区间（`ABNORMAL_LOW=0.40`、`ABNORMAL_HIGH=0.60`），须先复核打标逻辑再进下游。词表、自检区间、D5 规则登记为清洗操作注册表的**默认参数**，可配置但改动须留配置版本与前后统计；MUST NOT 在业务代码里另写一份判据。
- **未打标语义**：板块 2 产出与入库的 `dataset_commit.is_bug_inducing` 保持 `NULL`，MUST NOT 当 0。
- **历史基准**（上游 `866b7dc` 全量采集与 SZZ 报告，2026-10-14）：含缺陷编号 38,716 条；编号 + 修复词首语义 7,787 条；编号 + `fix` 词首语义 6,631 条；完整提交 84,461。**这些是历史基准，不代表本机已重跑全量采集**；数据源 / 版本 / 过滤条件改变时先重跑并重新登记，子集运行标注「不可比」而非自检通过。

## 5 特征与训练边界

`实现状态：部分　期次：一期`

- Kamei 14 维定义、列序与 log 变换（`fix` 除外）见 [commit_feature.md](commit_feature.md)；在线 expert 权重列序以 `data_model/pipelines/expert/models/feature_order.txt` 为准。
- **切分**：方式用户可配置——`random`（默认，按种子固定）或 `time_order`（按 `committed_at` 时间序前 70% / 后 30%，可配置比例）；仅 `time_order` 模式 MUST 保留「检验集最早时间 > 训练集最晚时间」断言。随机切分不再被禁止；切分在训练阶段完成，不落 `is_test` 到采集/清洗产物。
- **模型线**：仅 expert（Kamei 14 维）/ semantic（冻结头 CodeBERT 768 维）两线，各 8 分类器（`lr rf xgb lgbm et svm mlp_deep tabnet`），共 16 模型；`fused` / `e2e` 两线已砍掉。算法清单与超参 schema 登记进 `algorithm` 表，训练表单从该表读取，前端 MUST NOT 硬编码算法清单；种子 / 阈值 / 早停等训练级参数的出厂默认在 `data_model/pipelines/*/config.py`（如 expert `SEED=42`、`DECISION_THRESHOLD=0.5`），运行时权威在 `user_config` 与训练配置模板。
- **工件登记**：训练成功写 `model_artifact`（路径 / checksum / 大小 / 训练 job / 状态 / 特征版本）并同事务派生 `model` 行；失败任务 MUST NOT 覆盖已有可用工件。模型状态三态：available / load_failed / retired。
- **加载**：`model_registry` 读表 + 校验 checksum，不扫目录；新模型经登记即可被选择与加载，无需重启后端。
- tabnet 权重若 GPU 训练、CPU 加载报 CUDA 反序列化错误，运行 `python data_model/pipelines/reexport_tabnet_cpu.py` 重导出（原文件备份 `*.bak-cuda`）。

## 6 语义增量口径

`实现状态：已实现　期次：一期`

semantic 线读 `data_model/pipelines/semantic/data/semantic_embeddings.npz`（冻结头 CodeBERT 768 维向量），为训练阶段预计算产物，体积大且被 `.gitignore` 忽略，不随仓库分发。`fused` / `e2e` 的预计算产物已随两线删除，不再是契约组成。

- **正常路径**：预计算表覆盖的提交直接查表，在线预测不加载 CodeBERT。
- **增量兜底**：新同步提交不在表内时，后端用源仓库现场构造 diff 文本（口径与 `data_model/pipelines/text_source.py` 一致），用冻结 CodeBERT mean-pool 编码为 768 维；结果缓存进程内，不重写大表。
- **失败语义**：源仓库未配置、提交不可读或编码器不可用时返回 `40001` 明确文案，MUST NOT 编造向量。
- 在线兜底保证干净检出 + 已配置源仓库时两线模型都能对新提交预测，但不替代离线重训所需全量产物。

## 7 配置持久化与恢复

`实现状态：部分　期次：一期`

W1 已实现配置服务与 `/api/config` 读写、功能①配置区、风险阈值和指标配置接入；清洗/训练模板和其他业务参数随对应模块波次生效。配置写入前使用数据库当前读进行跨键校验，包含受全局默认变更影响的用户覆盖值；值长度按 UTF-8 字节限制为 65,535。

独立迁移入口：[infra/migrate_mysql.py](../../infra/migrate_mysql.py)。默认只读预检；`--apply` 才执行。已覆盖空库、标准五表、旧四表与重复执行；旧四表删除冗余列和标签表须显式 `--allow-legacy-cleanup --backup-dir <已有目录>`，并先完成 mysqldump。缺少客户端或备份失败时不写库；共享演示库须另行确认，不能因测试通过自动执行。

旧备份未记录训练/测试集划分时，迁移报告明确标注 `is_test=0` 为未恢复的默认值，不冒充历史时间序切分结果；标签为空保持 NULL，未知模型参数与工件信息不编造。

- `user_config` 是阈值、默认数据集、默认 XAI 技术、指标勾选与页面偏好的**唯一权威**，模型不设默认值（键清单与校验见 [user_config.md](user_config.md)）；`.env` 与 `data_model/pipelines/*/config.py` 仅作出厂默认值的来源。
- 读取顺序：当前用户行 → `global` 行 → 出厂默认常量，只在配置服务内实现；前端读配置接口，MUST NOT 自带第二份默认值。
- 提供读取 / 单键更新 / 批量更新 / 删除接口与最小设置界面；未知键 / 非法值 / 越权访问返回明确错误码。
- **恢复语义**：写入立即生效；后端 / 容器 / 进程异常关闭后重启，接口可读取原有配置（TODO/01 验收线）。

## 8 任务持久化

`实现状态：未实现　期次：一期`

- `job` 统一承载六类任务：`collect` / `clean` / `train` / `predict_batch` / `evaluate` / `explain`；五态 `queued / running / success / failed / cancelled`，记录入参快照、进度、起止时间、错误日志、重试次数与产出引用（见 [job.md](job.md)）。
- 同 kind 同一时刻仅一个 running，互斥以表为准（条件更新），冲突返回可解释错误码。
- 重启恢复：遗留 `running` 行置 `failed`（中断），保留进度供重试；状态接口读表，前端轮询与 CLI 走同一接口。
- 日志脱敏：`error_log` / `params_json` MUST NOT 含令牌 / 口令 / LLM Key。

## 9 分期与不变量

`实现状态：部分　期次：一期 / 二期`

- **一期**：12 表结构落地；数据集单版本（`dataset_commit` 联合主键幂等）；一个模型名一份当前工件。
- **二期**：数据集多版本——`dataset_commit` 增加 `feature_version` 进主键，承载同一提交在不同处理链版本下的特征；动主键前必须备份数据库并留恢复脚本。
- **不变量清单**（作为可配置默认值存在，改动须留配置版本与前后统计，MUST NOT 改坏口径）：
  1. Kamei 14 维定义与列序；log 变换口径（`fix` 除外）。
  2. SZZ 词首边界判据 `\b(fix|bug|patch)`；`szz_v1 / szz_lite` 双方法分别报告。
  3. 划分方式用户可配置：`random`（默认，按种子固定）或 `time_order`（前 70% / 后 30%，保留切分边界断言）。
  4. 真标签统一 `is_bug_inducing`；未打标 `NULL` MUST NOT 当 0。
  5. 架构 → 模型两级级联 + 独立时间范围（非三级）。
  6. `X-API-Key` 统一鉴权；`/static/**` 不免鉴权。

## 10 统计与证据

`实现状态：部分　期次：一期`

- 采集条数、打标比例、特征缺口、切分边界由每次运行输出与 `data_model/preparation/reports/` 记录；该目录**尚未在本机生成**，不得引用历史数字冒充当前结果。
- `04_build_dataset.py` 七项统计：过滤合并提交后总提交数、UTC 时间跨度、打标成功数、正样本数、负样本数、正样本比例、打标方法（正样本比例 = 正样本数 ÷ 打标成功数）。报告须检查标签与提交清单、特征表按 `commit_hash` 对齐，并列出被排除行数。
- 模型线评估报告与图集在 `data_model/pipelines/*/reports/`；离线指标汇总产物为 `data_model/evaluation/out/model_metrics.csv`。验收结论以当次运行证据为准。
