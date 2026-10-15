# Camel 数据源切换补齐

## Why

基于 `feat/model/expert-line-training` 的 `866b7dc`：代码和训练报告已切换为 Camel，但数据源登记、契约中的 repo_name、活规格和 SZZ 报告模板仍混有 ActiveMQ 口径。自检基准为 None，报告还把「尚未登记」误报成「子集」。这会使干净环境无法按文档复现，也可能掩盖判据漂移。

## What Changes

- 沿用已训练的 Camel `camel-4.23.0` 和完整提交 `b2329103df8f5d1edfca2ad262be09e3be95ee68`，不另选版本。
- 依据既有 Camel 全量采集/SZZ 证据登记样本数和三项判据基准；修正报告中的编号、未登记/子集状态与自检失败处理。
- 同步当前数据源说明、复现命令和规格，保留历史归档与历史实验数字的来源。
- 新增判据、报告和失败路径回归测试。

## Capabilities

### Modified Capabilities
- `commit-collection`: 明确 Camel 固定源和仓库字段值。
- `szz-labeling`: Camel 判据、自检状态和失败退出与登记一致。

## Impact

影响 `data_model/02_szz_labeling.py`、数据线测试和相关文档/规格；`repo_name` 的值由 activemq 切换为 camel，列名、类型、14 项特征、70%/30% 时间切分和接口格式不变。仅替换 `docs/design/sprint0-scope.md` 的单仓库对象，不扩大产品边界。

未归档的 `semantic-feature-mainline`、`public-dataset-quality` 提案同步当前单仓库名称和样本规模；旧语义特征耗时估算标记为需按 Camel 重测，保持各自范围与完成状态不变。

## 不做什么

不修改前后端代码、不重新实现已有 Camel 训练、不改模型或特征定义、不改数据库、不合并队友分支、不上传数据集/模型、不重写历史归档。本机没有全量数据，本次不把上游报告当成本机重新运行的结果。
