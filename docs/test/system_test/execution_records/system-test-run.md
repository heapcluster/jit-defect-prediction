# 系统测试执行记录 · 2026-11-12

> **性质**：执行记录（运行证据），**不是**系统测试计划/总结。按 AI-R5，`docs/common/` 的正式系统测试计划、总结与验收报告须由 neon 本人依据本记录撰写并签字，AI 不代写。
>
> 被测：`afdee84`（main，含 PR #216）＋本 PR 的测试脚本与文档（未改业务代码）
> 环境：Windows 本机；conda `jit-defect-prediction`（Python 3.12.14）；MySQL80 `jit_demo` / `jit_test`；后端 `uvicorn` 127.0.0.1:8000（另起 8001 空库实例）；前端 `vite` localhost:5173；浏览器 Chromium（Playwright）

## 1 · 端到端主线

| 步骤 | 操作 | 实测结果 | 证据 |
|---|---|---|---|
| 1 建库与启动 | `infra/setup_mysql.py --skip-start`；`uvicorn app.main:app` | 五表就绪；启动后 `health=ok, db=up, models_loaded=8` | 终端输出（§5 复现命令） |
| 2 同步真实提交 | `POST /api/sync?line=expert`，轮询 `/api/sync/status` | 25,285 → 25,307；`total=10, done=10, last_error=null`；单条抽取约 40–100s | `../../integration_test/report.md` §4 |
| 3 特征与预测 | `POST /api/predict`（`et_v1`，commit `3f166232…`） | `risk=0.97637`；14 维列序与 `config.FEATURE_COLUMNS` 一致；约 54ms（特征已在库） | `T-IN-13`、`T-IN-35` |
| 4 风险列表 | `/` 页面：分页、排序、模型级联 | 25,203 条，按风险降序，高风险标签与百分比正确；同步中显示「同步中 8/10」 | `risk-list-2026-11-12T09-09-57-241Z.png` |
| 5 提交详情 | `/commit/3f166232…` | 99.9% 高风险、`xgb_v1`、SZZ=引入缺陷、风险解释 Top-10、缺陷定位（行级着色 + 截断提示）、修复参考 5 条、14 维特征分组 | `commit-detail-2026-11-12T09-10-10-400Z.png` |
| 6 趋势看板 | `/trend` | 周粒度 221 个周期渲染成功，汇总卡与明细正常 | `trend-board-2026-11-12T09-10-30-729Z.png` |
| 7 模型性能看板 | `/model-performance` | 25,183 条提交可查、14 维特征预览、SZZ 判断、性能评估区可开 | `model-performance-2026-11-12T09-10-45-181Z.png` |

## 2 · 异常场景（5 类）

| 类别 | 状态 | 实测 |
|---|---|---|
| 空库 | ✅ 通过 | `jit_test` 清空五表后另起 8001 实例：`health=ok`（`commit_count=0`）、`/api/commits` → `code=0, total=0, items=[]`、`/api/trends` → `series=[]`、`/api/figures` → 404/40400。**空数据不是错误**。 |
| 无效令牌 | ✅ 通过 | 缺失/错误令牌在 `/api/commits`、`/api/models`、`/api/health` 共 6 例均 401 + `40100` + `missing or invalid token`；`/static/**` 同样 401。 |
| 非法参数 | ✅ 通过 | `size=101`、`granularity=day`、39/41 位 hash、非十六进制 hash → 400 + `40001`，响应体无堆栈/SQL/路径。 |
| 缺失权重 | ❌ 未执行 | 需临时移走 expert `.pkl` 或改造启动目录，会破坏当次环境并影响其他用例；留待单独窗口执行。 |
| 失败恢复 | ❌ 未执行 | 未构造同步中断/服务强杀；`sync/status.last_error` 与重启恢复路径只有代码阅读结论，无实测。 |

## 3 · 非功能（2 项）

| 维度 | 阈值/口径 | 实测 | 证据 |
|---|---|---|---|
| 性能 | `POST /api/predict` p95 < 500ms（100 次） | p50 28.3ms / **p95 48.1ms** / p99 48.9ms / max 56.0ms，达标 | [`backend/scripts/evidence/2026-11-12-perf.md`](../../../../backend/scripts/evidence/2026-11-12-perf.md) |
| 安全 | 鉴权失败 401/40100；畸形参数 40001 不泄漏；模型不可用不 500 | 12/12 通过；`et_semantic_v1` 返回 400/40001 明确文案 | [`backend/scripts/evidence/2026-11-12-security.md`](../../../../backend/scripts/evidence/2026-11-12-security.md) |

## 4 · 界面异常态与可用性观察

| 场景 | 结果 | 证据 |
|---|---|---|
| 详情页查不存在的提交 | 显示「该提交不存在」+「返回列表」，与「尚未预测」区分明确 | `commit-not-found-2026-11-12T09-15-47-087Z.png` |
| 未知路由 | 命中兜底页，非空白 | `not-found-2026-11-12T09-15-55-823Z.png` |
| 同步进度跨页 | 离开列表页再回到列表，进度条仍显示（PR #216 全局化后） | 见主线条目 4 |

## 5 · 复现命令

```bash
python infra/setup_mysql.py --skip-start
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev
cd backend && python scripts/integration_cases.py     # 35/35
cd backend && python scripts/security_cases.py        # 12/12
cd backend && python scripts/perf_loop.py             # p95=48.1ms
```

## 6 · 未覆盖与限制

- 未逐条执行 124 条 OpenSpec Scenario（仅覆盖四页面主干与上述异常），验收测试仍待组织。
- 「缺权重」「失败恢复」两类异常未执行，原因见 §2。
- 截图为本机 Chromium 全页/视口截图，未做多浏览器兼容性验证。
- 本记录不构成系统测试结论；结论与签字由 neon 依据本记录与 `report.md` 产出。
