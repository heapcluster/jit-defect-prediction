# 单条特征入口验证（2026-10-23）

- 在 Python 3.12 本地隔离环境运行 `python -m pytest -o addopts='' data_model/tests/test_single_commit_features.py -q`：`3 passed in 5.03s`。
- 运行 `python -m ruff check data_model/preparation/03_extract_features.py data_model/tests/test_single_commit_features.py --output-format concise`：`All checks passed!`。
- 用例创建临时 Git 仓库，逐条比较单条入口与既有批量 `compute_raw()` + `apply_contract()` 的 14 项结果；验证无批量 CSV、非法和不可达哈希拒绝。
- 这不是 Camel 全量仓库重跑；`extract_single_commit()` 每次扫描完整历史，尚未接入 HTTP，也没有 500ms p95 数据。后端接入与性能验收不得勾选完成。
