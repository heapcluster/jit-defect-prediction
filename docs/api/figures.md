# figures

模型性能图分两类：**每线对比图**（整条线所有模型画在一张上）与**逐模型图集**（每个模型一套 roc / pr / 混淆矩阵 / 校准 / effort）。后端把模型线交付的图目录挂成静态资源，并提供逐模型图索引。

## 处理功能
- **方式一（索引）**：`GET /api/figures?model_name=`，返回该模型的逐模型图清单
- **方式二（静态）**：
  - 每线对比图：`StaticFiles` 挂 `data_model/pipelines/{line}/reports/figs/*.png`
  - 逐模型图集：`StaticFiles` 挂 `backend/static/figures/{line}/{model}/{figure_type}.png`
- **权限**：沿用后端统一鉴权
- **关联数据**：`model_figure`（图元数据）、`model.line`（路径分组）

## 每线对比图（实测）
| 文件名 | 内容 | 覆盖线 |
|---|---|---|
| `roc_curves.png` | 该线各模型 ROC 曲线**同图对比** | expert / semantic / fused / e2e |
| `metric_bars.png` | 该线各模型指标柱状对比（effort-unaware 一类） | expert / semantic / fused |
| `effort_curves_loc.png` | **effort-aware**：按 LOC 检查预算的缺陷捕获曲线 | expert / semantic / fused / e2e |

`e2e` 只有 2 张（无 `metric_bars.png`）。

## 逐模型图集（`model_figure`）
`figure_type` 取值：`roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance`。
- `effort`：effort-aware 曲线（累计 LOC 预算 vs 召回率，含随机基线与 oracle）；
- `feat_importance`：仅 `expert` 线产出（Kamei 14 维可读）；semantic / fused 的 768 维、e2e 文本不产出该图；
- `file_path` 形如 `/static/figures/{line}/{model}/{figure_type}.png`，由 `data_model/evaluation/` 生成并拷贝到后端静态目录。

### 方式一响应（200 OK）
| 字段 | 含义 |
|---|---|
| `model_name` | 模型名 |
| `figures[]` | 图数组 |
| `figures[].figure_type` | `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| `figures[].title` | 图标题 |
| `figures[].file_path` | 图 URL（指向静态目录） |

### 方式一响应示例
```json
{
  "model_name": "lr_fused_v1",
  "figures": [
    {"figure_type": "roc", "title": "ROC curve", "file_path": "/static/figures/fused/lr_fused_v1/roc.png"},
    {"figure_type": "effort", "title": "Effort-aware curve (LOC proxy)", "file_path": "/static/figures/fused/lr_fused_v1/effort.png"}
  ]
}
```

### 方式二
直接返回图片二进制（`Content-Type: image/png`）。

## 前端用法
- 每线对比图：把该线所有模型画在同一张上，选中项的区别体现在明细表与指标数值。
- 逐模型图集：切换 `model_name` 时刷新，展示该模型自己的 roc / pr / confusion / calibration / effort。
- 课程《项目要求》要求 effort-unaware 与 effort-aware **两类**指标，各对应至少一张图。
- **取图方式**：`<img src>` 带不了 `X-API-Key`，前端用 `fetch`（带鉴权头）取二进制再转 `ObjectURL` 渲染；不许为了让 `<img>` 能显示就把静态路径开成免鉴权。

## 错误响应
| 状态码 | 含义 |
|---|---|
| 400 | 缺少 `model_name` |
| 401 | 未鉴权 |
| 404 | 模型无图、线别目录或图文件不存在 |
