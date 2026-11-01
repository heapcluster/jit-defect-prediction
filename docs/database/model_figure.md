# model_figure（新增表）

**一句话**：各模型性能图的索引表——把「一堆 png 文件」变成「可查询、可关联的图元数据」，前端测试集评估页据它列出某模型有哪些图。

## 字段

| 字段 | 类型 | 键 | 含义 |
|---|---|---|---|
| model_name | VARCHAR(64) | 主键（联合） + 外键 → `model.model_name` | 该图属于哪个模型 |
| figure_type | VARCHAR(32) | 主键（联合） | 图类型：`roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| title | VARCHAR(128) | — | 图标题（前端展示用） |
| file_path | VARCHAR(255) | — | 图相对路径，指向 `backend/static/figures/{line}/{model}/{figure_type}.png` |
| generated_at | DATETIME | — | 图生成时间（判断是否过期重生成） |
| updated_at | DATETIME | — | 审计列 |

## 约束与索引
- **联合主键 `(model_name, figure_type)`**：每个模型每种图只登记一行，无需多余的自增 id。

## 被谁所用
| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 模型线交付（`export_sql.py` 生成 `data_init.sql`） | 登记逐模型图元数据 |
| 读取 | 后端 `figures` 服务（`GET /api/figures?model_name=`） | 返回该模型图清单，前端按 `file_path` 渲染 |
| 展示 | 前端测试集评估页「模型效果图」板块 | 切换模型时刷新图集 |

## 口径
- 只登记**逐模型图集**；`figure_type` 取值 `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance`。
- `feat_importance` 仅 `expert` 线产出（Kamei 14 维可读）；semantic / fused 的 768 维、e2e 文本不产出该图——e2e 只有 5 张。
- 外键直接指向 `model.model_name`（`model` 表以 `model_name` 为主键），`GET /api/figures?model_name=` 无需解析。
