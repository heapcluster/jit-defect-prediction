# 数据同步

纵向功能点：从 Git 源仓库拉取提交/PR 并现算全模型预测入库。跨后端、数据库、模型线。

## 各层职责
| 层 | 职责 |
|---|---|
| 模型线 | 提供预测能力 |
| 后端 | `POST /api/sync` / `catchup` 拉取预测；`GET /api/sync/status` 状态；`GET /api/sync/stream` SSE 进度；`POST /api/webhook/github` 事件驱动触发 |
| 数据库 | `commit` / `commit_feature` / `prediction` 写入 |

## 关键字段
| 字段 | 作用 |
|---|---|
| `commit.commit_hash` | 拉取对象 |
| `prediction.*` | 全模型预测结果 |

## 验收
- 增量/补齐同步幂等；状态可查、进度可订阅。
