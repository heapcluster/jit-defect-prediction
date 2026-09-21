# query-api Specification

## Purpose
把契约三 1.4 的三个查询接口落地为 FastAPI 实现：统一包络、错误码、`X-API-Key` 鉴权与输入校验，并以自动生成的 OpenAPI/Swagger 作实现镜像，保证规格与代码一致。

## Requirements

### Requirement: 统一包络与错误码

所有接口 SHALL 返回 `{ "code": 0, "message": "ok", "data": {...} }` 包络；错误码 SHALL 只取 `docs/contracts/api-format.md` 1.4 的 0 / 40001 / 40100 / 40400 / 50000，MUST NOT 自造。

#### Scenario: 成功响应

- **WHEN** 任一接口请求成功
- **THEN** 响应体 `code` 为 0，业务载荷位于 `data`

#### Scenario: 分页越界

- **WHEN** 以 `size=101` 调用 `GET /api/commits`
- **THEN** 返回 40001（HTTP 400），message 指出参数名 `size` 与上限 100

#### Scenario: 上限边界值

- **WHEN** 以 `size=100` 调用 `GET /api/commits`
- **THEN** 正常返回至多 100 条，MUST NOT 判为非法

### Requirement: 接口鉴权

四个接口（含 `POST /api/predict`）SHALL 校验请求头 `X-API-Key`；缺失或不匹配 SHALL 返回 40100（HTTP 401），message 固定为 `missing or invalid token`。

#### Scenario: 缺失令牌

- **WHEN** 不带 `X-API-Key` 头调用任一 `/api` 接口
- **THEN** 返回 40100 且 HTTP 状态为 401，message 为 `missing or invalid token`

#### Scenario: 非法令牌

- **WHEN** 携带与 `.env` 配置不符的令牌调用
- **THEN** 同样返回 40100，message MUST NOT 提示正确令牌的形式或长度

### Requirement: 风险列表查询

`GET /api/commits` SHALL 按 `risk_score` 降序返回提交列表，支持 `page`/`size` 分页（默认 1/20）与 `min_risk`/`model_name`/`start_time`/`end_time` 筛选；`items` SHALL 只取单个 `model_name` 的预测行，`model_name` 缺省 SHALL 取 `prediction` 表内模型中**版本序**（`version_key`，design D6）最大者，MUST NOT 跨模型混排（否则同一提交会翻出多条重复项）。

#### Scenario: 默认排序与分页

- **WHEN** 不带任何参数调用
- **THEN** `items` 按 `risk_score` 降序、返回第 1 页 20 条，`total` 为筛选后总数

#### Scenario: 筛选结果为空

- **WHEN** `min_risk` 高于全部已有风险值
- **THEN** 返回 `code` 0、`items` 空数组、`total` 0 —— 空数据不是错误

### Requirement: 提交详情查询

`GET /api/commits/{commit_hash}` SHALL 返回提交元信息、14 项特征值与 `explanation`；`features` SHALL 读自 `commit_feature` 表，键名与 `docs/contracts/feature-columns.md` 逐字一致；本响应 MUST NOT 返回真实标签。

#### Scenario: 哈希不存在

- **WHEN** 以不在 `commit` 表中的 `commit_hash` 查询
- **THEN** 返回 40400（HTTP 404），message 为 `commit not found`

#### Scenario: 提交存在但尚无预测

- **WHEN** 查询的提交在 `commit` 表存在但 `prediction` 表无对应行
- **THEN** 返回 `code` 0，`risk_score` 与 `model_name` 为 null、`explanation` 为空数组（口径见 design D3）

### Requirement: 趋势聚合查询

`GET /api/trends` SHALL 按 `granularity`（枚举 `week` 默认 / `month`）聚合风险趋势；SHALL 支持可选参数 `start_time`/`end_time`（ISO 8601 带时区，按 `committed_at` 过滤，缺省不限）与 `model_name`（缺省取表内版本序最大模型）；`high_risk_count` SHALL 由后端按**固定常量阈值 `risk_score >= 0.5`** 计算（本 change 不开放为请求参数 —— 契约三 §3 请求参数表未列该参数，见 design D10），MUST NOT 交由前端重算；`series` SHALL 只返回单个 `model_name` 的一组数据。

#### Scenario: 周粒度聚合

- **WHEN** 以默认参数调用
- **THEN** `series` 按周升序，每项含 `period`/`commit_count`/`avg_risk`/`high_risk_count`，`period` 格式形如 `2026-W30`

#### Scenario: 粒度取值非法

- **WHEN** 以 `granularity=day` 调用
- **THEN** 返回 40001（HTTP 400），message 指出参数名与合法枚举

#### Scenario: 时间范围内无数据

- **WHEN** 所选时间范围内没有任何提交
- **THEN** 返回 `code` 0、`series` 空数组 —— 空数据不是错误

### Requirement: 内部信息不回显

`50000` 的 message SHALL 为固定文案，MUST NOT 包含异常堆栈、SQL 语句、文件路径（含模型文件路径）；内部细节 SHALL 只写服务端日志。

#### Scenario: 内部错误掩盖

- **WHEN** 数据库连接中断等内部异常被触发
- **THEN** 响应为 50000（HTTP 500）且 message 为固定文案，服务端日志中保留完整异常

### Requirement: Swagger 实现镜像

系统 SHALL 暴露 FastAPI 自动生成的 OpenAPI/Swagger；生成 schema 中的路径、字段名与类型 SHALL 与 `docs/contracts/api-format.md` 1.4 逐字一致，偏离 SHALL 修改代码消除，MUST NOT 反向修改契约。

#### Scenario: 镜像比对零偏离

- **WHEN** 导出 `openapi.json` 与契约三四个接口逐字段比对
- **THEN** 路径、字段名、类型与枚举无偏离

#### Scenario: 发现偏离

- **WHEN** 比对发现实现与契约不一致
- **THEN** 修改代码对齐契约并重新比对，MUST NOT 以「改契约迁就代码」结案
