# health

**一句话**：健康检查接口——三个探针，供监控/排障判断「进程活着、DB 通、模型加载了」。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 运维 / 监控 | 探活、就绪判断、看行数快照 |
| K8s / 部署探针 | `/api/health/live`、`/api/health/ready` |
| 集成测试 | 三条探针的正常 / 鉴权用例 |
| 前端页面 | **不引用**：风险列表已移除状态卡，新页面不展示健康信息 |

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/health` | GET | 综合快照：DB 连通、已加载模型、两张表行数、最近同步时间 |
| `/api/health/live` | GET | 存活探针（liveness）**只证明进程活着，不碰 DB** |
| `/api/health/ready` | GET | 就绪探针（readiness）：DB 通 + 至少加载一个模型 |

- **权限**：**三条都需要 `X-API-Key`**（实测不带 token 返回 `401 / 40100`）。这是当前口径，别按「监控探针应免鉴权」去改代码。
- **降级语义**：DB 不可达时 `status` 变 `degraded`，HTTP 仍是 `200`（业务码 `code=0`）——探针不靠状态码表达健康，读 `data.status`。
- 失败细节只进服务端日志，响应不回显连接串、口令或堆栈。

## 响应 `data`

### `/api/health`
| 字段 | 含义 |
|---|---|
| `status` | `ok` / `degraded` |
| `db` | `up` / `down` |
| `models_loaded` / `model_names` | 已加载模型数与名单 |
| `commit_count` / `prediction_count` | 两张表行数 |
| `last_sync_at` | 最近一次同步开始时间；进程重启后为 `null` |
| `server_time` | 服务端当前时间（`Z` 结尾） |

### `/api/health/live`
| 字段 | 含义 |
|---|---|
| `status` | 恒 `ok` |
| `server_time` | 服务端当前时间 |

### `/api/health/ready`
| 字段 | 含义 |
|---|---|
| `status` | `ok` / `degraded` |
| `db` | `up` / `down` |
| `models_loaded` | 已加载模型数（为 0 即 `degraded`） |
| `server_time` | 服务端当前时间 |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40100 | 401 | 缺 / 错 token |

## 口径
- `labeled_count` 字段**已随 `commit_label` 表删除下线**；真标签改在 `commit_feature.is_bug_inducing`，不再单独计数。
- 三条探针均无业务参数，集成测试按「正常 / 缺 token / 非法 token / 篡改 token」四类场景覆盖即可。
