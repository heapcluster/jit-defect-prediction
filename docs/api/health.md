# health

健康检查接口（模块 `health.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/health` | GET | 综合快照：DB 连通、已加载模型、三张表的行数、最近一次同步时间 |
| `/api/health/live` | GET | 存活探针（liveness）**只证明进程活着，不碰 DB** |
| `/api/health/ready` | GET | 就绪探针（readiness）：DB 通 + 至少加载一个模型 |

- **权限**：**三条都需要 `X-API-Key`**（实测不带 token 返回 `401 / 40100`）。外部编排系统接不了免鉴权探针，这是当前口径，别按「监控探针应免鉴权」去改代码。
- **降级语义**：DB 不可达时 `status` 变 `degraded`，HTTP 仍是 `200`（业务码 `code=0`）——探针不靠状态码表达健康，读 `data.status`。
- 失败细节只进服务端日志，响应不回显连接串、口令或堆栈。

## 传输模型
### `/api/health` 响应 `data`
| 字段 | 含义 |
|---|---|
| `status` | `ok` / `degraded` |
| `db` | `up` / `down` |
| `models_loaded` / `model_names` | 已加载模型数与名单 |
| `commit_count` / `prediction_count` / `labeled_count` | 三张表行数 |
| `last_sync_at` | 最近一次同步开始时间；进程重启后为 `null` |
| `server_time` | 服务端当前时间（`Z` 结尾） |

### `/api/health/live` 响应 `data`
| 字段 | 含义 |
|---|---|
| `status` | 恒 `ok` |
| `server_time` | 服务端当前时间 |

### `/api/health/ready` 响应 `data`
| 字段 | 含义 |
|---|---|
| `status` | `ok` / `degraded` |
| `db` | `up` / `down` |
| `models_loaded` | 已加载模型数（为 0 即 `degraded`） |
| `server_time` | 服务端当前时间 |

## 口径说明
- `labeled_count` 统计的是 `commit_label` 全表行数（当前全是 szz），**与已下线的「人工确认」无关**；不要把它读成人工标注量，也不要为它再加人工口径。
- 三条探针均无业务参数，集成测试按「正常 / 缺 token / 非法 token / 篡改 token」四类场景覆盖即可。
