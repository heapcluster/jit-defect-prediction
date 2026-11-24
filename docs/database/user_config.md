# user_config

`实现状态：部分　期次：一期`

W1 已实现配置服务、四类读写端点、原子校验与重启恢复；业务接入已覆盖风险阈值与指标配置，其余模块随对应波次消费配置。

**一句话**：用户级键值配置表，是阈值、默认数据集、默认 XAI 技术、指标勾选与页面偏好的**唯一权威来源**；「异常关闭重开后自动恢复用户设置」的落点。模型不设默认值，由每次运行显式选择。

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| user_id | VARCHAR(36) | NOT NULL | 联合主键 + 外键 → `user.user_id` | 配置归属；`global` 为全局默认行 |
| config_key | VARCHAR(64) | NOT NULL | 联合主键 | 配置键，取值见下表 |
| value_json | TEXT | NOT NULL | — | 值（JSON 编码，标量也编码为 JSON） |
| value_type | VARCHAR(16) | NOT NULL | — | `float` / `int` / `string` / `bool` / `list` / `object` |
| updated_at | DATETIME | NOT NULL | — | 最近写入时间 |

## 主键与约束理由

- 联合主键 `(user_id, config_key)`：一个用户一个键一行，单键更新幂等。
- 外键指向 `user`，配置必须有归属；无用户上下文时归 `global` 行。
- `updated_at` 为配置语义必需（恢复与审计），随每次写入更新。

## 配置键清单（一期）

| 键 | 类型 | 默认值 | 校验 |
|---|---|---|---|
| `decision_threshold` | float | 0.5 | 开区间 (0,1) |
| `risk_high_threshold` | float | 0.5 | (0,1)，且 > `risk_mid_threshold` |
| `risk_mid_threshold` | float | 0.2 | (0,1) |
| `default_dataset` | string | 空（回退默认数据集） | 须为已登记 `dataset_id` |
| `default_xai` | string | `shap` | 须为解释器注册表已注册技术 |
| `metrics_selected` | list | 六项基础指标（AUC / AP / F1 / Precision / Recall / Accuracy） | 元素须属可选指标清单（含 Effort-aware 指标） |
| `primary_metric` | string | `auc` | 须属 `metrics_selected` |
| `effort_enabled` | bool | true | — |
| `page_prefs` | object | `{}` | 白名单键（页大小、抽屉展开态等） |

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 配置 API（读取 / 单键更新 / 批量更新 / 删除） | 用户调整阈值 / 指标 / XAI |
| 读取 | 预测（判定阈值）、评估（阈值 + 指标勾选）、解释（默认技术）、收集（默认数据集） | 全系统配置单源 |
| 展示 | 设置页 / 设置抽屉、各页面偏好 | 配置查看与修改入口 |

## 口径

- **单源规则**：读取顺序 = 当前用户行 → `global` 行 → 代码内出厂默认常量，三层只在配置服务内实现；业务代码与前端 MUST NOT 自带第二份默认值，前端改读配置接口。`.env` 与 `data_model/pipelines/*/config.py` 仅作出厂默认值的来源。
- 未知键、类型不符、越界值、跨键约束违反（如 mid ≥ high）返回明确错误码（40001），MUST NOT 静默截断或忽略。
- 写入立即生效（配置服务不缓存过期值）；后端 / 容器 / 进程异常关闭后重启，接口可恢复原值。
- 恢复默认值 = 删除用户行对应键，回退 `global` / 出厂默认。
- 敏感信息（API Key、口令等）MUST NOT 作为配置键入库。

## 验收

- 改 `decision_threshold=0.3` → 评估指标与风险判定同步变化；重启后仍为 0.3。
- 非法值（1.5、mid=0.6/high=0.5、未知键）→ 40001 且原值不变。
- 删除用户键 → 回退 `global`；`global` 缺省时回退出厂默认。
- 配置接口与设置界面读写一致；接口不返回任何凭证。