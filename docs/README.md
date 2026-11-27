# 文档导航

本文件是 `docs/` 目录的**导航入口**。仓库运行与部署入口见根目录 [README.md](../README.md)，系统设计总纲见 [overview.md](overview.md)，可验收规格见 `openspec/specs/`。

## 阅读顺序

1. [overview.md](overview.md)：系统范围、页面、数据流、12 张表、模型口径与文档口径。
2. [project-structure.md](project-structure.md)：包结构、配置分层、算法资产与运行时产物归属。
3. 按角色查看对象契约：

| 目录 | 回答的问题 | 入口 |
|---|---|---|
| `api/` | 接口路径、参数、响应、错误码 | [api/README.md](api/README.md) |
| `database/` | 表结构、字段、约束、数据口径 | [database/README.md](database/README.md) |
| `function_point/` | 功能点职责、输入输出、边界 | 见下方功能点索引 |
| `web_page/` | 页面结构、交互、验收 | [web_page/README.md](web_page/README.md) |

## 功能点索引

| 编号 | 功能 | 页面设计 | 功能设计 | 接口 |
|---|---|---|---|---|
| ① | 数据存储 | [web_page/storage.md](web_page/storage.md) | [function_point/storage.md](function_point/storage.md) | [api/storage.md](api/storage.md) |
| ② | 数据收集 | [web_page/collect.md](web_page/collect.md) | [function_point/collect.md](function_point/collect.md) | [api/collect.md](api/collect.md) |
| ③ | 数据清洗 | [web_page/clean.md](web_page/clean.md) | [function_point/clean.md](function_point/clean.md) | [api/clean.md](api/clean.md) |
| ④ | 模型训练 | [web_page/train.md](web_page/train.md) | [function_point/train.md](function_point/train.md) | [api/train.md](api/train.md) |
| ⑤ | 模型预测 | [web_page/predict.md](web_page/predict.md) | [function_point/predict.md](function_point/predict.md) | [api/predict.md](api/predict.md) |
| ⑥ | 预测评估 | [web_page/evaluate.md](web_page/evaluate.md) | [function_point/evaluate.md](function_point/evaluate.md) | [api/evaluate.md](api/evaluate.md) |
| ⑦ | 结果解释 | [web_page/predict_detail.md](web_page/predict_detail.md) | [function_point/explain.md](function_point/explain.md) | [api/explain.md](api/explain.md) |
| ⑧ | 缺陷定位 | [web_page/predict_detail.md](web_page/predict_detail.md) | [function_point/localization.md](function_point/localization.md) | [api/source.md](api/source.md) |

配置区在数据存储页（见 [web_page/storage.md](web_page/storage.md)），配置接口见 [api/config.md](api/config.md)。

## 写作规范

- 只写最新设计，不记录阶段划分与历史版本。
- 接口只写 `api/`，表结构只写 `database/`，功能边界只写 `function_point/`，页面交互只写 `web_page/`；重复话术改为互相引用。
- 历史决策留在 `openspec/changes/archive/`，不回灌到现行设计文档。
- 测试提示词统一指向本文件，不单独归档。

## 测试说明

各测试文件中的「提示词见」统一指向本文件。测试用例的权威说明以测试代码本身与 [overview.md](overview.md) 为准。
