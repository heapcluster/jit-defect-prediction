## MODIFIED Requirements

### Requirement: 实时同步入库

系统 SHALL 只以实时同步端点（`POST /api/sync` 与 `POST /api/sync-prs`）作为**运行时**数据入库入口，MUST NOT 保留离线 CSV 灌库作为服务端入口路径。写入 SHALL 遵循 design D4 的按表幂等键（`commit` 按 `commit_hash`、`commit_label` 按 `(commit_hash, label_method)`、`commit_feature` 按 `commit_hash`、`prediction` 按 `(commit_hash, model_name)`）：同一键重复写入 MUST NOT 产生第二行。同步逐条处理时，单条预测失败 MUST 只影响该条并计入 `skipped`，MUST NOT 中断整批，MUST NOT 使整端返回 50000。

**例外（本地开发初始化）**：仓库根的 `infra/bootstrap_dev.py` SHALL 属开发者手工执行的初始化工具，只把仓库内既有的数据线产物一次性导入开发库并预跑预测；它 MUST NOT 被任何服务进程、启动钩子或 CI 必需步骤调用，MUST NOT 承担增量同步职责（增量仍由 `POST /api/sync` / `POST /api/sync-prs` 完成）。

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

- **WHEN** 审查 `infra/bootstrap_dev.py` 的调用方
- **THEN** 只存在「开发者命令行」调用；任何 API 路由、应用启动流程或 CI 必需步骤引用它即为规格不一致

## ADDED Requirements

### Requirement: 本地开发数据初始化

系统 SHALL 提供仓库根脚本 `infra/bootstrap_dev.py`，供开发者把仓库内已有的数据线产物
（`data_model/data/commits.csv`、`commit_features.csv`、`dataset_szz.csv`）一次性导入 `backend/.env`
所配的 MySQL 库，并用真实权重（`data_model/pipelines/expert/models/`）为已导入的提交预跑预测，
使「列表 / 详情 / 趋势」三页在首次 clone 后即有真实规模数据。

导入 SHALL 幂等：重复执行 MUST NOT 产生重复行；SHALL 支持 `--limit`（取最新 N 条提交）、
`--models`（指定预跑哪些模型）、`--reset`（清空重建）与 `--skip-predict`。
脚本 MUST NOT 打印数据库口令，MUST NOT 写入仓库外路径。

#### Scenario: 首次初始化

- **WHEN** 在干净 clone 上按 `README` 配好 `backend/.env` 后执行 `python infra/bootstrap_dev.py`
- **THEN** `commit` / `commit_feature` / `commit_label` / `prediction` 四表有数据，命令退出码为 0，并打印各表行数

#### Scenario: 重复执行（异常 / 边界）

- **WHEN** 连续执行两次 `python infra/bootstrap_dev.py`
- **THEN** 四表行数不变（按主键/幂等键跳过已存在行），MUST NOT 报错

#### Scenario: 与实时同步共存

- **WHEN** 初始化完成后调用 `POST /api/sync` 同步新的提交
- **THEN** 新提交按实时口径入库，初始化写入的历史行不受影响，也不被重复写入
