# commits

提交相关查询接口（模块 `commits.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/commits` | GET | 提交列表，分页/筛选（按模型、风险、时间） |
| `/api/commits/coverage` | GET | 各模型已预测的提交时间覆盖区间 `[min, max]` |
| `/api/commits/{commit_hash}` | GET | 单提交详情（特征 + 各模型 risk_score） |

- **权限**：沿用后端统一鉴权。
- **关键参数**：`page` / `size` / `model_name` / `risk_min` / `risk_max` / `commit_hash`。

## 传输模型
### 列表响应（/api/commits）
| 字段 | 含义 |
|---|---|
| `total` / `page` / `size` | 分页信息 |
| `items[]` | 提交数组 |
| `items[].commit_hash` / `author` / `committed_at` / `message` | 提交信息 |
| `items[].risk_score` | 指定模型风险分 |
| `items[].is_defect` | 判定 |
### 详情响应（/api/commits/{hash}）
| 字段 | 含义 |
|---|---|
| `commit` | 提交元信息 |
| `features{ns..sexp}` | Kamei 14 维 |
| `predictions[]` | 各模型 `model_name` + `risk_score` |
