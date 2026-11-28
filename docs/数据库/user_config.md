# user_config

## 用途

按用户存储个人配置；与页面进度分开存放。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `user_id` | CHAR(36) | 否 | — | 归属用户 |
| `config_key` | VARCHAR(64) | 否 | — | 配置键 |
| `value_json` | TEXT | 否 | — | 配置值，JSON 编码 |
| `updated_at` | DATETIME | 否 | — | 最后更新时间 |

## 约束与索引

- 主键 `(user_id, config_key)`。
- 外键 `user_id` → `user.user_id`。
- 只允许写入已登记的配置键。

## 配置键

| 键 | 类型 | 默认 | 约束 |
|---|---|---|---|
| `estimate_warn_minutes` | 正整数 | 10 | 小于 `estimate_danger_minutes` |
| `estimate_danger_minutes` | 正整数 | 30 | 大于 `estimate_warn_minutes` |

- 未保存的键不落库；读取时不补齐默认值。

## 读写方

- 写入：`PUT /api/config`。
- 读取：`GET /api/config`、任务预估耗时。
