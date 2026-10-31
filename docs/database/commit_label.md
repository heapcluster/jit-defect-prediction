# commit_label（复用表）

真标签表，作为「模型判断是否正确」的对照基准。

| 字段 | 含义 |
|---|---|
| `id` | 自增主键 |
| `commit_hash` | 关联 `commit` |
| `is_bug_inducing` | 该提交是否引入缺陷（0/1） |
| `label_method` | 标签来源口径：`szz` / `manual` |
| `bug_fix_hash` | 关联修复提交（SZZ 回溯用） |
| `labeled_at` | 打标时间 |

**说明**：
- 本设计评估**只用 `szz` 口径**；`manual` 为冗余非核心，不纳入测试集评估范围。
- szz 真标签用于计算性能指标（AUC / PR / 混淆矩阵）与阈值校准。
