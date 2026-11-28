# user_session

## 用途

登录会话。服务端保存会话记录，浏览器 Cookie 只持有原始令牌；登出或过期后立即失效。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `session_id` | CHAR(64) | 否 | — | 令牌的 SHA-256 十六进制摘要，主键；Cookie 中为原始令牌 |
| `user_id` | CHAR(36) | 否 | — | 归属用户 |
| `created_at` | DATETIME | 否 | — | 登录建立会话的时间 |
| `last_seen_at` | DATETIME | 否 | — | 最近一次通过该会话访问的时间 |
| `expires_at` | DATETIME | 否 | — | 过期时间，登录时定为 7 天后 |

## 约束与索引

- 主键 `session_id`；外键 `user_id` → `user.user_id`（`ON DELETE CASCADE`）。
- 索引：`ix_user_session_user (user_id)`、`ix_user_session_expires (expires_at)`。
- 会话记录存 `user_session` 表，Cookie 只存原始令牌；服务端只保存令牌摘要。
- 会话有效期固定 7 天，不做滑动续期。
- 过期清理不设定时任务：鉴权时校验 `expires_at`，登录时顺带删除该用户的过期行。
- 账号 `status=disabled` 时，其全部会话在下一次鉴权即视为失效。

## 读写方

- 写入：`POST /api/auth/login` 校验通过后插入一行。
- 读取：每次鉴权按 `session_id` 查询并校验 `expires_at`，同时更新 `last_seen_at`。
- 删除：`POST /api/auth/logout` 删除当前行；过期行在鉴权时视为无效、登录时顺带删除；用户被删除时随外键级联删除。
