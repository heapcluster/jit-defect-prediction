# health

健康检查接口（模块 `health.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/health` | GET | 综合健康快照（组件状态、依赖连通性） |
| `/api/health/live` | GET | 存活探针（liveness） |
| `/api/health/ready` | GET | 就绪探针（readiness，含 DB/外部依赖） |

- **权限**：通常免鉴权（供编排/监控调用）。
- **用途**：K8s/监控探活、依赖就绪判断。

## 传输模型
### /api/health 响应
| 字段 | 含义 |
|---|---|
| `status` | ok / degraded / down |
| `components{}` | 各组件状态（db / git / model 等） |
| `checked_at` | 检查时间 |
### /api/health/live · /ready
| 字段 | 含义 |
|---|---|
| `status` | alive / ready（布尔语义） |
| `detail` | 简短说明 |
