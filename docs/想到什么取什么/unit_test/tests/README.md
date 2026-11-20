# 单元测试代码（提交快照）

本目录是从仓库各端**复制**过来的测试代码，用于交付归档。**运行时请回各端真源目录**，不要在这里执行——这里没有 `pytest.ini` / `vite.config.js` / `package.json`，直接跑会因找不到配置和依赖而失败。

## 与真源的对应关系

| 本目录 | 真源 | 运行方式 | 用例数 |
|---|---|---|---:|
| `backend/` | `backend/tests/` | `cd backend && python -m pytest -q` | 279 |
| `data_model/` | `data_model/tests/` | `cd data_model && python -m pytest -q` | 163 |
| `frontend/` | `frontend/tests/` | `cd frontend && npm run test:unit` | 65 |
| `infra/` | `infra/tests/` | `python -m pytest -q infra/tests` | 8 |
| `ci/` | `.github/ci/tests/` | `python -m unittest discover -s .github/ci/tests -p 'test_*.py'` | 11 |
| — | — | **合计** | **526** |

## 说明

- 快照与真源逐字节一致（不含 `__pycache__` 等缓存）。
- 真源目录还有 `pytest.ini`（后端/模型线）、`vite.config.js`（前端）、`conftest.py`（后端夹具），这些属于各端工程配置，不在本快照内。
- 每个测试文件头部含 §2.1 格式的 AI 辅助说明注释。
- 测试结果与覆盖率见 [`../README.md`](../README.md)。
