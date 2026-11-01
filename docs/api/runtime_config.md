# runtime-config

运行时配置读写接口（模块 `runtime_config.py`）。

## 处理功能
| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/config` | GET | 读取当前配置快照（阈值、冠军模型等） |
| `/api/config` | PUT | 更新风险等级阈值与冠军模型 |

- **权限**：沿用后端统一鉴权（写操作通常限管理员）。
- **约束**：`0 <= mid <= high <= 1`，非法返回 `40001`。
- **调用方**：测试集评估看板（定工作点）与运维。**`test_split_at` 不在本接口请求体内**——它由模型线交付流程写入 `runtime_setting`，别在这里顺手加字段。
- **PUT 是全量提交**：两个阈值都必须在请求体里给，缺一个就 `400`（不是补丁语义）。

## 传输模型
### GET 响应
| 字段 | 含义 |
|---|---|
| `high_risk_threshold` | 高风险阈值 |
| `mid_risk_threshold` | 中风险阈值 |
| `champion_model` | 冠军模型名 |
### PUT 请求体
| 字段 | 必填 | 含义 |
|---|---|---|
| `high_risk_threshold` | 是 | 新高阈值 |
| `mid_risk_threshold` | 是 | 中新阈值 |
| `champion_model` | 否 | 省略或 `null` = 不改；传**空字符串** = 清空，回落到「已加载且预测非空的最新模型」兜底口径 |
