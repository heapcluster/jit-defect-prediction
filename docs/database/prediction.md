# prediction（复用表）

一行对应一个 `(commit, model)` 的判断结果，是本次需求的核心数据（"每个模型的判断结果"）。

| 字段 | 含义 |
|---|---|
| id | 自增主键 |
| commit_hash | 关联 `commit`（被预测的提交） |
| model_name | 关联 `model`，如 `lr_v1` / `lr_fused_v1` / `codebert_e2e_v1` |
| risk_score | 风险概率 `[0,1]`，模型对"引入缺陷"的置信度，判定依据 |
| predicted_at | 预测执行时间 |
| feature_version | 预测所用特征版本 |

**约束**：`(commit_hash, model_name)` 唯一，保证每模型每提交仅一行。

**说明**：
- 结构不变；导入范围按需求覆盖**四线 25 模型**（可先 expert 8 个）。
- 真标签（szz）不在此表，由测试集明细 CSV 随行提供，用于计算性能指标。
