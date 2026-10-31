# prs

Pull Request 风险评估接口（模块 `prs.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/sync-prs` | POST | 拉取源仓库最新 open PR 并逐条现算预测入库 |
| `/api/prs` | GET | PR 列表（含整体风险） |
| `/api/prs/{number}` | GET | 单 PR 元信息 + 各提交风险分 |
| `/api/prs/{number}/gate` | GET | CI 风险门禁：以运行时高阈值为界给出放行/拦截 |

- **权限**：沿用后端统一鉴权。
- **关键参数**：`limit` / `model_name` / `number`。

## 传输模型
### /api/prs 响应
| 字段 | 含义 |
|---|---|
| `items[]` | PR 数组 |
| `items[].number` / `title` / `author` | PR 信息 |
| `items[].risk_score` | PR 整体风险（各提交聚合） |
| `items[].gate` | 门禁结论（pass / block） |
### /api/prs/{number}/gate 响应
| 字段 | 含义 |
|---|---|
| `number` | PR 编号 |
| `gate` | pass / block |
| `threshold` | 判定的高风险阈值（来自 runtime_setting） |
| `max_risk` | 该 PR 内最高提交风险分 |
