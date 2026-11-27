## MODIFIED Requirements

### Requirement: 统一包络与错误码

所有接口 SHALL 返回 `{ "code": 0, "message": "ok", "data": {...} }` 包络；错误码 SHALL 只取 `docs/backend/api-spec.md`（契约三 v1.5）的 0 / 40001 / 40100 / 40400 / 50000，MUST NOT 自造。

#### Scenario: 成功响应

- **WHEN** 任一接口请求成功
- **THEN** 响应体 `code` 为 0，业务载荷位于 `data`

#### Scenario: 分页越界

- **WHEN** 以 `size=101` 调用 `GET /api/commits`
- **THEN** 返回 40001（HTTP 400），message 指出参数名 `size` 与上限 100

#### Scenario: 上限边界值

- **WHEN** 以 `size=100` 调用 `GET /api/commits`
- **THEN** 正常返回至多 100 条，MUST NOT 判为非法

### Requirement: Swagger 实现镜像

系统 SHALL 暴露 FastAPI 自动生成的 OpenAPI/Swagger；生成 schema 中的路径、字段名与类型 SHALL 与 `docs/backend/api-spec.md`（契约三 v1.5）逐字一致，偏离 SHALL 修改代码消除，MUST NOT 反向修改契约。

#### Scenario: 镜像比对零偏离

- **WHEN** 导出 `openapi.json` 与契约三四个接口逐字段比对
- **THEN** 路径、字段名、类型与枚举无偏离

#### Scenario: 发现偏离

- **WHEN** 比对发现实现与契约不一致
- **THEN** 修改代码对齐契约并重新比对，MUST NOT 以「改契约迁就代码」结案
