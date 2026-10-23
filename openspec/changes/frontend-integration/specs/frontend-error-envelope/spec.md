## Purpose

三页共用请求层将后端业务错误码传递给页面，使三态与操作入口在 HTTP 错误时仍符合接口契约。

## ADDED Requirements

### Requirement: 非 2xx 错误包络归一

前端请求层 MUST 同时处理成功 HTTP 响应中的非零 `code` 和非 2xx HTTP 响应体中的 `{code,message,data}`。已知业务码 MUST 传递给页面，展示文案 MUST 按 `docs/frontend/pages.md` 第 5 节处理；50000 MUST NOT 将服务端原文直接展示。无业务包络的网络错误 MUST 保留为网络错误，不得伪造业务码。

#### Scenario: 后端返回 40400

- **WHEN** `GET /api/commits/{commit_hash}` 返回 HTTP 404 且响应体 `code=40400`
- **THEN** 详情页收到 `40400`，显示「该提交不存在」和「返回列表」入口

#### Scenario: 后端返回 50000

- **WHEN** 任一页面收到 HTTP 500 且响应体 `code=50000`
- **THEN** 页面显示统一服务错误提示与重试入口，MUST NOT 展示服务端内部错误文本

#### Scenario: 连接失败

- **WHEN** 请求未收到 HTTP 响应体
- **THEN** 请求层保留网络错误，MUST NOT 将其误判为 40001/40100/40400/50000
