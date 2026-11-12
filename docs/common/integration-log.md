# 联调证据索引

本文件是**当前证据索引**，不能替代 `docs/api/` 的契约正文，也不能代替人工验收。联调基线见 [`local-runbook.md`](local-runbook.md)；具体操作按 [`../overview.md`](../overview.md) 的页面 ↔ 接口表执行。逐条用例结果与复现命令见 [`integration-report.md`](integration-report.md)。

| 场景 | 本次提交 SHA | 操作者 / 日期 | 结果 | 证据链接 |
|---|---|---|---|---|
| 后端五表初始化与健康检查 | `afdee84` + 本 PR 脚本 | neon / 2026-11-12 | 通过：`health=ok, db=up, models=8, commits=25,307` | [`evidence/2026-11-12/`](evidence/2026-11-12/)、`integration-report.md` §3 |
| 同步提交并轮询状态 | 同上 | neon / 2026-11-12 | 通过：25,285 → 25,307，`done=10/10`，`last_error=null` | `integration-report.md` §4（T-IN-20/21） |
| 风险列表与详情 | 同上 | neon / 2026-11-12 | 通过：列表 25,203 条、详情 99.9%（`xgb_v1`），`model_name` 透传一致 | [`evidence/2026-11-12/risk-list-*.png`](evidence/2026-11-12/)、`commit-detail-*.png` |
| 趋势与模型性能看板 | 同上 | neon / 2026-11-12 | 通过：周粒度 221 周期、月 53；模型性能看板可查询与预览 | [`evidence/2026-11-12/trend-board-*.png`](evidence/2026-11-12/)、`model-performance-*.png` |
| 异常场景：错误令牌、缺权重、空数据 | 同上 | neon / 2026-11-12 | 部分通过：错误令牌 6/6、空库实例 5/5；**缺权重未执行**（需移走 `.pkl`） | `integration-report.md` §5/§7、`backend/scripts/evidence/2026-11-12-security.md` |

旧 change 中标为“已截图”的路径如已删除，应由负责人重新附 PR 附件或飞书链接，并在此登记；不得把本索引本身当成通过证据。

## 2026-11-12 取证说明

- 本机已具备 conda `jit-defect-prediction`（Python 3.12.14：fastapi / sqlalchemy / pymysql / sklearn / xgboost / lightgbm / shap / transformers / pytest-cov 齐备）与 MySQL80，后端 `uvicorn`、前端 `vite` 均实跑，上表结果来自当次真实请求与浏览器截图。
- 逐条用例（35 条）结果、并发与跨模块链路见 [`integration-report.md`](integration-report.md)；非功能两项见 `backend/scripts/evidence/2026-11-12-{perf,security}.md`。
- 「缺权重」与 e2e 在线路径仍未取证：前者会破坏当次环境，后者缺 `commit_text.csv`（[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)）。
