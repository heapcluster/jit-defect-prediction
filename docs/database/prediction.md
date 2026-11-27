# prediction

> 预测结果二维表必须落库；`infra/schema.sql` 与 ORM 字段与本文一致。`predicted_label` / `decision_threshold` 为非空字段，写入时必须提供。

**一句话**：一行对应一个 `(commit_hash, model_name)` 的最新完整预测结果二维表，是提交详情、预测页分页预览与预测评估的数据源。

实现锚点：backend/app/models.py:88-102（旧结构），目标字段以本文为准。

## 字段（目标契约）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| commit_hash | CHAR(40) | NOT NULL | 联合主键 + 外键 → `commit.commit_hash` | 被预测的提交 |
| model_name | VARCHAR(64) | NOT NULL | 联合主键 + 外键 → `model.model_name` | 打分模型 |
| risk_score | DECIMAL(6,5) | NOT NULL | ix_prediction_model_risk（第 2 列） | 风险概率 `[0,1]` |
| predicted_label | TINYINT | NOT NULL | — | 按本次 `decision_threshold` 生成的 0/1 标签 |
| decision_threshold | DECIMAL(4,3) | NOT NULL DEFAULT 0.500 | — | 本次预测判定阈值 |
| predicted_at | DATETIME | NOT NULL | — | 预测执行时间 |
| model_version | VARCHAR(64) | NULL | — | 产出该行时的模型版本（stale 溯源） |
| feature_version | VARCHAR(32) | NULL | — | 产出该行时的特征版本（stale 溯源） |
| is_bug_inducing | TINYINT | NULL | — | 从训练测试集透传的真标签；Web 批量预测必须非空 |
| job_id | VARCHAR(36) | NULL | ix_prediction_job | 产出该行的最新预测批次 |
| output_name | VARCHAR(128) | NULL | — | 本次预测结果展示名 / 导出文件基础名 |

## 主键与约束理由

- 联合主键 `(commit_hash, model_name)`：每模型每提交只保留最新一行，保证提交详情只显示当前有效结果。
- 复合索引 `(model_name, risk_score)`：支撑"某模型 + 按风险排序"的取数路径。
- `job_id` 与 `output_name` 用于追溯最近一次批量预测，不作为第二主键。
- 预测结果二维表与 `predictions.csv` predictions 列契约对齐：CSV 的列必须能从本表直接生成。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | predict 服务（单条同步）、批量预测服务（`job.kind=predict_batch`） | 幂等 upsert 完整预测结果行 |
| 读取 | commits（提交详情风险与标签）、evaluate（指标计算）、storage 导出服务 | 读预测结果 |
| 展示 | 提交详情、预测页分页预览 | 预测结果都来自它 |

## 口径

- **完整二维表落库**：批量预测成功的全部行 MUST 写入本表，至少包含 commit_hash、model_name、risk_score、predicted_label、decision_threshold、model_version、feature_version、predicted_at、is_bug_inducing；失败行不入库。
- **概率与标签同时保存**：`risk_score` 是模型概率；`predicted_label` 是本次按 `risk_score >= decision_threshold` 生成的标签。MUST NOT 把阈值烧进概率。
- **默认阈值**：预测页默认 `0.5`，用户本次修改后写入 `decision_threshold` 与 summary。
- **风险等级**：`risk_level(high|mid|low)` 仍由配置 `risk_high_threshold / risk_mid_threshold` 对 `risk_score` 现算，不单独落列。
- **版本溯源落本表**：`model_version / feature_version` 记录产出该行时的版本，供 stale 检测；历史行两列为 NULL 时视为过期。
- **真标签落本表**：Web 批量预测输入只能是训练阶段 `train_testset`，每行真实标签非空；本表 `is_bug_inducing` 必须透传该值，供评估读取与详情页展示。
- **`predicted_at` 对外**：提交详情按选中模型返回该行预测时间；无预测行时返回 `null`。
- **幂等语义**：同一提交同一模型重复预测时行数不变，更新概率、标签、阈值、版本、时间、真标签、job_id 与 output_name。
- **保存失败语义**：数据库保存失败视为批量预测任务失败；产物文件保留，任务可重试。重试成功后补齐本表结果。
- **内部特征列不落预测表**：`features`、原始特征向量、解释与定位结果不属于本表；需要时由提交详情 / 解释 / 定位各自数据源提供。

## 验收

- 同一提交同一模型重复预测：行数不变，完整结果行更新。
- Web 批量预测成功后，`prediction` 表行数等于 `summary.success_count`，且 `is_bug_inducing` 全部非空。
- 预测页分页预览读取本表，展示 predictions 列契约全部列，不展示内部特征列。
- 改阈值后重新预测会更新 `predicted_label` 与 `decision_threshold`，但同一次运行的 `risk_score` 仍由模型概率决定。
- 无预测行的提交在详情中返回 `null` 而非 0。
- 「某模型 + 风险排序」查询走复合索引。

