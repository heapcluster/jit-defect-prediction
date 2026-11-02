# prediction（复用表）

**一句话**：一行对应一个 `(commit, model)` 的判断结果，是整个系统的核心数据——风险列表、详情、趋势、测试集评估全都读它。

## 字段

| 字段 | 类型 | 键 | 含义 |
|---|---|---|---|
| commit_hash | CHAR(40) | 主键（联合） + 外键 → `commit.commit_hash` | 被预测的提交 |
| model_name | VARCHAR(64) | 主键（联合） + 外键 → `model.model_name` | 哪个模型打的这个分 |
| risk_score | DECIMAL(6,5) | — | 风险概率 `[0,1]`，判定依据 |
| predicted_at | DATETIME | — | 预测执行时间 |
| feature_version | VARCHAR(32) | — | 预测所用特征版本 |
| updated_at | DATETIME | — | 审计列 |

## 约束与索引
- **联合主键 `(commit_hash, model_name)`**：每模型每提交仅一行（幂等保证），无需多余的自增 id。
- `(model_name, risk_score)` 复合索引：支撑列表/趋势「某模型 + 按风险排序」的取数，没有它是全表扫 + filesort。

## 被谁所用
| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | 后端 `sync` / `predict` 服务 | 现算或导入预测结果，幂等 upsert |
| 读取 | 后端 `commits`（列表/详情风险分）、`trends`（聚合）、`test_detail`（明细）、`champion`（默认模型解析） | 全链路读分 |
| 展示 | 前端风险列表、提交详情、趋势看板、测试集评估明细 | 所有页面显示的 `risk_score` 都来自它 |

## 口径
- 外键直接指向 `model.model_name`（`model` 表以 `model_name` 为主键），查询「按模型名筛」无需任何解析。
- 联合主键 `(commit_hash, model_name)` 取代「自增 id + 唯一约束」——后者多一个无人引用的死键（现状代码 `Prediction.id` 待删）。
- 导入范围按需求覆盖**四线 25 模型**（可先 expert 8 个）。
- **真标签不在这张表**：szz 真标签已并入 `commit_feature.is_bug_inducing`，算性能指标时 join `commit_feature` 取。
- 判定（高/中/低）不由本表字段给出，由调用方按 `.env` 写死阈值对 `risk_score` 现算。
