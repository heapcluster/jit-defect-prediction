# trends

趋势分析接口（模块 `trends.py`）。

## 处理功能
- **方法 / 路径**：`GET /api/trends`
- **用途**：按时间粒度聚合提交量与风险，供趋势看板画**两条 y 轴**（提交数 + 高风险数）。
- **权限**：沿用后端统一鉴权。

## 关键参数
| 参数 | 含义 |
|---|---|
| `granularity` | `week`（默认）/ `month` |
| `start_time` / `end_time` | commit 时间区间，两端闭区间 |
| `model_name` | 选中模型；省略时取运行时默认模型 |

## 传输模型
### 响应 `data`
| 字段 | 含义 |
|---|---|
| `granularity` | 回显聚合粒度 |
| `model_name` | 实际使用的模型 |
| `series[]` | 时间桶数组，**按 period 字典序即时间序** |
| `series[].period` | 时间桶标签：周 `2024-W31`（ISO 周），月 `2024-07` |
| `series[].commit_count` | 该桶提交数 → y 轴一 |
| `series[].high_risk_count` | 该桶 `risk_score >= 高阈值` 的提交数 → y 轴二 |
| `series[].avg_risk` | 该桶风险均值 |

**阈值口径**：`high_risk_count` 用运行时高风险阈值（`runtime_setting`）统计，改阈值后趋势随之变化。

## 口径说明
- 数组名是 `series`（不是 `points`），时间键是 `period`（不是 `bucket`）。
- **没有 `defect_count` 字段**：本接口统计的是「预测为高风险」的提交数，不是真缺陷数。要按 szz 真标签统计，走测试集评估明细。
- MySQL 路径把分桶/计数/均值全部下推 SQL（`build_aggregate_stmt`）；Python 侧分桶仅作单测方言回退。
