## MODIFIED Requirements

### Requirement: 实时同步入库

系统 SHALL 只以实时同步端点（`POST /api/sync` 与 `POST /api/sync-prs`）作为数据入库入口，MUST NOT 保留离线 CSV 灌库路径。写入 SHALL 遵循 design D4 的按表幂等键（`commit` 按 `commit_hash`、`commit_label` 按 `(commit_hash, label_method)`、`commit_feature` 按 `commit_hash`、`prediction` 按 `(commit_hash, model_name)`）：同一键重复写入 MUST NOT 产生第二行。同步逐条处理时，单条预测失败 MUST 只影响该条并计入 `skipped`，MUST NOT 中断整批，MUST NOT 使整端返回 50000。

#### Scenario: 正常入库

- **WHEN** 对一条可现算特征的提交执行同步预测
- **THEN** 对应模型的预测行按幂等键写入 `prediction` 表，关键字段与现算结果一致

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
- **THEN** 查询端点返回空列表（`code=0`）而非 50000；用户从界面触发同步后，提交按「现算特征 → 预测 → 逐条落库」进来，MUST NOT 预先批量灌库

## REMOVED Requirements

### Requirement: 本地开发数据初始化

**Reason**：owner 裁定「不允许提前灌库」——CSV 直灌（`bootstrap_dev.py`，2026-10-26 短暂存在）与「数据一律从 git 历史现算进来」的项目卖点相悖，且数据线产物与权重均不入库，该脚本对其他机器是死路。

**Migration**：空库首次使用改为**按需现算**——前端提供同步加载台，用户逐批触发 `POST /api/sync` / `POST /api/sync-prs`（每条现算特征并用真实权重预测后落库）；`infra/bootstrap_dev.py` 已删除，`infra/clone_camel_history.py` 仍是建立历史索引的正规步骤。