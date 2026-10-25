## ADDED Requirements

### Requirement: 批量同步最新提交并在线预测

服务端 SHALL 提供 `POST /api/sync?limit=N`（N 默认 10、上限 50）：对配置的 `SOURCE_REPO` 执行 `git fetch`（MUST 经命令行参数禁用代理），将最新提交中库内尚不存在的哈希**逐条**走现行单条预测链（现算特征 → 幂等写 `prediction`），并返回 `{tip, scanned, new, predicted[], skipped[]}` 汇总。`SOURCE_REPO` 未配置时 SHALL 返回 40400；`limit` 越界 SHALL 返回 40001；单条失败 MUST 计入 `skipped` 而非中断整批；无新提交时 SHALL 幂等返回 `new=0`；同一时刻 MUST NOT 并发执行两个同步任务。错误码 MUST 使用冻结集合（0/40001/40400/50000），MUST NOT 新增错误码。

#### Scenario: 有新提交时批量入库

- **WHEN** 上游出现库中不存在的最新提交且服务端已配置 `SOURCE_REPO`
- **THEN** 每条新提交现算特征后以默认模型预测入库，`predicted` 含各条 `commit_hash/model_name/risk_score`，列表接口可按风险查到新行

#### Scenario: 无新提交时幂等（边界场景）

- **WHEN** 最新提交均已在库中
- **THEN** 返回 `new=0`、`predicted=[]`，库内行数不变

#### Scenario: 单条不可达（边界场景）

- **WHEN** 某条最新提交无法从 HEAD 可达或现算失败
- **THEN** 该条计入 `skipped`（含冻结错误码），其余条目继续处理，整批响应仍为 `code=0`

#### Scenario: 未配置同步源与并发（边界场景）

- **WHEN** 服务端未配置 `SOURCE_REPO`，或上一同步尚未结束时再次调用
- **THEN** 前者返回 40400，后者返回 50000；响应 MUST NOT 泄露仓库本机路径
