# job

`实现状态：部分　期次：一期`

W2 已实现持久状态、条件流转/重试令牌、同 kind 互斥及启动中断恢复；业务执行器随各模块波次接入。任务 API 不伪造业务已运行结果。

**一句话**：统一任务表，承载收集 / 清洗 / 训练 / 批量预测 / 评估 / 解释六类异步任务的状态、进度、日志与产出引用；任务状态持久化，重启可恢复。

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| job_id | VARCHAR(36) | NOT NULL | 主键 | 任务标识 |
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
- 状态与进度以表为准（条件更新），不靠进程内存字典；进程重启后状态可恢复。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 收集 / 清洗 / 训练 / 批量预测 / 评估 / 解释六类服务 | 任务生命周期 |
| 读取 | 任务状态 API、重试入口、CLI 状态查询 | 进度与诊断（前端轮询与 CLI 走同一接口） |
| 展示 | 页面进度条、日志抽屉、任务列表 | 状态 / 进度 / 错误原因 |

## 口径

- **六类 kind**：`collect` / `clean` / `train` / `predict_batch` / `evaluate` / `explain`。
- **五态流转**：queued → running → success / failed；running → cancelled；failed → queued（重试，`retry_count+1`）。非法流转返回 40001。
- **同 kind 互斥**：同一时刻同 kind 仅一个 running；冲突返回可解释 40001，不隐式排队等待。
- **重启恢复**：启动时把遗留 `running` 行置 `failed`（中断），`error_log` 记录中断原因，保留 `done` 进度供重试续跑；MUST NOT 静默丢弃或假装成功。
- **失败隔离**：训练任务内多算法逐个执行，单算法失败只记该子项错误，不影响其他算法产出（子项状态放 `output_ref_json`）。
- **日志脱敏**：`error_log` 与 `params_json` MUST NOT 写入 API Key / 口令 / LLM Key。

## 验收

- 发起收集 / 训练 → 任务行五态流转可查询；杀进程重启 → 遗留任务显示「中断失败」且可重试。
- 并发同 kind 任务 → 第二个返回可解释冲突码。
- 训练两算法一败一成 → 成功算法工件正常登记，失败子项有可读原因。
- 日志与入参快照中无凭证字符串（自动化断言）。