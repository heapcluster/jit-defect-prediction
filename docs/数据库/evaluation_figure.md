# evaluation_figure

## 用途

评估图表文件登记。每张图一条，归属一次评估，用于历史详情展示与 PNG 下载。

## 字段

| 字段 | 类型 | 可空 | 默认 | 说明 |
|---|---|---|---|---|
| `figure_id` | CHAR(36) | 否 | — | 主键 |
| `evaluation_id` | CHAR(36) | 否 | — | 所属评估 |
| `figure_type` | VARCHAR(16) | 否 | — | `roc` / `pr` / `confusion` / `bar` |
| `file_path` | VARCHAR(512) | 否 | — | PNG 相对仓库根目录的路径（如 `temp/evaluations/...`） |
| `sha256` | CHAR(64) | 否 | — | 文件校验 |
| `width` | INT | 是 | NULL | 像素宽 |
| `height` | INT | 是 | NULL | 像素高 |
| `created_at` | DATETIME | 否 | — | 生成时间 |

## 约束与索引

- 主键 `figure_id`。
- 外键 `evaluation_id` → `evaluation.evaluation_id`（`ON DELETE CASCADE`）。
- 索引 `ix_evaluation_figure_evaluation (evaluation_id)`。
- 同一次评估同一 `figure_type` 只登记一条。

## 删除语义

- 随评估删除；不单独提供删除入口。
- 图片只服务评估历史，不进入数据存储页。

## 读写方

- 写入：`POST /api/evaluate/save`。
- 读取：`GET /api/evaluate/history/{evaluation_id}`、`GET /api/evaluate/results/{job_id}/figures/{figure_type}`、`GET /api/evaluate/history/{evaluation_id}/figures/{figure_type}`。
