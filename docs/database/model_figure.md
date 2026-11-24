# model_figure

`实现状态：已实现　期次：一期`

**一句话**：逐模型性能图的索引表——把图集变成可查询、可关联的图元数据，前端模型性能看板据它列出某模型有哪些图。

实现锚点：backend/app/models.py:105-116

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| model_name | VARCHAR(64) | NOT NULL | 联合主键 + 外键 → `model.model_name` | 图所属模型 |
| figure_type | VARCHAR(32) | NOT NULL | 联合主键 | 图类型：`roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance` |
| title | VARCHAR(128) | NOT NULL | — | 图标题（前端展示用） |
| file_path | VARCHAR(255) | NOT NULL | — | 图相对路径，指向 `backend/static/figures/{line}/{model}/{figure_type}.png` |
| generated_at | DATETIME | NOT NULL | — | 图生成时间（审计列，接口不返回） |

## 主键与约束理由

- 联合主键 `(model_name, figure_type)`：每模型每种图只登记一行，重复生成按主键幂等覆盖，不造代理 id。
- 外键直接指向 `model.model_name`，`GET /api/figures?model_name=` 无需解析。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 评估服务（`job.kind=evaluate`）、模型线交付导入 | 登记逐模型图元数据 |
| 读取 | figures 服务（`GET /api/figures?model_name=`） | 返回该模型图清单 |
| 展示 | 模型性能看板「查看」抽屉 | 选定模型后渲染性能评估图集 |

## 口径

- 只登记逐模型图集；`figure_type` 取值 `roc` / `pr` / `confusion` / `calibration` / `effort` / `feat_importance`。
- `feat_importance` 仅 expert 线产出（Kamei 14 维可读）；semantic 的 768 维语义向量不直接映射可读特征名，不产出该图。两线均为 `.pkl` 权重模型包，无 safetensors 目录形态。
- `title` 由 `(model_name, figure_type)` 决定，每模型每图一个标题。
- `generated_at` 只写不读，用于追溯图生成批次。
- 图文件经 `/static/**` 提供，MUST 带 `X-API-Key` 鉴权，不为 `<img>` 开免鉴权例外。

## 验收

- 每模型每图一行；重复评估生成不产生重复登记。
- 按 `model_name` 查询返回完整图清单，`file_path` 可渲染。
- 无 `X-API-Key` 访问图文件被拒绝。