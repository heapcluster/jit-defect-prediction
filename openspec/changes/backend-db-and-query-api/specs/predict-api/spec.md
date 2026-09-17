## Purpose

落地课程要求的「对外提供在线预测服务」：启动时加载模型文件（方案 A），`POST /api/predict` 对库中提交实时推理并给出 SHAP 解释，结果按幂等口径落 `prediction` 表。

## ADDED Requirements

### Requirement: 模型加载

系统 SHALL 在启动时从 `MODEL_DIR`（`.env` 配置，默认 `data_model/models/`）加载 `.pkl` 模型文件并建立注册表；`model_name` SHALL 取文件名主干；加载失败 SHALL NOT 阻断服务启动。

#### Scenario: 正常加载

- **WHEN** `MODEL_DIR` 下存在可反序列化的 `.pkl` 文件
- **THEN** 启动日志记录已加载的 `model_name` 清单，注册表可按名取用

#### Scenario: 模型文件缺失或损坏

- **WHEN** `MODEL_DIR` 为空或某文件反序列化失败
- **THEN** 服务照常启动、查询接口可用；失败详情只写服务端日志，MUST NOT 在任何响应中回显文件路径

### Requirement: 在线预测入口

`POST /api/predict` SHALL 对请求的 `commit_hash` 实时运行模型推理（MUST NOT 以查 `prediction` 表代替），返回 `commit_hash`、`model_name`、`risk_score`（0.0~1.0）、`predicted_at`（ISO 8601 UTC）、`features` 与 `explanation`；`model_name` 缺省 SHALL 取注册表中最新模型。

#### Scenario: 正常预测

- **WHEN** 以库中存在且含特征行的 `commit_hash` 调用
- **THEN** 返回实时推理得到的 `risk_score` 与按 design D8 计算的 `explanation`，`features` 为 `commit_feature` 中口径处理后的值

#### Scenario: 缺省模型

- **WHEN** 请求体不带 `model_name` 且注册表含多个模型
- **THEN** 使用注册表中最新的模型并在响应中回显其 `model_name`

### Requirement: 预测请求校验

请求体 `commit_hash` SHALL 为必填且为 40 位十六进制字符串；缺失或格式不符 SHALL 返回 40001（HTTP 400）。

#### Scenario: 缺失 commit_hash

- **WHEN** 请求体为空对象
- **THEN** 返回 40001，message 指出参数名 `commit_hash`

#### Scenario: 哈希格式非法

- **WHEN** `commit_hash` 为 39 位或含非十六进制字符
- **THEN** 返回 40001，message 指出参数名与格式要求

### Requirement: 预测数据缺失错误

`commit_hash` 不在 `commit` 表 SHALL 返回 40400、message `commit not found`；该提交在 `commit_feature` 表无特征行 SHALL 返回 40400、message `features not found for this commit`。

#### Scenario: 提交不存在

- **WHEN** 以格式合法但不在 `commit` 表的哈希调用
- **THEN** 返回 40400 且 message 为 `commit not found`

#### Scenario: 特征行缺失

- **WHEN** 提交存在但 `commit_feature` 表无对应行
- **THEN** 返回 40400 且 message 为 `features not found for this commit`

### Requirement: 模型不可用错误

预测所需模型缺失或加载失败 SHALL 返回 50000（HTTP 500），message 为固定文案；异常详情 SHALL 只写服务端日志。

#### Scenario: 无可用模型

- **WHEN** 注册表为空时调用 predict
- **THEN** 返回 50000 且 message 不回显任何文件路径

### Requirement: 预测结果幂等落库

predict 成功后 SHALL 将结果写入 `prediction` 表（聊天第三条：A 与 C 写同一张表、靠 `model_name` 区分）；同一 `(commit_hash, model_name)` 重复调用 SHALL 只保留最新一行（update-or-insert，design D7），MUST NOT 累积重复行。

#### Scenario: 重复调用不累积

- **WHEN** 对同一 `(commit_hash, model_name)` 连续调用两次 predict
- **THEN** `prediction` 表中该键仅一行，`predicted_at` 与 `risk_score` 为第二次调用的值

#### Scenario: 换模型名新增行

- **WHEN** 以不同 `model_name` 对同一提交各调用一次
- **THEN** `prediction` 表中该提交有两行，互不覆盖

### Requirement: SHAP 解释

`explanation` SHALL 由 SHAP 计算（树模型用 TreeExplainer，线性模型用 LinearExplainer，见 design D8），逐项含 `feature` / `contribution` / `direction`；`feature` 的键名 SHALL 与 `features` 同一套列名。

#### Scenario: 树模型解释

- **WHEN** 注册模型为树族模型且预测成功
- **THEN** `explanation` 非空，每项 `direction` 取 `increase` 或 `decrease`，`contribution` 为非负数

#### Scenario: 不支持的解释器

- **WHEN** 注册模型类型无对应 SHAP Explainer
- **THEN** `risk_score` 照常返回、`explanation` 为空数组，并写服务端日志说明原因
