# trends

**一句话**：趋势分析接口——按时间粒度聚合提交量与风险度，供趋势看板画两条折线。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「趋势看板」页 | 选线 → 选模型 → 选时间范围，看提交量与风险度走势 |

## 处理功能
- **方法 / 路径**：`GET /api/trends`
- **权限**：沿用后端统一鉴权。

## 参数
| 参数 | 必填 | 含义 |
|---|---|---|
| `granularity` | 否 | `week`（默认）/ `month` |
| `start_time` / `end_time` | 否 | commit 时间区间，两端闭区间 |
| `line` | 否 | **待实现**：线别筛选，与 `model_name` 二选一或叠加 |
| `model_name` | 否 | 选中模型；省略时取默认模型 = 已加载模型中 `version_key` 最大者 |

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `granularity` | 回显聚合粒度 |
| `model_name` | 实际使用的模型 |
| `series[]` | 时间桶数组，按 `period` 字典序即时间序 |
| `series[].period` | 时间桶标签：周 `2024-W31`（ISO 周），月 `2024-07` |
| `series[].commit_count` | 该桶提交数 → **折线一（提交量）** |
| `series[].avg_risk` | 该桶**风险度**（0~1，所有提交 `risk_score` 均值）→ **折线二（风险度）** |
| `series[].high_risk_count` | 该桶 `risk_score >= 高阈值` 的提交数（辅助指标，可选展示） |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 参数非法 |
| 40100 | 401 | 缺 / 错 token |

## 口径
- **模型标识统一用 `model_name`**：参数与响应都用 `model_name`，与库表外键同名，无中间转换。
- 数组名是 `series`（不是 `points`），时间键是 `period`（不是 `bucket`）。
- **两条折线**：`commit_count`（提交量）与 `avg_risk`（风险度）；`avg_risk` 是桶内所有预测提交 `risk_score` 的算术均值，0~1，前端按百分比显示。
- `high_risk_count` 是辅助指标（高风险提交数），不是第三条折线；它按 `.env` 写死阈值（`HIGH_RISK_THRESHOLD`）统计。
- 要按 szz 真标签统计缺陷，走测试集评估明细（`api/test_detail.md`）。
- MySQL 路径把分桶/计数/均值全部下推 SQL（`build_aggregate_stmt`）；Python 侧分桶仅作单测方言回退。
