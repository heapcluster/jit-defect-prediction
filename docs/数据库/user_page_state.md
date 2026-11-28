# user_page_state

## 用途

按用户与页面保存流程进度，用于刷新、重新登录后恢复。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `user_id` | CHAR(36) | 否 | — | 归属用户 |
| `page` | VARCHAR(16) | 否 | — | 页面标识 |
| `state_json` | MEDIUMTEXT | 否 | — | 进度内容，JSON 编码 |
| `updated_at` | DATETIME | 否 | — | 最后更新时间 |

## 约束与索引

- 主键 `(user_id, page)`。
- 外键 `user_id` → `user.user_id`。
- `page` 取值：`collect`、`clean`、`train`、`predict`、`evaluate`、`storage`。
- `state_json` 序列化后不超过 64KB；只存引用，不存结果行数据。

## 读写方

- 写入：`PUT /api/page-state/{page}`，整份覆盖。
- 读取：`GET /api/page-state/{page}`；无记录返回空。
- 删除：`DELETE /api/page-state/{page}`，同时清理其引用的未入库产物。
