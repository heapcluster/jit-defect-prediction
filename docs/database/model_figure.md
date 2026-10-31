# model_figure（新增表）

各模型性能图的索引表，后端据它列出某模型有哪些图，前端拿 `file_path` 渲染。

| 字段 | 含义 |
|---|---|
| model_name | 关联 `model`（该图属于哪个模型） |
| figure_type | 图类型标识：`roc` / `pr` / `confusion` / `calibration` / `feat_importance` |
| title | 图标题（前端展示用） |
| file_path | 图文件相对路径，指向 `backend/static/figures/{line}/{model}/{figure_type}.png` |
| generated_at | 图生成时间（用于判断是否过期重生成） |

**角色**：把"图"从一堆 png 文件变成可查询、可关联的元数据；明细展示与切换模型的图集都靠它。
