# 新提交在线预测合成联调（2026-10-23）

在临时 Git 仓库创建一条实际提交，调用后端测试客户端的 `POST /api/predict`；测试会检查 14 项特征、`commit` / `commit_feature` / `prediction` 落库、重复请求幂等、详情回显和显式模型列表查询。

复现命令：`cd backend && python -m pytest -o addopts='' -q`。本地 Python 3.12 环境结果：`103 passed, 1 warning in 3.63s`；警告为 Starlette `httpx` 兼容弃用提示。`ruff check app tests` 通过。

本测试使用合成小仓库和夹具模型，不等于 Camel 全量仓库、真实三权重、MySQL 联调或 500ms p95 验收。本机未找到 `data_model/data/camel/` 与需灌库的 CSV；这些工作明确保持未完成。

另在并行的三模型加载 PR #96 上，以本机已有权重、14 维全零向量做 5 次函数级探测：`rf_v1` 预热后推理+解释为 608.1 / 605.8 / 691.9 / 947.5 / 854.3ms，均超过 500ms。此结果不含 HTTP/数据库/真实输入，也不是正式 p95，但已提示三模型交付与性能靶子冲突；必须在真实联调中优化并重测，不能将本合成测试通过解释为非功能达标。
