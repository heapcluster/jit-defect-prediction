# sync

数据同步接口（模块 `sync.py`）：拉取 Git 源仓库提交并现算全模型预测入库。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/sync` | POST | 拉取最新提交并逐条现算全模型预测入库（幂等） |
| `/api/sync/catchup` | POST | 补齐到最新：DB 缺、git 有的提交全部预测入库 |
| `/api/sync/status` | GET | 同步状态快照（running/mode/scope/total/done/...） |
| `/api/sync/stream` | GET | SSE 实时推送同步进度，替代轮询 |

- **权限**：沿用后端统一鉴权（通常为内部/运维调用）。
- **关键参数**：`limit`（单次批大小）。

## 传输模型
### /api/sync/status 响应
| 字段 | 含义 |
|---|---|
| `running` | 是否同步中 |
| `mode` | 同步模式 |
| `scope` | 范围 |
| `total` / `done` | 总量 / 已完成 |
| `current_hash` | 当前处理提交 |
| `last_error` | 最近错误（如有） |
### /api/sync/stream 响应
`text/event-stream`，逐行推送进度事件（百分比 / 当前 hash / 错误）。
