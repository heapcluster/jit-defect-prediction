# 数据库契约索引

当前数据库为五张表，结构见 `infra/schema.sql` 与 `backend/app/models.py`，字段含义以以下文档为准：

| 表 | 说明 |
|---|---|
| [`commit.md`](commit.md) | 提交元信息 |
| [`model.md`](model.md) | 模型注册与架构 |
| [`commit_feature.md`](commit_feature.md) | Kamei 14 维、检验集标记与 SZZ 真标签 |
| [`prediction.md`](prediction.md) | 按提交和模型保存风险预测 |
| [`model_figure.md`](model_figure.md) | 逐模型图索引 |

旧 `commit_label` 已并入 `commit_feature`，`runtime_setting` 已删除。特征输入的**列序**以 `data_model/pipelines/expert/models/feature_order.txt` 为准，不能只按本目录表格顺序组装模型输入。
