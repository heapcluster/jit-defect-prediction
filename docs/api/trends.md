# trends

趋势分析接口（模块 `trends.py`）。

## 处理功能
- **方法 / 路径**：`GET /api/trends`
- **用途**：按时间粒度聚合风险/缺陷趋势，供趋势看板展示。
- **权限**：沿用后端统一鉴权。
- **关键参数**：`granularity`（如 week / month）、`model_name`、`range`。

## 传输模型
### 响应（200 OK）
| 字段 | 含义 |
|---|---|
| `granularity` | 聚合粒度 |
| `points[]` | 时间点数组 |
| `points[].bucket` | 时间桶（如某周） |
| `points[].commit_count` | 该桶提交数 |
| `points[].defect_count` | 该桶预测为缺陷数 |
| `points[].avg_risk` | 该桶平均风险分 |
