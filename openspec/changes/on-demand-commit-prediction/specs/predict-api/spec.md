## MODIFIED Requirements

### Requirement: 在线预测入口

`POST /api/predict` SHALL 对请求的 `commit_hash` 实时运行模型推理（MUST NOT 以查 `prediction` 表代替），返回 `commit_hash`、`model_name`、`risk_score`（0.0~1.0）、`predicted_at`（ISO 8601 UTC）、`features` 与 `explanation`；`model_name` 缺省 SHALL 取注册表中版本序最大模型（`version_key`）。当服务端配置 `SOURCE_REPO` 且提交或特征行尚未入库时，系统 SHALL 从该本地 Git 仓库现算与冻结 v1 一致的 14 项特征并落库后推理；仓库路径 MUST NOT 由请求方提供。

#### Scenario: 正常预测

- **WHEN** 以库中存在且含特征行的 `commit_hash` 调用
- **THEN** 返回实时推理得到的 `risk_score` 与 `explanation`，`features` 为 `commit_feature` 中口径处理后的值

#### Scenario: 缺省模型

- **WHEN** 请求体不带 `model_name` 且注册表含多个模型
- **THEN** 使用注册表中最新的模型并在响应中回显其 `model_name`

#### Scenario: 新提交现算

- **WHEN** 提供 40 位哈希对应的提交在配置的 `SOURCE_REPO` HEAD 可达、且库中缺少提交或特征行
- **THEN** 复用模型线 v1 入口算出 14 项、落 `commit` 与 `commit_feature`，再实时推理；同键重复请求不产生重复行

### Requirement: 预测数据缺失错误

未配置 `SOURCE_REPO` 时，`commit_hash` 不在 `commit` 表 SHALL 返回 40400、message `commit not found`；提交在 `commit_feature` 表无特征行 SHALL 返回 40400、message `features not found for this commit`。已配置来源但目标提交不可达 SHALL 返回同一 40400；来源仓库无法读取或特征抽取内部失败 SHALL 返回 50000 且不得回显服务端路径。

#### Scenario: 提交不存在

- **WHEN** 以格式合法但不在 `commit` 表且无法从配置来源找到的哈希调用
- **THEN** 返回 40400 且 message 为 `commit not found`

#### Scenario: 特征行缺失

- **WHEN** 提交存在但 `commit_feature` 表无对应行，且未配置可达来源
- **THEN** 返回 40400 且 message 为 `features not found for this commit`

#### Scenario: 配置的来源不可用

- **WHEN** `SOURCE_REPO` 指向不存在或损坏的本地仓库
- **THEN** 返回 50000，message 为固定内部错误文案，不含仓库路径
