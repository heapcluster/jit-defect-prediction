# job

`实现状态：部分　期次：一期`

W2 已实现持久状态、条件流转/重试令牌、同 kind 互斥及启动中断恢复；业务执行器随各模块波次接入。任务 API 不伪造业务已运行结果。板块 2 的 collect 任务按本文承载 Git 仓库采集和公开数据集 URL 拉取，二者共用 `kind=collect`。

**一句话**：统一任务表，承载收集 / 清洗 / 训练 / 批量预测 / 评估 / 解释六类异步任务的状态、进度、日志与产出引用；任务状态持久化，重启可恢复。

collect 的 `params_json` 必须记录 `source_type`、`dataset_name`、`save_to_db`、`label_source`；Git 模式另记仓库 / 分支（来自 `GET /api/collect/branches` 返回值）/ 提交时间范围 / SZZ 方法，公开数据集模式另记来源、许可证、字段映射与标签映射。`error_log` 记载保存数据库失败的脱敏原因；`output_ref_json.outputs` 登记核心 `collected_commits_<job_id>.csv` 及 manifest / summary / audit / quality 等内部产物；`dataset_id` 由 resave 单独写入，页面只展示核心 CSV。

clean 的 `params_json` 必须记录输入 `dataset_id`、`mode=apply`、`output_name`、归一化后的 `steps[]`；Web 页面不传 `chart_columns` 与 `format`，后端只记录每步前后差异与字段级变化，不生成 PNG 变化图。`output_ref_json.outputs` 登记核心 `clean_dataset_<job_id>.csv` 或 `<output_name>.csv` 及 manifest / steps_stats；不登记预生成 XLSX，页面只展示核心 CSV。

predict_batch 的 `params_json` 必须记录 `model_name`、`testset_ref`、`decision_threshold`、`output_name`、`save_to_db=true` 与 `batch_size`。Web 页面测试集只能来自训练成功任务产出的 `train_testset`。`output_ref_json.outputs` 登记核心 `predict_predictions_<job_id>.csv` 或 `<output_name>.csv` 及 manifest / summary；不登记预生成 XLSX，页面只展示核心 CSV。成功后全部结果行写入 `prediction`，保存失败视为任务失败并可重试。

evaluate 的 `params_json` 必须记录 `prediction_job_id`、`metrics`、`primary_metric`、`effort_enabled`、`figure_zip_name`、`metrics_name`、`output_format`。评估沿用预测结果中的 `predicted_label` 与 `decision_threshold`，不接受新阈值，固定单一模型、单一测试集。`output_ref_json.outputs` 登记「评估图集 zip」「评估指标表」及逐图 PNG / manifest / summary；逐图按 `evaluate_<job_id>_<figure_type>.png` 标准命名登记到 `model_figure`，可按 `job_id` 查询批次图集，页面只展示 zip 与指标表。

## 数据链路（chain）

一条链路是一次“数据 → 模型 → 结果”的完整操作。链路在任务提交时**显式写入**，不靠前端或产物库按文件名猜测：

| 新建任务 | 父任务解析方式（全部来自已校验输入） |
|---|---|
| collect | 链根：`chain_id = job_id`，`parent_job_ids = []` |
| clean | 输入文件 manifest 的 `module=collect` + `job_id`；选 `dataset_id` 时取 `dataset.job_id` |
| train | `clean_dataset_<job>.csv` 的 manifest；选 `dataset_id` 时取 `dataset.job_id` |
| predict_batch | `train_testset_<job>.csv` 的 manifest（测试集所属训练任务）+ `model_name` 对应 `model_artifact.train_job_id`，去重后写入 |
| evaluate | 预测结果文件 manifest 的 `job_id`，或 `params.prediction_job_id` |
| explain | 预测任务 + 模型所属训练任务 |
| 清洗产物自动登记（内部） | 不写 `job`，因此没有 `chain_id`，不进入链路视图；仅由清洗成功后自动登记数据集使用，不做伪链、不伪造上下游 |

口径：

- `chain_id` 继承第一个父任务的 `chain_id`；父任务跨越不同链路时取最早链根，并把链路视图按 `parent_job_ids` 计算的连通分量归并。
- 训练多个算法或同一清洗结果训练多个模型时，链路在 train 节点分叉，属于同一条链，不拆成多条。
- 重试沿用原 `job_id` 与 `chain_id`，不新建链路。
- `model_artifact.train_job_id` 必须由训练登记写入；`dataset.job_id` 必须由收集创建时写入（清洗自动登记的数据集该字段为空），二者是 predict / train 解析父任务的依据。
- 删除以链路为单位：链内任务、产物文件、训练产出的模型与收集产出的数据集整体删除；若链内资产被链路外任务引用，删除前置拒绝并列出引用方，不静默删除共享资产。

## 字段（字段与索引对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| job_id | VARCHAR(36) | NOT NULL | 主键 | 任务标识 |
| chain_id | VARCHAR(36) | NOT NULL DEFAULT '' | ix_job_chain | 所属数据链路根任务标识；链根任务等于自身 `job_id`，历史空值按自身 `job_id` 回填 |
| parent_job_ids | TEXT | 可空 | — | 直接父任务 JSON 数组 `[{"kind":"clean","job_id":"..."}]`；提交时按已校验输入显式写入 |
| kind | VARCHAR(16) | NOT NULL | ix_job_kind_status（第 1 列） | `collect` / `clean` / `train` / `predict_batch` / `evaluate` / `explain` |
| status | VARCHAR(16) | NOT NULL DEFAULT 'queued' | ix_job_kind_status（第 2 列） | `queued` / `running` / `success` / `failed` / `cancelled` |
| params_json | TEXT | 可空 | — | 入参快照（仓库 / 数据集 / 算法 / 超参 / 阈值 / 模型列表等），复现与重试用 |
| total | INT | NOT NULL DEFAULT 0 | — | 进度总量 |
| done | INT | NOT NULL DEFAULT 0 | — | 已完成量 |
| current_item | VARCHAR(64) | 可空 | — | 当前处理对象（commit_hash / 算法名等） |
| started_at | DATETIME | 可空 | — | 开始时间 |
| finished_at | DATETIME | 可空 | — | 结束时间 |
| error_log | TEXT | 可空 | — | 可读错误日志（脱敏） |
| retry_count | INT | NOT NULL DEFAULT 0 | — | 已重试次数 |
| output_ref_json | TEXT | 可空 | — | 产出引用：dataset_id / artifact_id / 结果集标识 / 报告路径；多算法子项状态也放这里 |
| created_at | DATETIME | NOT NULL | — | 创建时间 |

## 主键与约束理由

- `job_id` 自然主键（UUID 字符串）；`dataset.job_id`、`model_artifact.train_job_id` 外键指向它。
- 复合索引 `(kind, status)`：同 kind 互斥检查与「按类型筛运行中任务」都走它。
- `ix_job_chain`：产物库按链路取整链任务、按链路删除时走它。
- `parent_job_ids` 是链路 DAG 的邻接表，由后端提交阶段写入，前端不解析文件名猜上下游。
- 状态与进度以表为准（条件更新），不靠进程内存字典；进程重启后状态可恢复。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 收集 / 清洗 / 训练 / 批量预测 / 评估 / 解释六类服务 | 任务生命周期 |
| 读取 | 任务状态 API、重试入口、CLI 状态查询 | 进度与诊断（前端轮询与 CLI 走同一接口） |
| 读取 | 产物库链路视图、按链路删除 | 以 `chain_id` / `parent_job_ids` 还原任务树并整体清理 |
| 展示 | 页面进度条、日志抽屉、任务列表、链路卡片 | 状态 / 进度 / 错误原因 / 上下游关系 |

## 口径

- **六类 kind**：`collect` / `clean` / `train` / `predict_batch` / `evaluate` / `explain`。
- **五态流转**：queued → running → success / failed；running → cancelled；failed → queued（重试，`retry_count+1`）。非法流转返回 40001。
- **同 kind 互斥**：同一时刻同 kind 仅一个 running；冲突返回可解释 40001，不隐式排队等待。
- **重启恢复**：启动时把遗留 `running` 行置 `failed`（中断），`error_log` 记录中断原因，保留 `done` 进度供重试续跑；MUST NOT 静默丢弃或假装成功。
- **失败隔离**：训练任务内多算法逐个执行，单算法失败只记该子项错误，不影响其他算法产出（子项状态放 `output_ref_json`）。
- **日志脱敏**：`error_log` 与 `params_json` MUST NOT 写入 API Key / 口令 / LLM Key。
- **范式取舍（有意偏离 BCNF）**：`params_json` / `output_ref_json` 是非结构化 JSON 快照，不同 kind 写入的键集合不同，无法用固定列表达而不产生大量可空列。这是有意选择的动态 schema，不建子表拆分；校验由写入侧按 kind 的契约保证，读取侧按需要解析。

## 验收

- 发起收集 / 训练 → 任务行五态流转可查询；杀进程重启 → 遗留任务显示「中断失败」且可重试。
- 并发同 kind 任务 → 第二个返回可解释冲突码。
- 训练两算法一败一成 → 成功算法工件正常登记，失败子项有可读原因。
- 依次跑收集 → 清洗 → 训练 → 预测 → 评估 → `GET /api/storage/lineage` 返回同一条链，`parent_job_ids` 逐级指向上一任务。
- 同一清洗结果训练两个算法 → 链路在 train 分叉，仍属同一 `chain_id`。
- 删除整条链路 → 链内任务、产物、模型与数据集一并清理；被链路外引用时返回 40001 并列出引用方。
- 日志与入参快照中无凭证字符串（自动化断言）。