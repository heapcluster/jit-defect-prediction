# trends

**一句话**：趋势分析接口——按时间粒度聚合提交量与高风险数，供趋势看板画两张图。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「趋势看板」页 | 选架构 → 选模型（两级级联）+ 独立时间范围，看提交数与高风险数走势 |

## 处理功能
- **方法 / 路径**：`GET /api/trends`
- **权限**：沿用后端统一鉴权。

## 参数
| 参数 | 必填 | 含义 |
|---|---|---|
| `granularity` | 否 | `week`（默认）/ `month` |
| `start_time` / `end_time` | 否 | commit 时间区间，两端闭区间 |
| `model_name` | 否 | 选中模型；省略时取默认模型 = 已加载模型中 `version_key` 最大者 |

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `granularity` | 回显聚合粒度 |
| `model_name` | 实际使用的模型 |
| `series[]` | 时间桶数组，按 `period` 字典序即时间序 |
| `series[].period` | 时间桶标签：周 `2024-W31`（ISO 周），月 `2024-07` |
| `series[].commit_count` | 该桶提交数 → **图一（提交数趋势）** |
| `series[].high_risk_count` | 该桶 `risk_score >= HIGH_RISK_THRESHOLD` 的提交数 → **图二（高风险数趋势）** |
| `series[].avg_risk` | 该桶所有提交 `risk_score` 的均值（0~1）→ **汇总卡「加权平均风险」** |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法 |
| 40100 | 401 | 缺 / 错 token |

## 口径
- **两张图**：图一取 `commit_count`，图二取 `high_risk_count`；`avg_risk` 只用于汇总卡，不再单列折线。
- `high_risk_count` 按 `.env` 写死的 `HIGH_RISK_THRESHOLD` 统计；`avg_risk` 是桶内预测提交 `risk_score` 的算术均值。
- 数组名是 `series`（不是 `points`），时间键是 `period`（不是 `bucket`）。
- **模型标识统一用 `model_name`**：参数与响应都用 `model_name`，与库表外键同名，无中间转换。
- **模型名已隐含架构**：`/api/trends` 不接收 `line`；架构只用于 `GET /api/models` 的级联选择。
- **页面筛选**：架构 → 模型两级级联 + 独立时间范围；前两级来自 `GET /api/models`，时间范围可单独选择，走 `start_time` / `end_time`。
- 要按 SZZ 真标签统计缺陷，走模型性能看板的 `is_defect` 列，不在本接口聚合。
- MySQL 路径把分桶/计数/均值全部下推 SQL（`build_aggregate_stmt`）；Python 侧分桶仅作单测方言回退。
