# model_figure

`实现状态：目标设计　期次：一期`

**一句话**：逐批次、逐模型性能图的索引表——把评估图集拆成可按批次与模型查找的图元数据，前端模型性能页据它列出某模型有哪些图，评估产物库据它定位某次评估的每张图。

实现锚点：backend/app/models.py、infra/schema.sql（`job_id` 与标准文件名已按本文落地）。

## 字段

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| job_id | VARCHAR(36) | NOT NULL | 联合主键 + 索引（逻辑关联 `job.job_id`） | 产生该图的评估任务批次，用于区分同模型多次评估 |
| model_name | VARCHAR(64) | NOT NULL | 联合主键 + 外键 → `model.model_name` | 图所属模型（一次评估固定单一模型） |
| figure_type | VARCHAR(32) | NOT NULL | 联合主键 | 图类型：`roc` / `pr` / `confusion` / `calibration` / `effort_unaware` / `effort_aware` |
| figure_name | VARCHAR(128) | NOT NULL | — | 后端标准文件名，形如 `evaluate_<job_id>_<figure_type>.png` |
| title | VARCHAR(128) | NOT NULL | — | 图标题（前端展示用） |
| file_path | VARCHAR(255) | NOT NULL | — | 图相对路径，指向 `backend/static/figures/{model_name}/evaluate_<job_id>_<figure_type>.png` |
| testset_ref | VARCHAR(64) | 可空 | — | 图对应的训练测试集标识，便于按数据集查找 |
| generated_at | DATETIME | NOT NULL | — | 图生成时间（审计列，接口不返回） |

## 主键与约束理由

- 联合主键 `(job_id, model_name, figure_type)`：同一次评估每种图只登记一行；不同评估批次（不同 `job_id`）的同类型图各自保留，不被覆盖，支持按批次追溯。
- `job_id` 以联合主键 + 索引关联评估任务（不建物理外键，避免 `model_figure` 建表顺序依赖 `job`）；可按 `job_id` 查询一次评估的完整图集。
- 外键 `model_name → model.model_name`：`GET /api/figures?model_name=` 无需解析。
- `figure_name` 由后端按 `evaluate_<job_id>_<figure_type>.png` 标准生成，不由用户输入；图集 zip 内的文件名与数据库登记、文件夹保存名三者一致。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 评估服务（`job.kind=evaluate`） | 逐张图标准命名保存并登记图元数据 |
| 读取 | figures 服务（`GET /api/figures?model_name=` / `?job_id=`） | 返回某模型或某评估批次的图清单 |
| 展示 | 模型性能页「查看」抽屉 | 选定模型与评估批次后渲染性能评估图集 |
| 展示 | 评估页结果区图集预览 | 按 `job_id` 定位本次评估的每张图 |

## 口径

- 只登记逐图集元数据；`figure_type` 取值 `roc` / `pr` / `confusion` / `calibration` / `effort_unaware` / `effort_aware`。
- 用户在评估页只命名图集 zip，图集内每张图由后端按标准命名单独保存，文件名与 `figure_name` / `file_path` 一致，便于文件夹与数据库查找。
- `title` 由 `(model_name, figure_type)` 决定，同类型图跨批次共用一个标题。
- `testset_ref` 记录图对应的训练测试集，配合 `job_id` 支持「同模型不同测试集」的图区分。
- `generated_at` 只写不读，用于追溯图生成时间；批次追溯以 `job_id` 为准。
- 图文件经 `/static/**` 提供，MUST 带 `X-API-Key` 鉴权，不为 `<img>` 开免鉴权例外。

## 验收

- 一次评估每种图一行；重复评估不会覆盖历史批次，可按 `job_id` 查询完整图集。
- 按 `model_name` 查询返回该模型图清单，`file_path` 可渲染；按 `job_id` 查询返回该批次图清单。
- `figure_name`、`zip` 内文件名与文件夹保存名三者一致。
- 无 `X-API-Key` 访问图文件被拒绝。
