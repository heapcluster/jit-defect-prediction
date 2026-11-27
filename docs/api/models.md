# 模型清单与生命周期 API（models）

一句话：提供架构到模型的只读级联清单，以及模型状态、加载、卸载和重载，所有加载都以模型文件校验为前提；不管理默认模型。

模型文件契约见本文 §3 与 [train.md](train.md) 的训练产物契约；默认配置见 [config.md](config.md)。

## 1. 职责与不负责范围

- 负责可用模型清单、工件状态与运行时状态、显式加载/卸载/重载与加载失败原因。
- 模型名单的登记源为 model_artifact，model 行由工件派生；独立文件运行可直接上传模型文件（训练产物为 `.pkl`，外部交付包可为 ZIP），不要求先登记。
- 不负责训练、预测计算、解释或评估；GET 清单不触发加载，页面刷新不隐式重载模型。
- 不通过扫描未知目录建立第二份模型名单，不加载 checksum 或特征元数据不符的包。

## 2. 端点契约

### GET /api/models

可选 `line=expert|semantic`。响应 `data.lines[]` 按 expert/semantic 排列，每项 `{line,label,models[]}`；models 为可用 model_name 字符串数组，空线返回空数组。`line` 仅接受 `expert` / `semantic`，其他值返回 40001。

### GET /api/models/status

可选 `line`、`model_name`。响应：

| 字段 | 含义 |
|---|---|
| `selected_model` | 用户当前选择的模型，仅用于页面回显，不参与任何运行入口的自动填充 |
| `items[]` | 逐模型状态 |
| `items[].model_name` / `line` / `algo` | 标识与算法 |
| `items[].artifact_status` | `available` / `load_failed` / `retired` |
| `items[].runtime_state` | `loaded` / `loading` / `load_failed` / `unloaded` |
| `items[].load_error` | 脱敏失败原因，成功为 null |
| `items[].version_key` / `feature_version` / `trained_at` | 版本元信息 |
| `items[].checksum_sha256` | 登记校验值 |

### POST /api/models/{name}/load

无请求体；从已登记工件加载 name。响应 `{model_name,runtime_state,load_error}`。加载前校验模型文件（`.pkl` 或外部交付 ZIP）与侧车元数据、checksum、特征列宽；失败返回明确状态，不破坏上一个可用模型。

### POST /api/models/{name}/unload

无请求体；响应同上。已加载模型可直接卸载；登记资产不删除。

### POST /api/models/{name}/reload

无请求体；重新读取登记包并复验 checksum、内部元数据和特征列宽后替换运行时实例。失败保留旧实例并返回 load_failed 原因。

### PUT /api/models/selection

请求 `{model_name}`，仅接受 available 模型；只记录当前页面选择用于回显，不影响任何运行入口。`PUT /api/models/default` 不是有效端点，调用返回 40001。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | line/操作非法、模型不可用、重复非法状态流转、模型文件校验失败、调用无效的 default 端点 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | model_name 或登记工件不存在 |
| 50000 | 500 | 未预期内部错误；可预期加载失败以 runtime_state/load_error 表达 |

## 3. 输入契约

管理输入为模型标识和登记工件；独立预测 / 解释 / 定位运行也可直接上传模型文件：训练产物为单个 `.pkl`，外部交付可为 ZIP。默认契约如下：

> 训练产物：`train_<algo>_model_<job_id>.pkl` + 侧车 `train_<algo>_meta_<job_id>.json`（feature_order / feature_schema / 超参 / 划分 / 种子），checksum 由 manifest 登记。
> 外部交付 ZIP：内含权重文件 `.pkl`（`expert`=Kamei 14 维、`semantic`=冻结头 CodeBERT 768 维）、`feature_order.txt`、`model_meta.json`（model_name/line/algo/feature_set/version_key/feature_version/trained_at/超参快照/划分 mode/种子）、`checksum.sha256`。`fused` / `e2e` 及其 safetensors 产物已取消。predict/explain/source MUST 校验 checksum 与特征列宽后再加载。

models 加载执行相同校验，并限制 ZIP 路径穿越、文件数量、解压大小和反序列化资源。登记路径必须位于允许资产根内，文件名不拼接 shell。模型版本、line、algo 和 feature_version 必须与登记一致。

## 4. 输出契约

只输出 JSON 清单与状态，不生成新的模型文件或 manifest。训练产出的 `.pkl` 及其同名 manifest 经 `GET /api/train/outputs/{job_id}/{name}` 下载；models 不复制工件、不另建输出目录。

GET /api/models 只返回选择器所需字段；版本、状态和 checksum 经 status 获取。所有错误原因脱敏，不泄露绝对路径、堆栈或密钥。

## 5. 可配置项

- 不设默认模型；PUT models/selection 只记录当前页面选择用于回显，不参与任何运行入口的自动填充。
- 未选择模型时各运行入口返回 40001；选择失效时返回明确状态，不静默改选其他线模型。
- 自动加载由 train 的 auto_load 或显式 load 控制；auto_load 不改变当前选择。
- `.env` 仅提供出厂默认；运行时加载态不必写 user_config，资产登记必须持久化。

## 6. 状态持久化

- model_artifact 持久保存路径、checksum、版本和工件状态，model 行由其派生；runtime_state 反映进程实际加载情况。
- 重启后运行态加载清空，由用户显式选择或 train auto_load 触发加载；加载失败保留原因并维持上一个可用模型，ready 探针据实降级。
- 不创建 job，不在 models 端点下写业务输出；加载日志脱敏，可用于排障。
- 训练登记的新工件无需重启即可出现在清单；retired 不可选但保留追溯记录。

## 7. 验收

fixtures：`tests/fixtures/files/models/`，包含合法模型文件、损坏文件、checksum 不符文件和元数据不匹配文件。

- **正常**：两线清单、状态查询、load/unload/reload、selection 回显全路径通过；selection 只回显，不参与 predict/commits 等运行入口的模型缺省。
- **边界**：空模型线、懒加载、未选择模型时的空态、加载失败保留旧实例、retired 资产追溯均符合状态语义；不回退到默认模型。
- **非法**：路径穿越、checksum 不符、列宽/版本不符、未登记模型、卸载未加载模型、非法 line 均返回 40001/40400，旧模型不受影响。
- 只写文件未登记不出现在管理清单，但可作为 predict/explain run 的显式上传输入；任何 GET 不触发计算或加载。

## 8. 边界

models 是模型资产管理面，不是模块间文件总线。train 交付 `.pkl` 权重与侧车元数据，predict/explain/source 可独立校验并加载模型文件；model_artifact 登记只提供可选展示与管理便利，数据库不是文件预测的前置。

