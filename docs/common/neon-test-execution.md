# neon 测试工作执行记录

> 本文件记录 neon 承接的集成 / 系统 / 验收测试**执行边界与证据**，不是测试报告。逐条用例见 [`integration-report.md`](integration-report.md)，系统侧执行见 [`evidence/2026-11-12/system-test-run.md`](evidence/2026-11-12/system-test-run.md)。
>
> 分支：`test/neon-test-baseline` ｜ 代码基线：`afdee84`（main，含 PR #216）｜ 负责人：neon
> **状态变更**：2026-11-10 因本机无可用 Python 后端运行时，后端相关项全部标记「未执行」；**2026-11-12 用户提供 conda 环境 `jit-defect-prediction` 与本机 MySQL 后，原阻断项已实际执行**（下表 E-11 起）。历史结论保留，不删改。

## 1 · 环境能力（2026-11-12 复测）

| 项 | 实查结果 | 命令 / 佐证 |
|---|---|---|
| Python | conda env `jit-defect-prediction` = **3.12.14**，`fastapi` / `sqlalchemy` / `pymysql` / `pandas` / `numpy` / `sklearn` / `xgboost` / `lightgbm` / `shap` / `joblib` / `httpx` / `transformers` / `pytest-cov` **齐备** | `D:\workspace\env\miniconda3\envs\jit-defect-prediction\python.exe -V` 与逐模块 `find_spec` |
| 系统 `python` | 仍是 WindowsApps 占位程序（无输出） | 因此本轮全部命令均用 conda 解释器绝对路径 |
| MySQL | `MySQL80` Running，`jit_demo`（25,307 提交）与 `jit_test` 就绪；`infra/setup_mysql.py --skip-start` 建五表成功 | 实测输出「五张表就绪」 |
| 后端 | `uvicorn app.main:app` @8000 启动成功，`health=ok, db=up, models_loaded=8` | `D:\workspace\tmp\uvicorn.log` |
| 前端 | `vite` @5173，`/api`、`/static` 代理到 8000 | `D:\workspace\tmp\vite.log` |
| 浏览器 | Chromium（Playwright），四页面 + 两种异常态截图入库 | `docs/common/evidence/2026-11-12/*.png` |
| 空库实例 | `jit_test` 清空五表后另起 8001 实例（无需 root 建库权限） | 见执行记录 §5 |
| 模型权重 | expert 8 个 `.pkl` 可用；semantic 语义表在 `data_model/data/`（默认路径不符，见 #217）；e2e 文本表缺失（#218） | 实测 `predict` 行为 |
| OpenSpec CLI | 1.11.0 | `openspec validate` 通过 |

2026-11-10 的旧结论（「本机无可用后端运行时，不安装环境」）在当时成立；本轮环境由用户提供，**未由我安装或下载任何依赖**，也未修改 `.env` / `pytest.ini` / git 配置。

## 2 · 已执行项与真实结果

| # | 项 | 命令 | 结果 | 证据 |
|---|---|---|---|---|
| E-01 | 端点清单静态核对 | 人工 + 静态检索 | 11/11 路由覆盖；发现 6 处文档偏差 + 2 处规格缺口 | [`endpoint-inventory.md`](endpoint-inventory.md) §2–§3 |
| E-02 | 前端契约测试 | `cd frontend && npm run test:unit` | 9 文件 / **59 用例通过**，26.41s | 终端输出 |
| E-03 | 口径冲突盘点 | 静态检索 | 6 处接口文档偏差 + 2 处规格缺口 | `endpoint-inventory.md` §3 |
| E-04 | 用例设计 | AI 生成 + 人工复核 | 11 端点 × 四类场景（44 条设计，落地 35 条可执行用例） | `endpoint-inventory.md` §4 |
| E-05 | OpenSpec 校验 | `openspec validate neon-test-baseline --strict` | `is valid`；活规格 `12 passed, 0 failed` | 终端输出 |
| E-06 | PR #216 审阅与合入 | GitHub API review + squash merge | APPROVE，合入 `afdee84`；3 项跟进缺陷 | [`pr-review-log.md`](pr-review-log.md) |
| E-07 | 缺陷登记 | GitHub Issues | #217 语义表路径 / #218 e2e 文本表 / #219 契约部署 / #220 文档偏差 | [`defect-records.md`](defect-records.md) |
| E-08 | 合并后分支同步 | `git rebase main` | 分支与 `afdee84` 对齐 | git log |
| E-09 | 看板映射 | Bitable `tblLQAW6z5LB59nI` | 11 项任务入板（Sprint 2/3、负责人、状态、change、链接） | [项目看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) |
| E-10 | 周报 | `docs +create` | 《工作周报-20261113》已建（计划/总结/下周计划） | [周报](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa) |
| E-11 | 运行时契约导出 | `GET /openapi.json` | **11 个路径**，与文档/清单逐条一致；详情含 `model_name`；11/11 需 `x-api-key` | `integration-report.md` §1 |
| E-12 | 后端单测 + 覆盖率 | `python -m pytest -q --cov=app --cov-branch` | **249 passed / 0 failed**，28.2s；行覆盖 **85%**（分支 336，部分覆盖 40），HTML 报告已生成 | 终端输出（报告产物未入库） |
| E-13 | 集成用例 | `python scripts/integration_cases.py` | **35/35 通过**（含跨模块链路与并发） | [`integration-report.md`](integration-report.md) §3–§4 |
| E-14 | 安全用例 | `python scripts/security_cases.py` | **12/12 通过**（鉴权/畸形参数/模型不可用） | `backend/scripts/evidence/2026-11-12-security.md` |
| E-15 | 性能压测 | `python scripts/perf_loop.py` | p50 28.3ms / **p95 48.1ms** / p99 48.9ms / max 56.0ms，达标（<500ms） | `backend/scripts/evidence/2026-11-12-perf.md` |
| E-16 | 系统测试主线（浏览器） | Playwright 打开四页面 | 四页均渲染真实数据；截图 6 张入库 | `docs/common/evidence/2026-11-12/` |
| E-17 | 异常场景 | API + 第二实例 + 浏览器 | 空库 ✅、无效令牌 ✅、非法参数 ✅、详情不存在 ✅、未知路由 ✅；**缺权重 / 失败恢复未执行** | `system-test-run.md` §2 |

## 3 · 仍未执行 / 未产出

| # | 项 | 状态 | 原因 | 解除条件 |
|---|---|---|---|---|
| N-01 | 「缺权重」异常 | 未执行 | 需移走 expert `.pkl`，会破坏当次环境并影响其他用例 | 单独测试窗口，执行人 neon |
| N-02 | 「失败恢复」（同步中断 / 服务强杀后恢复） | 未执行 | 未构造断网/强杀场景 | 系统测试补充 |
| N-03 | e2e 在线预测 | 未验证 | `pipelines/e2e/data/commit_text.csv` 未生成（生成脚本 `build_text_dataset.py` 存在，[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)），当前恒 40001 | 生成产物后重跑 T-IN-16 扩展用例 |
| N-04 | 验收逐 Scenario（124 条） | 未执行 | 需按 `openspec/specs/` 逐条现场点验；本轮只覆盖四页面主干与异常态 | 组织验收演示，执行人 neon |
| N-05 | 系统测试计划/总结、验收方案/报告 | 未产出 | AI-R5：须 neon 本人撰写并签字 | neon 依据 `evidence/2026-11-12/` 产出 |
| N-06 | 前端逐接口联调截图 | 部分 | 只留四页面 + 两种异常态截图，未逐接口截图 | 验收阶段补齐 |

## 4 · 本轮不做什么

- 不把「249 passed」「35/35」「p95 48.1ms」之外的项写成通过；未执行的 N-01~N-06 一律标注。
- 不安装 / 升级依赖、不改 `.env`、不放宽 pytest 配置、不把权重或数据集入库（本轮环境由用户提供）。
- 不代写系统测试计划/总结与验收方案/报告（AI-R5）。
- 不修改业务代码修复 #217/#218：缺陷修复属蛋神的蛋 / 模型线，本分支只做测试与记录。

## 5 · 复现顺序

1. `python infra/setup_mysql.py --skip-start` → `cd backend && python -m uvicorn app.main:app`（另开终端）
2. `cd backend && python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov`
3. `cd backend && python scripts/integration_cases.py --json out.json` → 期望 35/35
4. `cd backend && python scripts/security_cases.py` → 期望 12/12；`python scripts/perf_loop.py` → 期望达标
5. `cd frontend && npm run dev` → 浏览器走查四页面与 `/commit/<不存在>`、未知路由
6. 空库场景：清空 `jit_test` 五表后以 `DB_NAME=jit_test` 另起实例（8001），核对 `code=0` 的空结果
