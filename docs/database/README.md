# 数据库文档索引

本目录定义表结构、字段含义、约束与数据口径。建表真源是 `infra/schema.sql`；本文只解释语义，不复制 DDL。

| 表 | 文档 | 说明 |
|---|---|---|
| `algorithm` | [algorithm.md](algorithm.md) | 算法库与超参 schema |
| `commit` | [commit.md](commit.md) | 提交锚点 |
| `commit_feature` | [commit_feature.md](commit_feature.md) | Kamei 14 维特征、标签与模型输入 |
| `dataset` / `dataset_commit` | [dataset.md](dataset.md) | 数据集与成员快照，一份文档覆盖两张关联表 |
| `job` | [job.md](job.md) | 六类异步任务与产物引用 |
| `model` | [model.md](model.md) | 在线模型登记 |
| `model_artifact` | [model_artifact.md](model_artifact.md) | 权重工件与 `model` 派生关系 |
| `model_figure` | [model_figure.md](model_figure.md) | 逐批次逐模型图索引 |
| `prediction` | [prediction.md](prediction.md) | 预测结果二维表 |
| `user` | [user.md](user.md) | 系统用户 |
| `user_config` | [user_config.md](user_config.md) | 运行期配置唯一权威 |

返回上级：[docs/README.md](../README.md)
