# user

## 用途

账号与登录凭据。系统无角色分级，所有用户权限相同。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `user_id` | CHAR(36) | 否 | — | 主键 |
| `username` | VARCHAR(64) | 否 | — | 登录名，唯一，大小写敏感 |
| `password` | VARCHAR(128) | 否 | — | 登录口令，课程演示项目按明文存储；禁止用于生产环境 |
| `display_name` | VARCHAR(64) | 否 | — | 页面展示名 |
| `status` | VARCHAR(16) | 否 | `active` | `active` / `disabled` |
| `created_at` | DATETIME | 否 | — | 创建时间 |
| `last_login_at` | DATETIME | 是 | NULL | 最近一次登录成功时间 |

## 约束与索引

- 主键 `user_id`；唯一键 `uk_user_username (username)`。
- `username` 与 `password` 使用 `utf8mb4_bin` 排序规则，大小写敏感；`Alice` 与 `alice` 是两个不同账号。
- `status=disabled` 的账号登录失败，错误文案与口令错误一致。
- 口令按明文比对与存储，仅用于课程演示；部署到真实环境前必须先改为哈希存储。

## 读写方

- 写入：初始化脚本创建账号；登录成功更新 `last_login_at`。
- 读取：`POST /api/auth/login`、`GET /api/auth/me`、归属校验。
- 不提供注册、改密、注销接口。
