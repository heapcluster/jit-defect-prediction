# 交付模型清单加载验证（2026-10-23）

本次验证合成模型加载边界，并对本机已有三款权重做只读加载烟雾测试；不包含数据集或数据库联调。可复现：

```text
cd backend
python -m pytest -q tests/test_model_registry.py tests/test_predict_api.py
```

本地 Python 3.12 隔离环境运行结果：定向回归 `16 passed, 1 warning in 5.75s`；`cd backend && python -m pytest -o addopts='' -q` 为 `102 passed, 1 warning in 4.35s`。警告来自 Starlette 对 `httpx` 的兼容弃用提示，与本变更无关。`ruff check backend/app/model_registry.py backend/tests/conftest.py backend/tests/test_model_registry.py` 通过；`openspec validate delivery-model-allowlist --strict --no-interactive` 为 valid。PR CI 链接待首次运行后补入 PR 描述。

额外只读烟雾测试：在本机已有的 `data_model/pipelines/expert/models/` 中同时存在 8 个 `.pkl`，设置 `MODEL_DIR` 指向该目录后，注册表只载入 `['lr_v1', 'rf_v1', 'xgb_v1']`；三者对 14 维全零测试向量均可返回 0–1 概率。该向量不是实际提交，不是模型质量验收。

| 本机权重 | SHA-256 |
|---|---|
| `lr_v1.pkl` | `62BE0DCDEA9AAE1E96EAB2B1C5FFC1809FA9255FB09AD9D9329001CE5CB0F84B` |
| `rf_v1.pkl` | `0B72F1A4181A408CCFD8187ED4ADC54528FFB68EF0EB8FD1E489A5369F49BCBF` |
| `xgb_v1.pkl` | `BFED117A0092AEE4E5AF756AF8DC61DA2C7945C7966045191384D4AD1065C09E` |

这批权重的 MD5 与旧证据 `backend/scripts/evidence/predict-real-models-2026-10-16.md` 所记三值不同，需模型线确认是否为重训练/重打包版本，不能将旧分数当作此批的验收结果。真实数据灌库、HTTP 预测和 p95 仍未做；不得把本文件当作完整联调验收。
