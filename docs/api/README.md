# API 文档索引

本目录只定义 HTTP 契约：路径、参数、响应、错误码与产物引用。功能边界见 `../function_point/`，页面交互见 `../web_page/`。

| 领域 | 文档 | 说明 |
|---|---|---|
| 数据存储 | [storage.md](storage.md) | 产物登记、数据链路、导出；文件导入仅为内部登记，不暴露给用户 |
| 数据收集 | [collect.md](collect.md) | Git / 公开数据集采集与 SZZ 打标 |
| 提交查询 | [commits.md](commits.md) | 提交、特征、标签与预测结果只读查询 |
| 数据清洗 | [clean.md](clean.md) | 预览 / 应用清洗、前后差异、单一 CSV 与按需 XLSX |
| 模型训练 | [train.md](train.md) | 切分、训练、`.pkl` 与训练 / 测试集交付 |
| 模型预测 | [predict.md](predict.md) | 测试集打分、写 `prediction` 表、预测结果交付 |
| 预测评估 | [evaluate.md](evaluate.md) | 单模型指标图集 zip 与指标表 |
| 结果解释 | [explain.md](explain.md) | SHAP / LIME 特征贡献 |
| 缺陷定位 | [source.md](source.md) | 源码树 / 文件读取与可疑行定位 |
| 图集 | [figures.md](figures.md) | 逐图索引、批次查询与缺图原因 |
| 模型清单 | [models.md](models.md) | 架构 → 模型级联与加载 / 卸载 / 重载 |
| 任务中心 | [jobs.md](jobs.md) | 六类异步任务状态、重试与取消 |
| 配置中心 | [config.md](config.md) | 运行期配置读写 |
| 数据集 | [datasets.md](datasets.md) | 数据集列表、成员与导出 |
| 同步 | [sync.md](sync.md) | 异步数据同步触发与状态 |
| 健康检查 | [health.md](health.md) | liveness / readiness 探针 |

返回上级：[docs/README.md](../README.md)
