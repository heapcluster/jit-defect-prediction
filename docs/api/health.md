# 健康检查 API（health）

一句话：提供完整运行状态与两个探针（liveness / readiness），供自检、容器编排与前端状态展示使用。

实现状态：已实现　期次：一期

## 1. 职责与不负责范围

- 负责报告进程存活、数据库连通性、已加载模型数与核心表计数。
- 不负责触发同步、训练或任何计算；健康检查是只读操作。
- 探测失败是**状态**（`degraded`），不是异常；三个端点均不返回 50000。

## 2. 端点契约

三个端点都需要 `X-API-Key`，响应包络统一为 `{"code":0,"message":"ok","data":{...}}`。

### GET /api/health

完整运行状态（人看的），含计数与最近同步时间。

| 字段 | 类型 | 含义 |
|---|---|---|
| `status` | string | `ok`：DB 通且有已加载模型；否则 `degraded` |
| `db` | string | `up` / `down` |
| `models_loaded` | int | 当前已加载模型数 |
| `model_names` | string[] | 已加载模型名 |
| `catalog_count` | int | `model` 表登记总数 |
| `commit_count` | int | `commit` 表行数 |
| `prediction_count` | int | `prediction` 表行数 |
| `last_sync_at` | string\|null | 最近一次同步开始时间（UTC，`Z` 结尾） |
| `server_time` | string | 服务端当前时间（UTC，`Z` 结尾） |

DB 不可达时 `db=down`、计数为 0，不返回连接串、口令或堆栈。

### GET /api/health/live

liveness：只证明进程活着，**不碰 DB**（DB 故障不应触发进程重启）。

```json
{"status": "ok", "server_time": "2026-11-27T00:00:00Z"}
```

### GET /api/health/ready

readiness：DB 通且至少加载一个模型才就绪（容器编排据此摘流量）。

```json
{"status": "ok", "db": "up", "models_loaded": 16, "server_time": "2026-11-27T00:00:00Z"}
```

任一条件不满足时 `status=degraded`。

## 3. 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40100 | 401 | 缺少或错误的 `X-API-Key` |

探针本身不产生业务错误码；DB 或模型不可用以 `degraded` 表达。

## 4. 验收

- 带正确 `X-API-Key` 请求三个端点均返回 `code=0`。
- 断开数据库后 `/api/health` 与 `/api/health/ready` 返回 `degraded`/`db=down`，`/api/health/live` 仍为 `ok`。
- 响应中不出现连接串、口令或堆栈信息。
