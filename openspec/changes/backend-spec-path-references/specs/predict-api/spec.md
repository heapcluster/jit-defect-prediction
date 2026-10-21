## MODIFIED Requirements

### Requirement: 模型加载

系统 SHALL 在启动时从 `MODEL_DIR`（`.env` 配置，默认 `data_model/pipelines/expert/models/`）加载 `.pkl` 模型文件并建立注册表；`model_name` SHALL 取文件名主干；加载失败 SHALL NOT 阻断服务启动。

#### Scenario: 正常加载

- **WHEN** `MODEL_DIR` 下存在可反序列化的 `.pkl` 文件
- **THEN** 启动日志记录已加载的 `model_name` 清单，注册表可按名取用

#### Scenario: 模型文件缺失或损坏

- **WHEN** `MODEL_DIR` 为空或某文件反序列化失败
- **THEN** 服务照常启动、查询接口可用；失败详情只写服务端日志，MUST NOT 在任何响应中回显文件路径
