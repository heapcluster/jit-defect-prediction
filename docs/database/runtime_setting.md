# runtime_setting（复用表）

运行时配置表，存「运营参数」，改完即时生效，无需重启。

| 字段 | 含义 |
|---|---|
| `key` | 配置键（PK） |
| `value` | 配置值（字符串存储） |
| `updated_at` | 更新时间 |

## 键清单
| key | 含义 | 谁写 |
|---|---|---|
| `high_risk_threshold` | 高风险阈值，风险分级与 `high_risk_count` 统计的界 | `PUT /api/config` |
| `mid_risk_threshold` | 中风险阈值 | `PUT /api/config` |
| `champion_model` | 冠军模型名；未配置时回落「已加载且预测非空」的最新模型 | `PUT /api/config` |
| `test_split_at` | **测试集时间边界**（ISO 时间戳）：`committed_at >= 该值` 即测试集 | 模型线交付时写入 |

**角色**：保存测试集评估校准出的工作点阈值、冠军模型与测试集边界。阈值影响风险分级与列表里的 `min_risk` 筛选口径；`test_split_at` 决定 `scope=test` 的范围（`.env` 改一次要重启，故这几类都入库）。
