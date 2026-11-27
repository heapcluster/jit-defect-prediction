# 页面文档索引

本目录定义页面结构、交互流程与验收口径。接口契约见 `../api/`，功能边界见 `../function_point/`。

| 页面 | 文档 | 说明 |
|---|---|---|
| 数据存储 | [storage.md](storage.md) | 我的文件 + 我的配置；无文件导入入口 |
| 数据收集 | [collect.md](collect.md) | 分支枚举、公开数据集采集、全量分页预览 |
| 数据清洗 | [clean.md](clean.md) | 四步清洗、前后差异表、全量分页预览 |
| 模型训练 | [train.md](train.md) | 算法卡片、超参、训练集 / 测试集 / `.pkl` 交付 |
| 模型预测 | [predict.md](predict.md) | 模型与数据集选择、全量分页结果预览 |
| 预测详情 | [predict_detail.md](predict_detail.md) | 提交详情、解释与定位内联 |
| 预测评估 | [evaluate.md](evaluate.md) | 单模型性能指标图 zip 与指标表 |

配置区位于数据存储页，`/settings` 重定向到 `/storage`。

模型性能读取入口属于预测评估页，不单独设页面文档。

返回上级：[docs/README.md](../README.md)
