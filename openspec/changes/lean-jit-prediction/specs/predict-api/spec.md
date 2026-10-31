## ADDED Requirements

### Requirement: 冠军模型配置

系统 SHALL 维护一个「冠军模型」配置；配置缺失或指向未加载模型时回退到注册表中版本序最大模型（`version_key`）作为冠军候选。读写路径 SHALL 共用 `default-model-resolution` 的有效默认模型解析入口，MUST NOT 在本变更另定义解析顺序。

`POST /api/predict` 在请求未指定 `model_name` 时 SHALL 使用全站有效默认模型解析入口，并在响应 `model_name` 中回显实际所用模型。

> 有效默认模型的单一完整判据由 `default-model-resolution` change 承接，本 Requirement 只声明引用关系与响应回显。

#### Scenario: 冠军缺省

- **WHEN** 请求体不带 `model_name`，且 `runtime_setting.champion_model = "tabnet_v1"`（已加载）
- **THEN** 用 `tabnet_v1` 推理，响应 `model_name` 为 `tabnet_v1`

#### Scenario: 冠军未配置时回退

- **WHEN** 请求体不带 `model_name`，且 `runtime_setting` 中没有 `champion_model`
- **THEN** 若有已加载模型存在预测行，使用其中 `version_key` 最大者；否则使用注册表中 `version_key` 最大模型，响应回显实际 `model_name`，HTTP 200

#### Scenario: 冠军配置了未交付的模型

- **WHEN** `champion_model` 指向一个不在交付清单内、因而未加载的模型名
- **THEN** 在服务端日志记录告警，再按有效默认模型顺序选择已加载模型，请求仍 200

### Requirement: 批量预测的模型范围

批量入口（`POST /api/sync`、`POST /api/sync/catchup`、`POST /api/sync-prs`）默认 SHALL 对全部已加载模型逐一打分并按 `(commit_hash, model_name)` 幂等落库；每条提交最多写入与已加载模型数相同的预测行。

每条提交 SHALL 只现算一次特征，再逐模型打分；MUST NOT 把 `all_models=true` 当作全模型落库的前置条件。

响应 SHALL 回显本次实际使用的模型清单（`models` 数组），调用方 MUST NOT 靠 `prediction` 表行数反推跑了几种模型。

#### Scenario: 默认全模型同步

- **WHEN** `POST /api/sync?limit=10`（不带 `all_models`），且这 10 条均无预测
- **THEN** 每条提交对全部已加载模型产生预测行；若已加载 8 个模型，最多新增 80 行，响应 `models` 长度为 8

#### Scenario: 显式参数不得缩小落库范围

- **WHEN** 调用方未传 `all_models` 或仍传旧参数，且已加载 8 个模型
- **THEN** 全模型落库范围保持 8 项；未支持的旧参数不得改变默认范围

#### Scenario: 幂等

- **WHEN** 对同一批提交重复调用上述任一入口
- **THEN** 不新增重复行（幂等键仍为 `(commit_hash, model_name)`），响应 `new` 为 0

### Requirement: 库内数据范围只由实时同步决定

系统 SHALL 只通过实时同步端点（`POST /api/sync`、`POST /api/sync/catchup`、`POST /api/sync-prs`）获得提交、特征与预测数据。

系统 MUST NOT 提供种子数据、离线 CSV 导入或历史全量回填通道；任何把既有数据文件批量灌入数据库的脚本 MUST NOT 被引入仓库，也 MUST NOT 被服务进程、启动钩子或 CI 必需步骤调用。

单次同步的范围 SHALL 由 `limit` 决定（`1..50`），语义固定为「最新 N 条」；MUST NOT 提供「从最早开始」或「补齐全部历史」的翻页式回填。

#### Scenario: 空库首启

- **WHEN** 空库第一次执行 `POST /api/sync?limit=10`
- **THEN** 库里只有最新 10 条提交及其预测；`GET /api/commits` 返回 `total=10`，MUST NOT 出现任何来自数据文件的额外行

#### Scenario: 不接受无界回填

- **WHEN** 调用方请求 `limit=5000`
- **THEN** 返回 40001（`limit` 需在 1..50），MUST NOT 静默截断成 50 条

#### Scenario: 数据贬值防护

- **WHEN** 特征口径升到 `v2` 或模型换版本
- **THEN** 库内没有按旧口径批量预置的历史行可供误读；新数据仍由实时同步产生

### Requirement: 预测入口分层

系统 SHALL 把「实时」与「显式拉取」分开，避免事件或启动触发演变成大规模重算：

- 实时入口（webhook 事件、PR 打开/更新）SHALL 只处理最新 `WEBHOOK_SYNC_LIMIT` 条提交与该 PR 内的提交；
- 显式入口（`POST /api/sync?limit=N`、`POST /api/sync/catchup`）SHALL 只由调用方触发，MUST NOT 在服务启动时自动执行；
- `SYNC_ON_STARTUP=1` 时，启动同步 SHALL 只处理 `SYNC_INITIAL_LIMIT` 条（默认 10），MUST NOT 追平历史。

#### Scenario: 启动不追历史

- **WHEN** 服务以 `SYNC_ON_STARTUP=1` 启动，且库内为空
- **THEN** 最多预测 `SYNC_INITIAL_LIMIT` 条提交，随后转入空闲，MUST NOT 持续拉取历史

#### Scenario: 事件触发不越界

- **WHEN** 收到一个 `opened` webhook
- **THEN** 只对最新 `WEBHOOK_SYNC_LIMIT` 条提交与该 PR 的提交补算，MUST NOT 触发更大范围扫描

### Requirement: 门禁阈值按评审预算（phase 2）

质量看板 SHALL 提供「按评审预算」视图：给定阈值后展示该阈值下在预算内（LOC 或文件数口径）可审到的缺陷占比（Recall@20% / Recall@50%），数据 MUST 来自离线 effort-aware 报告，前端 MUST NOT 自行重算。

#### Scenario: 预算视图随阈值变化

- **WHEN** 用户在质量看板把阈值从 0.5 调到 0.3
- **THEN** 预算曲线与 Recall@20% / @50% 随之更新，且与 `data_model/pipelines/expert/reports/model_metrics.md` 的口径一致
