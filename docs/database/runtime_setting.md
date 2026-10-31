# runtime_setting（复用表）

运行时配置表，存「运营参数」（如风险阈值），改完即时生效，无需重启。

| 字段 | 含义 |
|---|---|
| `key` | 配置键（PK），如 `high_risk_threshold` / `mid_risk_threshold` / `champion_model` |
| `value` | 配置值（字符串存储） |
| `updated_at` | 更新时间 |

**角色**：质量看板按人工标签校准后热更新阈值；阈值变更即时影响预测分级与 PR 门禁判定（`.env` 改一次要重启，故入库）。
