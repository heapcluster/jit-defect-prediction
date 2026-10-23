# 交付模型清单加载验证（2026-10-23）

本次只验证合成模型加载边界，不包含真实权重、数据集或数据库联调。可复现：

```text
cd backend
python -m pytest -q tests/test_model_registry.py tests/test_predict_api.py
```

本地 Python 3.12 隔离环境运行结果：定向回归 `16 passed, 1 warning in 5.75s`；`cd backend && python -m pytest -o addopts='' -q` 为 `102 passed, 1 warning in 4.35s`。警告来自 Starlette 对 `httpx` 的兼容弃用提示，与本变更无关。`ruff check backend/app/model_registry.py backend/tests/conftest.py backend/tests/test_model_registry.py` 通过；`openspec validate delivery-model-allowlist --strict --no-interactive` 为 valid。PR CI 链接待首次运行后补入 PR 描述。

真实交付仍须拿 `lr_v1.pkl`、`rf_v1.pkl`、`xgb_v1.pkl` 与 `feature_order.txt` 同目录验证，并另测预测 p95；不得把本文件当作已完成验收。
