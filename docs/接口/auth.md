# 接口 auth

## 1 POST /api/auth/login

登录并建立会话。

请求：

```json
{ "username": "alice", "password": "******" }
```

响应 `200`，同时下发 `Set-Cookie: jit_session=...`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user": { "user_id": "u_...", "username": "alice", "display_name": "Alice", "created_at": "2026-11-27T10:00:00+08:00" }
  }
}
```

- 服务端生成随机令牌，Cookie 返回原始令牌，`user_session` 只存其 SHA-256 摘要。
- 会话有效期 7 天，登录时写入 `expires_at`；重复登录产生新会话，不踢掉旧会话。

错误：

| code | 场景 |
|---|---|
| 40001 | 用户名或密码为空、超长 |
| 40101 | 用户名或密码错误（统一文案，不区分哪一项） |
| 50301 | 数据库不可用 |

## 2 POST /api/auth/logout

销毁当前会话，清除 Cookie。

- 删除当前 `user_session` 行；删除后同一令牌再次访问返回 `40101`。
- 响应：`{ "code": 0, "message": "ok", "data": null }`

## 3 GET /api/auth/me

返回当前用户信息与资产概览，用于页头与数据存储页。

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "user_id": "u_...",
    "username": "alice",
    "display_name": "Alice",
    "created_at": "2026-11-27T10:00:00+08:00",
    "last_login_at": "2026-11-27T10:00:00+08:00",
    "counts": { "datasets": 3, "models": 1 }
  }
}
```

- 未登录返回 `40101`。
- `counts` 只统计当前用户资产。

## 4 约束

- 口令按明文比对与存储，仅用于课程演示；部署到真实环境前必须先改为哈希存储。接口不回传任何口令字段。
- 会话只存令牌摘要；会话过期、登出或账号被禁用后立即不可用。
- 账号由初始化环节创建，不提供注册接口。
- 不提供修改密码、找回密码、注销账号接口。
