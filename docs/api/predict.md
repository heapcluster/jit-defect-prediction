# predict

单条提交现算预测接口（模块 `predict.py`）。

## 处理功能
- **方法 / 路径**：`POST /api/predict`
- **用途**：对单条提交**现算特征并预测**（不依赖预存 prediction），用于即时风险评估。
- **权限**：沿用后端统一鉴权。
- **请求体**：提交标识或 diff 内容（repo + commit_hash / diff 文本）。

## 传输模型
### 请求（body）
| 字段 | 含义 |
|---|---|
| `repo_name` | 仓库名 |
| `commit_hash` | 目标提交（或提供 diff 文本） |
| `model_name` | 指定模型（可选，默认冠军模型） |

### 响应（200 OK）
| 字段 | 含义 |
|---|---|
| `commit_hash` | 提交标识 |
| `model_name` | 使用的模型 |
| `risk_score` | 风险概率 `[0,1]` |
| `predicted` | 二值判定 |
| `features{ns..sexp}` | 现算的 14 维特征 |

### 错误响应
| 状态码 | 含义 |
|---|---|
| 400 | 请求体非法 |
| 404 | 提交/模型不存在 |
