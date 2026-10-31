# quality

质量看板与校准接口（模块 `quality.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/quality` | GET | 质量指标（按模型/AUC/PR 等） |
| `/api/quality/dataset` | GET | 导出人工标签样本（含 14 维特征），供离线再训练 |
| `/api/quality/calibrate` | POST | 按人工标签校准高风险阈值并落库（样本不足只报告不写） |

- **权限**：沿用后端统一鉴权。
- **关键参数**：`model_name` / 校准请求体（可选样本约束）。

## 传输模型
### /api/quality 响应
| 字段 | 含义 |
|---|---|
| `model_name` | 模型 |
| `auc` / `pr_auc` / `precision` / `recall` / `f1` | 性能指标 |
| `sample_size` | 评估样本数 |
### /api/quality/calibrate 响应
| 字段 | 含义 |
|---|---|
| `old_threshold` / `new_threshold` | 校准前后阈值 |
| `sample_size` | 用于校准的样本量 |
| `written` | 是否写入 runtime_setting |
