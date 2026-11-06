# API 契约索引

当前接口按功能拆成七份正文，共十一个路由。所有请求与响应字段以对应文件为准；实际可用路径可与后端 `/openapi.json` 对照。旧 `docs/backend/api-spec.md` 的章节号已失效，不再引用。

| 文件 | 路由 |
|---|---|
| [`commits.md`](commits.md) | `GET /api/commits`、`GET /api/commits/{commit_hash}` |
| [`models.md`](models.md) | `GET /api/models` |
| [`predict.md`](predict.md) | `POST /api/predict` |
| [`sync.md`](sync.md) | `POST /api/sync`、`GET /api/sync/status` |
| [`trends.md`](trends.md) | `GET /api/trends` |
| [`figures.md`](figures.md) | `GET /api/figures` |
| [`health.md`](health.md) | `GET /api/health`、`GET /api/health/live`、`GET /api/health/ready` |

受保护的业务端点使用 `X-API-Key`；错误码、参数及可空字段在各文件中定义。变更接口时须同步修改对应文件与 OpenSpec Scenario，不在多个文档复制一整份接口正文。
