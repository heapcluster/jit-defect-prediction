## MODIFIED Requirements

### Requirement: 实时同步入库

系统 SHALL 只以实时同步端点（`POST /api/sync`、`POST /api/sync-prs` 与新增的 `POST /api/sync/range`）作为数据入库入口，MUST NOT 保留离线 CSV 灌库路径。写入 SHALL 遵循 design D4 的按表幂等键（`commit` 按 `commit_hash`、`commit_label` 按 `(commit_hash, label_method)`、`commit_feature` 按 `commit_hash`、`prediction` 按 `(commit_hash, model_name)`）：同一键重复写入 MUST NOT 产生第二行。同步逐条处理时，单条预测失败 MUST 只影响该条并计入 `skipped`，MUST NOT 中断整批，MUST NOT 使整端返回 50000。`sync` SHALL 与 `sync-prs` 一致地对每条 commit **落全部注册模型的 `prediction` 行**。

#### Scenario: 正常入库

- **WHEN** 对一条可现算特征的提交执行同步预测
- **THEN** 对应全部模型的预测行按幂等键写入 `prediction` 表，关键字段与现算结果一致

#### Scenario: 同一提交重复同步

- **WHEN** 对同一提交连续执行两次同步预测
- **THEN** `prediction` 表行数不变，MUST NOT 产生重复行

#### Scenario: 单条失败不中断（边界场景）

- **WHEN** 某条提交的特征现算或模型推理失败
- **THEN** 该条计入 `skipped` 并记录原因，其余提交继续写入，整批响应仍为 `code=0`

#### Scenario: 初始化脚本不得冒充服务端入口（边界场景）

- **WHEN** 审查仓库内任何数据导入脚本（无论叫 bootstrap、seed 还是 ingest）
- **THEN** 它们 MUST NOT 被任何 API 路由、应用启动流程或 CI 必需步骤调用；数据入库入口只有实时同步端点，脚本产物不构成运行时口径

#### Scenario: 空库首启（边界场景）

- **WHEN** 干净环境首次启动、四表为空
- **THEN** 查询端点返回空列表（`code=0`）而非 50000；若 `SYNC_ON_STARTUP=1`，后台建立首启基线（见 `sync-api`），用户从界面可见进度，提交按「现算特征 → 预测 → 逐条落库」进来，MUST NOT 预先批量灌库

#### Scenario: 首启分级基线（边界场景）

- **WHEN** 首次启动且 `prediction` 表为空
- **THEN** 后台同步采用 `SYNC_INITIAL_LIMIT`（默认 10）作为基线窗口；之后重启 / 日常仅增量补最新 `SYNC_INITIAL_LIMIT` 条，`MUST NOT` 每次都全量重扫历史

## ADDED Requirements

### Requirement: 模型元数据表

系统 SHALL 新增 `model` 表，承载模型注册元数据，至少含 `model_name`（主键）、`version_key`、`trained_at`（UTC）、`algo`、`feature_version`；`prediction.model_name` SHALL 为引用 `model.model_name` 的外键。模型加载器 SHALL 在启动时将注册表写入或核对 `model` 表，保证 `prediction` 行的 `model_name` 必能在 `model` 表找到对应元数据。

#### Scenario: 模型元数据可查

- **WHEN** 查询某 `model_name` 的元数据
- **THEN** 返回其 `version_key` / `trained_at` / `algo` / `feature_version`，MUST NOT 把元数据内联冗余进 `prediction` 表

#### Scenario: 预测外键约束

- **WHEN** 写入 `prediction` 行
- **THEN** 其 `model_name` 必须存在于 `model` 表，否则数据库以外键约束拒绝

### Requirement: 外键与审计列

四张业务表（`commit` / `commit_label` / `commit_feature` / `prediction`）SHALL 通过 `commit_hash` 建立引用完整性：`commit_feature` / `commit_label` / `prediction` 的 `commit_hash` SHALL 为引用 `commit.commit_hash` 的外键。各表 SHALL 附加 `updated_at`（UTC）审计列，在数据写入或幂等更新时刷新。

#### Scenario: 子表引用完整性

- **WHEN** 向 `prediction` / `commit_feature` / `commit_label` 写入 `commit_hash`
- **THEN** 该哈希必须已存在于 `commit` 表，否则外键约束拒绝

#### Scenario: 审计列刷新

- **WHEN** 某行被幂等更新（如重新预测同键）
- **THEN** 该行 `updated_at` 被刷新为当前 UTC 时间，MUST NOT 保持旧值
