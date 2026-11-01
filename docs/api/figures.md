# figures

模型性能图的托管方式：后端把模型线交付的图目录挂成静态资源，前端按线别拼路径取图。**没有索引接口，也没有元数据表。**

## 处理功能
- **方式**：`StaticFiles` 挂载 `GET /static/figures/{line}/{file}.png`
- **源目录**：`data_model/pipelines/{line}/reports/figs/`（模型线产出，后端只读挂载，不复制、不改名、不生成）
- **权限**：沿用后端统一鉴权

## 现有图清单（实测，非计划）
| 文件名 | 内容 | 覆盖线 |
|---|---|---|
| `roc_curves.png` | 该线各模型 ROC 曲线**同图对比** | expert / semantic / fused / e2e |
| `metric_bars.png` | 该线各模型指标柱状对比（effort-unaware 一类） | expert / semantic / fused |
| `effort_curves_loc.png` | **effort-aware**：按 LOC 检查预算的缺陷捕获曲线 | expert / semantic / fused / e2e |

`e2e` 只有 2 张（无 `metric_bars.png`）。

## 前端用法
- 选中模型后展示**它所在线**的图集。对比图把该线所有模型画在同一张上，选中项的区别体现在明细表与指标数值，MUST NOT 声称「该图为所选模型单独生成」。
- 课程《项目要求》要求 effort-unaware 与 effort-aware **两类**指标，各对应一张图（`metric_bars.png` / `effort_curves_loc.png`），eval 页 MUST 至少各展示一张。
- **取图方式**：`<img src>` 带不了 `X-API-Key`，所以前端用 `fetch`（带鉴权头）取二进制再转 `ObjectURL` 渲染；不许为了让 `<img>` 能显示就把静态路径开成免鉴权。

## 错误响应
| 状态码 | 含义 |
|---|---|
| 401 | 未鉴权 |
| 404 | 线别目录或图文件不存在 |

## 明确不做
- **不建 `model_figure` 表**：图就是目录里的文件，路径由「线别 + 固定文件名」唯一确定；多一张表就多一个会和磁盘对不上的真相源。
- **不提供 `GET /api/figures` 索引端点**。
- **不承诺逐模型图集**（roc / pr / 混淆矩阵 / 校准曲线 / 特征重要性 × 25 模型）。真要做得先单开 change，同时决定谁来生成 125 张图、放哪个目录、表怎么同步。
