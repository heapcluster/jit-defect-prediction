# 新提交在线预测合成联调（2026-10-23）

在临时 Git 仓库创建一条实际提交，调用后端测试客户端的 `POST /api/predict`；测试会检查 14 项特征、`commit` / `commit_feature` / `prediction` 落库、重复请求幂等、详情回显和显式模型列表查询。

复现命令：`cd backend && python -m pytest -o addopts='' -q`。本地 Python 3.12 环境结果：`103 passed, 1 warning in 3.63s`；警告为 Starlette `httpx` 兼容弃用提示。`ruff check app tests` 通过。

本测试使用合成小仓库和夹具模型，不等于 Camel 全量仓库、真实三权重、MySQL 联调或 500ms p95 验收。本机未找到 `data_model/data/camel/` 与需灌库的 CSV；这些工作明确保持未完成。
