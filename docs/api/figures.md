# figures

**一句话**：模型性能图与指标接口——给前端模型性能看板的「查看」抽屉供数据：逐模型图集 + 指标数值。

## 被谁调用
| 调用方 | 场景 |
|---|---|
| 前端「模型性能看板」页「查看」抽屉 | 选定模型后渲染该模型的性能评估图集；指标数值可一并展示 |

## 处理功能
- **方式一（索引）**：`GET /api/figures?model_name=`，返回该模型的**指标数值 + 逐模型图清单**（后端路由已实现；指标 CSV 缺失时 `metrics=null`）
- **方式二（静态）**：逐模型图集：`StaticFiles` 挂 `backend/static/figures/{line}/{model}/{figure_type}.png`（**已实现**；当前仓库按文件清单计 133 张 PNG，变更后须重新核对）
- **权限**：沿用后端统一鉴权
- **关联数据**：`model_figure`（图元数据）、`model.line`（路径分组）、`data_model/evaluation/out/model_metrics.csv`（指标数值，由 `cd data_model && python -m evaluation.run_all` 生成；后端只读，不跑脚本）

## 参数（方式一）
| 参数 | 必填 | 含义 |
|---|---|---|
| `model_name` | 是 | 目标模型 |

## 响应 `data`（方式一，200 OK）
| 字段 | 含义 |
|---|---|
| `model_name` | 模型名 |
| `line` | 模型所属线 |
| `metrics` | **指标数值**（见下；来自 `model_metrics.csv`），无指标行时 `null` |
| `figures[]` | 图数组 |
| `figures[].figure_type` | `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| `figures[].title` | 图标题 |
| `figures[].file_path` | 图 URL（指向静态目录） |

### `metrics` 字段
| 字段 | 含义 |
|---|---|
| `auc` / `ap` / `f1` / `precision` / `recall` / `accuracy` | 该模型在测试集上的性能指标 |
| `n` | 测试集样本数 |
| `pos_rate` | 正样本占比 |

指标与图**同一请求返回**，前端「指标数值 + 图集」一次拿全。

## 错误
| 业务码 | HTTP | 含义 |
|---|---|---|
| 40001 | 400 | 缺少 `model_name` |
| 40100 | 401 | 缺 / 错 token |
| 40400 | 404 | 模型无图、架构目录或图文件不存在 |

## 口径
- **模型标识统一用 `model_name`**：请求/响应都用 `model_name`，库表 `model_figure` 外键即 `model_name`，无中间转换。
- **只收 `model_name`，不接收架构 / 时间**：`model_name` 唯一决定架构；图与指标是离线在测试集上生成的整模型产物，不随时间范围变化。按架构的对比图是静态文件（`data_model/pipelines/{line}/reports/figs/`），不在本接口。
- **逐模型图集（`model_figure`，实测已交付）**：`figure_type` 取值 `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance`；
  - `effort`：effort-aware 曲线（累计 LOC 预算 vs 召回率，含随机基线与 oracle）；
  - `feat_importance`：**仅 `expert` 线产出**（Kamei 14 维可读）；semantic / fused 的 768 维、e2e 文本不产出该图——e2e 只有 5 张，无 `feat_importance`。
  - `file_path` 形如 `/static/figures/{line}/{model}/{figure_type}.png`，由 `data_model/evaluation/` 生成并拷贝到 `backend/static/figures/`。
- 课程《项目要求》要求 effort-unaware 与 effort-aware **两类**指标，各对应至少一张图（`effort.png` 即 effort-aware 那张）。
- **取图方式**：`<img src>` 带不了 `X-API-Key`，前端用 `fetch`（带鉴权头）取二进制再转 `ObjectURL` 渲染；不许为了让 `<img>` 能显示就把静态路径开成免鉴权。
