# 单条提交特征抽取

## Why

现有 `data_model/preparation/03_extract_features.py` 只能从预生成 `commits.csv` 批量抽取。新提交尚未入库时，后端无法拿到 14 维特征，`POST /api/predict` 返回 40400。演示交付已确定以三个已登记模型为在线集，并要求新提交可以现算特征；本 change 先提供复用冻结 v1 口径的单条入口。

## What Changes

- 增加 `extract_single_commit(repo_dir, commit_hash)`：从本地 Git 仓库读取提交元信息，复用批量 `compute_raw()` 和 `apply_contract()`，返回 14 项值及有序向量。
- 增加 `--commit` 命令行模式：仅输出 JSON，不依赖 `commits.csv`，不改写批量产物。
- 用临时 Git 仓库对照批量旧算法，并覆盖非法、不可达提交。

## Capabilities

### Added Capabilities

- `single-commit-features`: 对 HEAD 可达的非合并提交按既有 v1 契约计算 14 项特征。

## Impact

仅改模型线抽取入口和测试，不修改冻结的 `docs/model/feature-columns.md` 数值口径、14 项顺序、数据库结构或现有批量输出。后端接入应作为下一独立 change，按 `docs/backend/api-spec.md` 更新缺特征行时的行为并做性能测试。

## 不做什么

本 change 不在 HTTP 请求中直接运行全量历史扫描，不承诺 500ms 性能达标；不上传仓库数据或模型权重，不修改前端或后端代码，不把合成仓库测试当 Camel 全量复现。
