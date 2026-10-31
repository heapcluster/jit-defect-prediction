# webhook

GitHub Webhook 接收接口（模块 `webhook.py`）。

## 处理功能
- **方法 / 路径**：`POST /api/webhook/github`
- **用途**：接收 GitHub push / PR 事件，触发增量同步与预测（事件驱动更新）。
- **权限**：校验 GitHub 签名（secret），非统一会话鉴权。
- **关键参数**：请求头签名（`X-Hub-Signature-256`）、事件体。

## 传输模型
### 响应
| 字段 | 含义 |
|---|---|
| `accepted` | 是否受理 |
| `event` | 事件类型 |
| `triggered` | 触发的后续动作（如 sync） |

**说明**：签名校验失败返回 4xx；受理即返回 200 并由后台异步处理。
