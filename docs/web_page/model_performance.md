# 模型性能看板（ModelPerformance）

## 页面与路由
- 页面名：模型性能看板
- 路由：`/model-performance`（新增）
- 入口：顶部导航栏「模型性能」（新增菜单项）

## 功能概述
集中展示各机器学习模型的综合性能：顶部通过级联下拉选定模型后点「查看」，打开**模型图片展示页**（多图导航）；下方表格按提交逐条展示 14 维特征、SZZ 自动缺陷判断、所选模型的缺陷引入概率，支持联动查询与可视化。

## 布局（从上到下）

```
┌────────────────────────────────────────────────────────────────────┐
│ 模型性能看板                                                        │
├────────────────────────────────────────────────────────────────────┤
│ 模型： 架构[▾] 模型[▾]  [查看]                                      │
├────────────────────────────────────────────────────────────────────┤
│ 搜索[____]  时间范围[____ 至 ____]  [查询] [重置]                    │
├────────────────────────────────────────────────────────────────────┤
│ 提交      作者   时间      提交信息    14维特征  SZZ判断  缺陷引入概率│
│ a1b2c3d4  dev1  2024-03-01 fix:null   [预览]   是       83.0%       │
│ …                                                                   │
├────────────────────────────────────────────────────────────────────┤
│                                  ‹ 1 2 3 ›       共 1234 条         │
└────────────────────────────────────────────────────────────────────┘
```

分块说明：

1. **模型选择区**（顶部）：架构下拉 → 模型下拉（级联），右侧「查看」按钮。
2. **查询栏**：搜索、时间范围、查询、重置（仿风险列表样式）。
3. **数据表格**（多维指标表）：列定义见下。
4. **分页器**：默认 20 / 页，上限 100。

## 交互
- **架构 → 模型级联**：选「架构」后「模型」联动展示该架构下的模型；切换架构清空已选模型；两级都不选 = 后端默认模型。
- **「查看」→ 模型图片展示页**：点击后打开该模型的**多图导航展示页**（全屏弹层或独立路由），见下节。
- **查询 / 重置**：按 搜索 / 时间范围 过滤表格；点「查询」或搜索框回车触发；重置清空筛选。
- **动态概率**：「缺陷引入概率」列随顶部所选模型变化。
- **14 维特征**：单元格悬浮预览 / 点击抽屉，按五维度分组展示 Kamei 14 维。

## 模型图片展示页（多图导航）

### 打开方式
- 选定模型后点「查看」→ 打开**全屏弹层（`el-dialog fullscreen`）或独立路由**（如 `/model-performance/images?model_name=lr_v1`）。

### 组件结构

```
┌─ 模型图片 · lr_v1 ─────────────────────────────────────────────┐
│ [ROC] [PR] [混淆矩阵] [校准] [Effort] [特征重要性]   ← 导航 Tabs │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│            （主展示区：当前选中图片的大图，可点击放大）           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

- **顶部导航栏（Tabs）**：菜单项由 `GET /api/figures?model_name=` 返回的 `figures[].title` **动态生成**；无图时显示空态。
- **主展示区**：`<el-image>`（带 `preview-src-list` 支持放大查看），渲染当前选中的 `figure.file_path`。

### State 管理
- `figures`：该模型图列表（`figure_type` / `title` / `file_path`）。
- `activeIndex`：当前选中图索引，默认 `0`（第一张）。
- `loading`：图片加载态；切图时置 loading，加载完成清除。

### 切换与取图逻辑
1. 打开页面 → `GET /api/figures?model_name=` 拉取图列表，渲染 Tabs。
2. 点击某个 Tab → 更新 `activeIndex` → 主区渲染对应 `file_path`。
3. 取图：`file_path` 走静态目录，`<img>` 带不了 `X-API-Key`，用 `fetch`（带鉴权头）取二进制转 `ObjectURL` 渲染（同 `docs/api/figures.md` 口径）。
4. 图片资源：逐模型图集在 `backend/static/figures/{line}/{model}/`（由 `data_model/pipelines` 生成并拷贝），`file_path` 已含该路径。

## 表格列定义
| 列 | 字段 | 说明 |
|---|---|---|
| 提交 | `commit_hash` | 前 8 位，悬停显示完整哈希 |
| 作者 | `author_name` | — |
| 时间 | `committed_at` | — |
| 提交信息 | `message` | 超长省略，悬停全文 |
| **14 维特征** | `features` | 悬浮 / 抽屉预览，按五维度分组 |
| **SZZ 判断** | `is_bug_inducing` | `1` = 是（引入缺陷）/ `0` = 否，SZZ 自动打标 |
| **缺陷引入概率** | `risk_score` | 百分比显示，随所选模型动态变化 |

## 数据接口
| 用途 | 接口 |
|---|---|
| 架构 → 模型层级 | `GET /api/models` |
| 模型图片列表（多图导航） | `GET /api/figures?model_name=` |
| 多维指标表格 | `GET /api/commits?page=&size=&q=&model_name=&start_time=&end_time=` |

`GET /api/figures?model_name=` 响应（供多图导航动态生成 Tabs）：

```json
{
  "model_name": "lr_v1",
  "figures": [
    { "figure_type": "roc", "title": "ROC curve", "file_path": "/static/figures/expert/lr_v1/roc.png" },
    { "figure_type": "pr", "title": "PR curve", "file_path": "/static/figures/expert/lr_v1/pr.png" },
    { "figure_type": "confusion", "title": "Confusion matrix", "file_path": "/static/figures/expert/lr_v1/confusion.png" },
    { "figure_type": "calibration", "title": "Calibration curve", "file_path": "/static/figures/expert/lr_v1/calibration.png" },
    { "figure_type": "effort", "title": "Effort-aware curve", "file_path": "/static/figures/expert/lr_v1/effort.png" },
    { "figure_type": "feat_importance", "title": "Feature importance", "file_path": "/static/figures/expert/lr_v1/feat_importance.png" }
  ]
}
```

## 说明
- 导航栏图片名称 = `figures[].title`，图片地址 = `figures[].file_path`；列表完全由后端返回，前端不硬编码图类型。
- 每线对比图（`roc_curves.png` / `metric_bars.png` / `effort_curves_loc.png`）挂在 `data_model/pipelines/{line}/reports/figs/*.png`，属「线级」对比，不在「单模型多图导航」内，如需要可另行补充。
- 14 维特征只展示 Kamei 14 维；SZZ 真标签来自 `commit_label`（`label_method='szz'`），manual 不纳入。
- 「缺陷引入概率」= 所选模型的 `risk_score`，模型切换后整列刷新。
