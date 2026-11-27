# model_artifact

模型工件登记模型结构 / checksum 校验、权重路径与同事务 model 元数据派生；训练产物为每个算法一个独立 `.pkl`，外部交付可为 ZIP。不自动加载或执行外部权重；加载校验与模型管理由模型加载服务负责。

**一句话**：模型工件登记表，一行对应一份可加载权重；是模型名单的**唯一登记源**，`model` 表行由它派生，`model_registry` 只读登记结果并校验 checksum。

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| artifact_id | VARCHAR(36) | NOT NULL | 主键 | 工件标识 |
| model_name | VARCHAR(64) | NOT NULL | uk_artifact_model（唯一）+ 外键 → `model.model_name` | 派生出的模型名（全局唯一） |
| line | VARCHAR(16) | NOT NULL | ix_artifact_line | `expert`（Kamei 14 维）/ `semantic`（冻结头 CodeBERT 768 维） |
| algo | VARCHAR(64) | 可空 | — | 算法标识（与 `algorithm` 表对应） |
| version_key | VARCHAR(64) | NOT NULL DEFAULT '' | — | 版本键 |
| weight_path | VARCHAR(255) | NOT NULL | — | 权重文件 / 目录路径（相对仓库根） |
| checksum_sha256 | CHAR(64) | NOT NULL | — | 权重 SHA-256 校验值；加载前必校验 |
| size_bytes | BIGINT | NOT NULL DEFAULT 0 | — | 文件大小（字节） |
| feature_version | VARCHAR(32) | 可空 | — | 适用特征版本 |
| train_job_id | VARCHAR(36) | 可空 | 外键 → `job.job_id` | 产出该工件的训练任务；交付导入时可空 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'available' | — | `available` / `load_failed` / `retired` |
| trained_at | DATETIME | 可空 | — | 训练完成时间 |
| created_at | DATETIME | NOT NULL | — | 登记时间 |

## 主键与约束理由

- `artifact_id` 主键；`uk_artifact_model` 唯一键保证一个模型名同一时刻只有一份当前工件。
- 双外键：`model_name → model`（派生行先落，同事务满足外键）、`train_job_id → job`（可追溯训练任务）。
- `ix_artifact_line`：按模型线批量加载 / 盘点取数。
- 权重文件本体不入库，只登记路径与校验值。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 训练服务、离线交付导入脚本 | 工件登记 |
| 读取 | `model_registry`（加载 / 懒加载 / checksum 校验）、模型管理 API（状态 / 加载 / 卸载 / 重载） | 模型生命周期 |
| 展示 | 模型管理页（工件状态 / 大小 / 训练任务）、级联选择器（经 `model` 表） | 资产可见可管 |

## 口径

- **派生规则**：登记 / 更新工件时同事务 upsert `model` 行（model_name / line / algo / version_key / trained_at / feature_version）；`retired` 工件对应的 `model` 行保留但级联选择器过滤为不可选。
- **加载契约**：`model_registry` 启动与懒加载都从本表取路径并校验文件存在与 `checksum_sha256`；缺失或不符 → `status=load_failed` 并保留原因，MUST NOT 静默跳过或扫目录兜底。
- **失败隔离**：训练失败 MUST NOT 覆盖已有 `available` 工件；新工件校验通过才置 `available`。
- **链路关联**：训练自产工件 MUST 写 `train_job_id`；预测 / 解释任务据此把 `model_name` 解析为训练父任务，产物库链路视图与整链删除都依赖该字段，外部交付导入可为空。
- 模型状态三态：`available`（可用）/ `load_failed`（加载失败）/ `retired`（停用）。
- 在线 expert 权重列序以 `data_model/pipelines/expert/models/feature_order.txt` 为准，登记时核对 `feature_version` 与列序一致。
- **范式取舍（有意偏离 BCNF）**：`line` / `algo` / `version_key` / `trained_at` / `feature_version` 同时存在于 `model` 与 `model_artifact`，其中 `model` 行由本表派生。冗余是为了让加载契约只读本表即可完成（不跨表 join），且工件元数据是登记时点快照，不被后续 `model` 行变更影响。一致性由"同事务 upsert `model` 行"的派生规则保证。

## 验收

- 训练成功 → 工件行 + `model` 行同事务出现；页面无需重启即可在级联中看到新模型。
- 篡改权重文件 → 加载返回明确「校验值不符」，旧可用模型不受影响。
- 只写文件不登记 → 页面不可见（证明单源）；只登记无文件 → `load_failed` 且原因可查。
- 三态可查询、可切换；失败训练不改变已有 `available` 工件。