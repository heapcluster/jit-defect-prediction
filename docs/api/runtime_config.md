# runtime-config

运行时配置读写接口（模块 `runtime_config.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/config` | GET | 读取当前配置快照（阈值、冠军模型等） |
| `/api/config` | PUT | 更新风险等级阈值与冠军模型 |

- **权限**：沿用后端统一鉴权（写操作通常限管理员）。
- **约束**：`0 <= mid <= high <= 1`，非法返回 `40001`。

## 传输模型
### GET 响应
| 字段 | 含义 |
|---|---|
| `high_risk_threshold` | 高风险阈值 |
| `mid_risk_threshold` | 中风险阈值 |
| `champion_model` | 冠军模型名 |
### PUT 请求体
| 字段 | 含义 |
|---|---|
| `high_risk_threshold` | 新高阈值 |
| `mid_risk_threshold` | 中新阈值 |
| `champion_model` | 新冠军模型 |
