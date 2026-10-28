## ADDED Requirements

### Requirement: 拉取 open PR 并实时预测入库

服务端 SHALL 提供 `POST /api/sync-prs?limit=N`（N 默认 10、上限 50）：拉取 `GITHUB_REPO` 的 open PR 清单，逐 PR 将 head ref 取入本地历史索引（MUST 仅 `git fetch` 取对象、MUST NOT checkout），取该 PR 提交清单后**逐提交复用单条多模型预测链**（一次现算特征 → 逐模型打分 → 幂等写 `prediction`），返回 `{prs_scanned, commits_predicted, prs[], skipped[]}` 汇总。`SOURCE_REPO` 未配置或失效 SHALL 返回 40400；`limit` 越界 SHALL 返回 40001；单 PR fetch 失败与单提交预测失败 MUST 计入 `skipped` 而非中断整批。错误码 MUST 使用冻结集合（0/40001/40400/50000），MUST NOT 新增错误码。

#### Scenario: open PR 逐提交预测入库

- **WHEN** 服务端已配置 `SOURCE_REPO` 与 `GITHUB_REPO`，上游存在 open PR
- **THEN** 每个 PR 的提交逐条现算特征后以各在线模型预测入库，`prs[]` 报各 PR 的 `commits_predicted`，查询接口可按 PR 查到新行

#### Scenario: PR head 不在本地 HEAD 历史上

- **WHEN** fetch 已取得 PR head，但其提交不在 `SOURCE_REPO` 的 HEAD 可达历史中
- **THEN** 服务端 SHALL 使用以 PR head 为 HEAD 的一次性 detached `--no-checkout` worktree 进行特征抽取，并在成功或失败后释放；MUST NOT 改变 `SOURCE_REPO` 的 HEAD、分支、索引或未提交文件

#### Scenario: 单 PR 失败不中断（边界场景）

- **WHEN** 某 PR 的 head ref fetch 失败或其某提交现算失败
- **THEN** 该 PR/该提交计入 `skipped`，其余 PR 与提交继续处理，整批响应仍为 `code=0`

### Requirement: open PR 聚合风险查询

服务端 SHALL 提供 `GET /api/prs`（`limit` 默认 20 上限 50、`model_name` 默认取全局默认模型）：返回 open PR 列表及其聚合风险，`risk_score` 为该 PR 各提交在指定模型下的最高风险分（无预测为 `null`，MUST NOT 用 0.0 冒充），并附 `commit_count` / `predicted_count` / `predicted_at`（ISO 8601 带 `Z`）。本端点为**纯只读**，数据来自 GitHub API 与 `prediction` 表，MUST NOT 依赖 `SOURCE_REPO`（未配置历史索引时照常返回库内数据，MUST NOT 返回 40400）；单个 PR 的提交清单拉取失败 MUST 只计入 `skipped` 计数，其余 PR 照常返回，MUST NOT 整端 50000。

#### Scenario: 未配置历史索引时仍可查询（边界场景）

- **WHEN** 服务端未配置 `SOURCE_REPO`，但库内已有 PR 提交的预测行
- **THEN** `GET /api/prs` 返回 `code=0` 与聚合风险，MUST NOT 因缺历史索引返回 40400

#### Scenario: 单 PR 聚合失败被隔离（边界场景）

- **WHEN** 某 PR 的提交清单拉取失败（如 GitHub 限额）
- **THEN** 该 PR 不出现在 `items` 且 `skipped` 计数 +1，其余 PR 正常返回，整端 `code=0`

### Requirement: 单个 PR 的提交级风险明细

服务端 SHALL 提供 `GET /api/prs/{number}`（`model_name` 口径同列表端）：返回该 PR 元信息与 `commits[]`（`sha` `message` `author` `risk_score` `predicted_at`，按 PR 内提交时间正序，`message` 截断至 200 字符）。库内无预测的提交 `risk_score`/`predicted_at` SHALL 为 `null`（「尚未预测」），MUST NOT 返回 40400、MUST NOT 用 0.0 冒充。本端点同为**纯只读**，MUST NOT 依赖 `SOURCE_REPO`。

#### Scenario: 未预测提交渲染为「尚未预测」（边界场景）

- **WHEN** PR 内某提交在 `prediction` 表无对应模型的行
- **THEN** 该提交 `risk_score`/`predicted_at` 为 `null`，其余提交照常返回预测值
