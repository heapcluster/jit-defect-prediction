# 模型清单与生命周期 API（models）

一句话：提供架构到模型的只读级联清单，以及模型状态、加载、卸载、重载和默认模型管理，所有加载都以模型包校验为前提。

实现状态：已实现　期次：一期

模型包契约见 [../file-contracts.md](../file-contracts.md) §3.3；默认配置见 [config.md](config.md)，训练交付见 [train.md](train.md)。

## 1. 职责与不负责范围

- 负责可用模型清单、工件状态与运行时状态、显式加载/卸载/重载、默认模型设置与加载失败原因。
- 模型名单的登记源为 model_artifact，model 行由工件派生；独立文件运行可直接上传模型包，不要求先登记。
- 不负责训练、预测计算、解释或评估；GET 清单不触发加载，页面刷新不隐式重载模型。
- 不通过扫描未知目录建立第二份模型名单，不加载 checksum 或特征元数据不符的包。

## 2. 端点契约

### GET /api/models

可选 `line=expert|semantic|fused|e2e`。响应 `data.lines[]` 按 expert/semantic/fused/e2e 排列，每项 `{line,label,models[]}`；models 为可用 model_name 字符串数组，空线返回空数组。

### GET /api/models/status

可选 `line`、`model_name`。响应：

| 字段 | 含义 |
|---|---|
| `default_model` | 实际默认模型；未配置时按回退规则解析 |
| `items[]` | 逐模型状态 |
| `items[].model_name` / `line` / `algo` | 标识与算法 |
| `items[].artifact_status` | `available` / `load_failed` / `retired` |
| `items[].runtime_state` | `loaded` / `loading` / `load_failed` / `unloaded` |
| `items[].load_error` | 脱敏失败原因，成功为 null |
| `items[].version_key` / `feature_version` / `trained_at` | 版本元信息 |
| `items[].checksum_sha256` | 登记校验值 |

### POST /api/models/{name}/load

无请求体；从已登记工件加载 name。响应 `{model_name,runtime_state,load_error}`。加载前校验 §3.3 包；失败返回明确状态，不破坏上一个可用模型。

### POST /api/models/{name}/unload

无请求体；响应同上。默认模型不可直接卸载，须先更换默认；登记资产不删除。

### POST /api/models/{name}/reload

无请求体；重新读取登记包并复验 checksum、内部元数据和特征列宽后替换运行时实例。失败保留旧实例并返回 load_failed 原因。

### PUT /api/models/default

请求 `{model_name}`，仅接受 available 模型；写入 user_config.default_model，响应 `{default_model}`。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | line/操作非法、模型不可用、卸载默认模型、重复非法状态流转、包校验失败 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | model_name 或登记工件不存在 |
| 50000 | 500 | 未预期内部错误；可预期加载失败以 runtime_state/load_error 表达 |

## 3. 输入契约

管理输入为模型标识和登记工件；独立预测/解释运行则可直接上传 §3.3 模型包。§3.3 逐字规定：

> zip 内含：权重文件（expert/semantic/fused 为 `.pkl`；e2e 为 safetensors 目录）、`feature_order.txt`、`model_meta.json`（model_name/line/algo/version_key/feature_version/trained_at/超参快照/划分/种子）、`checksum.sha256`。predict/explain MUST 校验 checksum 与特征列宽后再加载。

models 加载执行相同校验，并限制 ZIP 路径穿越、文件数量、解压大小和反序列化资源。登记路径必须位于允许资产根内，文件名不拼接 shell。模型版本、line、algo 和 feature_version 必须与登记一致。

## 4. 输出契约

只输出 JSON 清单与状态，不生成新的模型文件或 manifest。模型包及其同名 manifest 由 train run 产生并经 `GET /api/train/outputs/{job_id}/{name}` 下载；models 不复制工件、不另建输出目录。

GET /api/models 只返回选择器所需字段；版本、状态和 checksum 经 status 获取。所有错误原因脱敏，不泄露绝对路径、堆栈或密钥。

## 5. 可配置项

- `default_model` 是唯一默认模型配置；PUT models/default 与 PUT config/default_model 写同一行。
- 未配置时回退已加载 expert 中 version_key 最大者；显式配置失效时返回明确状态，不静默改选其他线模型。
- 自动加载由 train 的 auto_load 或显式 load 控制；auto_load 不改默认模型。
- `.env` 仅提供出厂默认；运行时加载态不必写 user_config，资产与默认配置必须持久化。

## 6. 状态持久化

- model_artifact 持久保存路径、checksum、版本和工件状态，model 行由其派生；runtime_state 反映进程实际加载情况。
- 重启后按 default_model 恢复加载；加载失败保留原因并回退上一个可用模型，ready 探针据实降级。
- 不创建 job，不在 models 端点下写业务输出；加载日志脱敏，可用于排障。
- 训练登记的新工件无需重启即可出现在清单；retired 不可选但保留追溯记录。

## 7. 验收

fixtures：`tests/fixtures/files/models/`，包含合法模型包、损坏包、checksum 不符包和元数据不匹配包。

- **正常**：四线清单、状态查询、load/unload/reload/default 全路径通过；设置默认后重启仍生效，predict/commits/trends 缺省模型一致。
- **边界**：空模型线、懒加载、默认模型回退、加载失败保留旧实例、retired 资产追溯均符合状态语义。
- **非法**：路径穿越、checksum 不符、列宽/版本不符、未登记模型、卸载默认模型、非法 line 均返回 40001/40400，旧模型不受影响。
- 只写文件未登记不出现在管理清单，但可作为 predict/explain run 的显式上传输入；任何 GET 不触发计算或加载。

## 8. 边界

models 是模型资产管理面，不是模块间文件总线。train 通过 §3.3 交付，predict/explain 可独立校验并加载包；model_artifact 登记只提供可选展示与管理便利，数据库不是文件预测的前置。
