# models

**一句话**：模型清单接口——前端「选线 → 选模型」两级选择器的数据源，替代前端写死清单。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端风险列表页、趋势看板、测试集评估页 | 渲染两级选择器：先选 line，再选该线下 model |

## 处理功能
- **方法 / 路径**：`GET /api/models`（**待实现**）
- **权限**：沿用后端统一鉴权。
- **数据来源**：`model` 表（`model_name` / `line` / `algo`），只读。

## 参数
| 参数 | 必填 | 含义 |
|---|---|---|
| `line` | 否 | `expert` / `semantic` / `fused` / `e2e`；省略返回全部四线 |

## 响应 `data`
| 字段 | 含义 |
|---|---|
| `lines[]` | 线数组，固定顺序 `expert → semantic → fused → e2e` |
| `lines[].line` | 线别 |
| `lines[].models[]` | 该线下模型数组 |
| `lines[].models[].model_name` | 模型名（对外唯一标识），如 `lr_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| `lines[].models[].algo` | 算法名 |

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40100 | 401 | 缺 / 错 token |

## 口径
- 前端 MUST 用本接口渲染两级选择器，MUST NOT 写死模型清单（交付 25 模型后写死会静默缺项）。
- **模型标识统一用 `model_name`**：库表 `model` 主键就是 `model_name`（见 `database/model.md`），请求/响应/前端/交付清单一律用它，无中间转换。
- 某线尚未交付模型时返回空 `models[]`，前端该线置灰或隐藏，不得报错。
- 只读 `model` 表，不触发任何计算；与 `api/test_detail.md`、`api/figures.md` 共用同一套 `model` 表数据。
