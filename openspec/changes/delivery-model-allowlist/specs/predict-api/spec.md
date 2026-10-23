## MODIFIED Requirements

### Requirement: 模型加载

系统 SHALL 在启动时从 `MODEL_DIR`（`.env` 配置，默认 `data_model/pipelines/expert/models/`）读取 `feature_order.txt` 的 `[models]` 与 `[feature_order]`，并且仅加载清单声明、列序与 `docs/model/feature-columns.md` 一致的 `.pkl` 权重；`model_name` SHALL 取文件名主干。清单缺失或列序不符 SHALL 使注册表保持空；单个权重加载失败 SHALL NOT 阻断查询服务启动，失败详情 MUST NOT 在响应中回显路径。

#### Scenario: 正常加载

- **WHEN** `MODEL_DIR` 下有有效清单和可反序列化的已声明 `.pkl` 文件
- **THEN** 启动日志记录已加载的 `model_name` 清单，注册表可按名取用

#### Scenario: 三模型交付目录含额外训练权重

- **WHEN** 清单声明 `lr_v1` / `rf_v1` / `xgb_v1`，目录同时存在其他训练 `.pkl`
- **THEN** 注册表只含三个交付模型，额外权重不被反序列化或暴露为可预测模型

#### Scenario: 清单缺失或特征列序漂移

- **WHEN** 交付目录没有 `feature_order.txt`，或其 `[feature_order]` 不等于冻结的 14 项列序
- **THEN** 注册表为空、查询接口仍可启动、预测返回既有 50000，错误详情只写服务端日志

#### Scenario: 模型文件缺失或损坏

- **WHEN** 清单中某个 `.pkl` 不存在或反序列化失败
- **THEN** 仅跳过该模型，服务照常启动；MUST NOT 在任何响应中回显文件路径
