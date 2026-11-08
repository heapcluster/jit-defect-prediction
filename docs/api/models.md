# models

**一句话**：模型清单接口——前端「架构 → 模型」级联选择器的数据源，替代前端写死清单。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端风险列表页 | 渲染架构 → 模型两级下拉 |
| 前端提交详情页 | 「重新预测」的架构 → 模型两级下拉 |
| 前端趋势看板 | 渲染架构 → 模型两级下拉 |
| 前端模型性能看板 | 渲染架构 → 模型两级下拉 |

## 处理功能
- **方法 / 路径**：`GET /api/models`（后端路由已实现；实际数据仍取决于已注册模型）
- **权限**：沿用后端统一鉴权。
- **数据来源**：`model` 表（`model_name` / `line`），按 `line` 分组，只读。

## 参数
| 参数 | 必填 | 含义 |
|---|---|---|
| `line` | 否 | 架构过滤：`expert` / `semantic` / `fused` / `e2e`；省略返回全部架构 |

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `lines[]` | 架构数组，固定顺序 `expert → semantic → fused → e2e` |
| `lines[].line` | 架构标识（小写，与库表 `model.line` 同值） |
| `lines[].label` | 中文显示名：`专家特征` / `语义` / `融合` / `端到端` |
| `lines[].models[]` | 该架构下的模型名数组，元素为 `model_name` 字符串 |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | `line` 取值非法 |
| 40100 | 401 | 缺 / 错 token |

## 口径
- **对外模型标识统一用 `model_name`**：数组元素就是 `model_name`；不返回 `algo`、`version_key`、训练时间等内部字段。
- **`label` 是后端常量映射，不落库**：`expert→专家特征`、`semantic→语义`、`fused→融合`、`e2e→端到端`。前端可本地兜底，但后端应返回，避免两边各维护一份。
- **架构 = `line`**：前后端统一用「架构（`line`）」描述这一级；取值一律小写 `expert` / `semantic` / `fused` / `e2e`，不写成 `SEM` / `EXPERT` 等大写形式。
- **查询时只有 `model_name` 进业务接口**：风险列表、趋势看板、模型性能看板查询传 `model_name`；提交详情用默认模型，「重新预测」调 `POST /api/predict` 传 `model_name`。`line` 只用于本接口的下拉联动；`/api/commits` 与 `/api/trends` 不接收 `line`。
- **本接口只提供架构 → 模型两级级联**；时间范围是独立筛选，可单独选择、不依赖模型，直接作为 `start_time` / `end_time` 传给 `/api/commits` / `/api/trends` / `/api/sync`。本接口不处理时间。
- 某架构尚未交付模型时返回空 `models[]`，前端该架构置灰或隐藏，不得报错。
- 只读 `model` 表，不触发任何计算；与 `api/figures.md`、`api/trends.md`、`api/commits.md` 共用同一套 `model` 数据。
