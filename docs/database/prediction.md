# prediction

`实现状态：已实现　期次：一期`

**一句话**：一行对应一个 `(commit, model)` 的预测结果，是系统的核心数据——风险列表、详情、趋势、模型性能看板全都读它。

实现锚点：backend/app/models.py:88-102

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| commit_hash | CHAR(40) | NOT NULL | 联合主键 + 外键 → `commit.commit_hash` | 被预测的提交 |
| model_name | VARCHAR(64) | NOT NULL | 联合主键 + 外键 → `model.model_name` | 打分模型 |
| risk_score | DECIMAL(6,5) | NOT NULL | ix_prediction_model_risk（第 2 列） | 风险概率 `[0,1]` |
| predicted_at | DATETIME | NOT NULL | — | 预测执行时间 |
| model_version | VARCHAR(64) | NULL | — | 产出该行时的模型版本（stale 溯源） |
| feature_version | VARCHAR(32) | NULL | — | 产出该行时的特征版本（stale 溯源） |

## 主键与约束理由

- 联合主键 `(commit_hash, model_name)`：每模型每提交仅一行，幂等 upsert 的天然保证，不造代理 id。
- 复合索引 `(model_name, risk_score)`：支撑列表 / 趋势「某模型 + 按风险排序」的取数路径，避免全表扫 + filesort。
- 双外键直接指向自然主键，按模型名 / 提交哈希筛选无需任何解析。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | predict 服务（单条同步）、批量预测服务（`job.kind=predict_batch`） | 幂等 upsert 预测结果 |
| 读取 | commits（列表 / 详情风险分与 `predicted_at`）、trends（聚合）、evaluate（指标计算）、导出服务 | 全链路读分 |
| 展示 | 风险列表、提交详情、趋势看板、模型性能看板 | 所有页面的 `risk_score` 都来自它 |

## 口径

- **概率与标签分离**：本表只存概率；高 / 中 / 低判定与二分类标签由调用方按配置单源阈值对 `risk_score` 现算（权威 = `user_config` 的 `risk_high_threshold / risk_mid_threshold / decision_threshold`，见 [user_config.md](user_config.md)）。MUST NOT 把阈值烧进概率。
- **版本溯源落本表**：`model_version / feature_version` 记录产出该行时的版本，供 stale 检测；当前模型/特征版本权威仍为 `model` 与 `commit_feature`，单条预测对比两者判定过期。历史行两列为 NULL 时视为过期（无法证明同版本），不冒充新鲜。
- **真标签不在本表**：算性能指标时 join `commit_feature.is_bug_inducing` 取；`NULL`（未打标）样本不参与指标计算。
- **`predicted_at` 对外**：提交详情按选中模型返回该行预测时间；该提交没有选中模型的预测行时，`risk_score` / `predicted_at` 同为 `null`。
- 批量预测保持联合主键幂等；单条预测沿用库中结果时，若行内 `model_version / feature_version` 与当前模型/特征版本不一致则 `stale=true`，`force_recompute=true` 重算并刷新版本。旧库经迁移脚本为 prediction 增补这两个可空列（不回填历史版本）。
- 导入范围覆盖四线 25 模型。

## 验收

- 同一提交同一模型重复预测：行数不变，分数与时间更新。
- 「某模型 + 风险排序」查询走复合索引。
- 改阈值只改变判定标签展示，`risk_score` 本体不变。
- 无预测行的提交在详情中返回 `null` 而非 0。