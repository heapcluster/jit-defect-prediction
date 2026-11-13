# neon 测试工作执行记录

> 本文件记录 neon 承接的集成 / 系统 / 验收测试**执行边界与证据**，不是测试报告。逐条用例见 [`../../integration_test/report.md`](../../integration_test/report.md)，系统侧执行见 [`system-test-run.md`](system-test-run.md)。
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
| 浏览器 | Chromium（Playwright），四页面 + 两种异常态截图入库 | `docs/test/system_test/execution_records/*.png` |
| 空库实例 | `jit_test` 清空五表后另起 8001 实例（无需 root 建库权限） | 见执行记录 §5 |
| 模型权重 | expert 8 个 `.pkl` 可用；semantic 语义表在 `data_model/data/`（默认路径不符，见 #217）；e2e 文本表缺失（#218） | 实测 `predict` 行为 |
| OpenSpec CLI | 1.11.0 | `openspec validate` 通过 |

2026-11-10 的旧结论（「本机无可用后端运行时，不安装环境」）在当时成立；本轮环境由用户提供，**未由我安装或下载任何依赖**，也未修改 `.env` / `pytest.ini` / git 配置。

## 2 · 已执行项与真实结果

| # | 项 | 命令 | 结果 | 证据 |
|---|---|---|---|---|
| E-01 | 端点清单静态核对 | 人工 + 静态检索 | 11/11 路由覆盖；发现 6 处文档偏差 + 2 处规格缺口 | [`../../integration_test/endpoint_inventory.md`](../../integration_test/endpoint_inventory.md) §2–§3 |
| E-02 | 前端契约测试 | `cd frontend && npm run test:unit` | 9 文件 / **59 用例通过**，26.41s | 终端输出 |
| E-03 | 口径冲突盘点 | 静态检索 | 6 处接口文档偏差 + 2 处规格缺口 | `../../integration_test/endpoint_inventory.md` §3 |
| E-04 | 用例设计 | AI 生成 + 人工复核 | 11 端点 × 四类场景（44 条设计，落地 35 条可执行用例） | `../../integration_test/endpoint_inventory.md` §4 |
| E-05 | OpenSpec 校验 | `openspec validate neon-test-baseline --strict` | `is valid`；活规格 `12 passed, 0 failed` | 终端输出 |
| E-06 | PR #216 审阅与合入 | GitHub API review + squash merge | APPROVE，合入 `afdee84`；3 项跟进缺陷 | [PR #216](https://github.com/heapcluster/jit-defect-prediction/pull/216) 的 Review 记录 |
| E-07 | 缺陷登记 | GitHub Issues | #217 语义表路径 / #218 e2e 文本表 / #219 契约部署 / #220 文档偏差 | [Issues #217–#220](https://github.com/heapcluster/jit-defect-prediction/issues) |
| E-08 | 合并后分支同步 | `git rebase main` | 分支与 `afdee84` 对齐 | git log |
| E-09 | 看板映射 | Bitable `tblLQAW6z5LB59nI` | 11 项任务入板（Sprint 2/3、负责人、状态、change、链接） | [项目看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) |
| E-10 | 周报 | `docs +create` | 《工作周报-20261113》已建（计划/总结/下周计划） | [周报](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa) |
| E-11 | 运行时契约导出 | `GET /openapi.json` | **11 个路径**，与文档/清单逐条一致；详情含 `model_name`；11/11 需 `x-api-key` | `../../integration_test/report.md` §1 |
| E-12 | 后端单测 + 覆盖率 | `python -m pytest -q --cov=app --cov-branch` | **249 passed / 0 failed**，28.2s；行覆盖 **85%**（分支 336，部分覆盖 40），HTML 报告已生成 | 终端输出（报告产物未入库） |
| E-13 | 集成用例 | `python scripts/integration_cases.py` | **35/35 通过**（含跨模块链路与并发） | [`../../integration_test/report.md`](../../integration_test/report.md) §3–§4 |
| E-14 | 安全用例 | `python scripts/security_cases.py` | **12/12 通过**（鉴权/畸形参数/模型不可用） | `backend/scripts/evidence/2026-11-12-security.md` |
| E-15 | 性能压测 | `python scripts/perf_loop.py` | p50 28.3ms / **p95 48.1ms** / p99 48.9ms / max 56.0ms，达标（<500ms） | `backend/scripts/evidence/2026-11-12-perf.md` |
| E-16 | 系统测试主线（浏览器） | Playwright 打开四页面 | 四页均渲染真实数据；截图 6 张入库 | `docs/test/system_test/execution_records/` |
| E-17 | 异常场景 | API + 第二实例 + 浏览器 | 空库 ✅、无效令牌 ✅、非法参数 ✅、详情不存在 ✅、未知路由 ✅；**缺权重 / 失败恢复未执行** | `system-test-run.md` §2 |
| E-18 | 25 模型在线矩阵 | 逐个 `POST /api/predict` | 补齐两张输入表后 **23/25 通过**；2 个 tabnet 因 CUDA 权重失败（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)）；三个关键数字与 PR #216 一致 | `backend/scripts/evidence/2026-11-12-online-25.md` |
| E-19 | 系统异常场景自动化 | `python scripts/system_exceptions.py --scenario all` | **13/13 通过**：缺权重、空库、失败恢复（自起/自停独立子进程，不移动权重、不影响 8000） | `backend/scripts/evidence/2026-11-12-system-exceptions.md` |
| E-20 | 验收用例生成 | `python scripts/acceptance_scenarios.py` | 抽取活规格 **124 条 Scenario** 生成现场对照清单；自动可判定子集 **10/10 通过** | `backend/scripts/evidence/2026-11-12-acceptance-checklist.md` |
| E-21 | 逐端点联调留痕 | `python scripts/linkage_capture.py` | 12 次真实请求（含 2 个异常）记录包络、字段形状与响应摘要；浏览器截图另见 `./` | `backend/scripts/evidence/2026-11-12-linkage.md` / `.json` |
| E-22 | 25 模型矩阵固化为门禁 | `python scripts/online_models_matrix.py` | 实跑 23/25 → 退出码 1（正确报警）；#222 修完目标 25/25 → 0 | `backend/scripts/online_models_matrix.py` |

## 3 · 仍未执行 / 未产出

| # | 项 | 状态 | 原因 | 解除条件 |
|---|---|---|---|---|
| N-01 | 「缺权重」异常 | **已执行** | `system_exceptions.py --scenario missing-weights`：用空 `MODEL_DIR` 起独立实例，不移动真实权重 | — |
| N-02 | 「失败恢复」（同步中断 / 服务强杀后恢复） | **已执行** | `system_exceptions.py --scenario failure-recovery`：强杀自建子进程后重启验证 | — |
| N-03 | 25 模型在线 25/25 | 未达成 | 2 个 tabnet 权重绑定 CUDA（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） | 蛋神修权重后跑 `online_models_matrix.py` |
| N-04 | 验收逐 Scenario（124 条） | 用例已生成 / 人工判定未做 | `acceptance_scenarios.py` 已生成全部 124 条对照清单并跑通 10 条自动子集；逐条「通过/失败/未执行」须现场判定 | 组织验收演示，neon 判定并签字 |
| N-05 | 系统测试计划/总结、验收方案/报告 | 未产出 | 文档由 **sober** 整理；**neon 只给实测内容、下结论、签字**（AI-R5 禁止 AI 代写/代签） | sober 依据 `./` 成文，neon 签字 |
| N-06 | 前端逐接口联调截图 | 部分 | 已有四页面 + 两种异常态截图；逐接口截图需浏览器自动化依赖（本机无 playwright/selenium，按要求不安装），HTTP 层联调留痕已由 `linkage_capture.py` 覆盖 | 具备浏览器自动化环境后补 |

## 4 · 本轮不做什么

- 不把未执行项写成通过；N-03~N-06 一律如实标注。
- 不安装 / 升级依赖、不改 `.env`、不放宽 pytest 配置、不把权重或数据集入库（本轮环境由用户提供）。
- 不代写正式测试文档、不代下结论、不代签字：文档归 sober，结论与签字归 neon（AI-R5）。
- 注（2026-11-13）：以上为 2026-11-12 当时的执行边界记录，按本文件「历史结论保留，不删改」的口径原样保留。项目方后续授权由 AI 依据实测证据代写四份测试文档（无人工签字），当前口径见 [`../../README.md`](../../overview.md) §2、§8。
- 不修改业务代码修复 #217 / #222：缺陷修复属蛋神的蛋 / 模型线，本分支只做测试代码与证据。

## 5 · 复现顺序

1. `python infra/setup_mysql.py --skip-start` → `cd backend && python -m uvicorn app.main:app`（另开终端）
2. `cd backend && python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov`
3. `cd backend && python scripts/integration_cases.py --json out.json` → 期望 35/35
4. `cd backend && python scripts/security_cases.py` → 期望 12/12；`python scripts/perf_loop.py` → 期望达标
5. `cd frontend && npm run dev` → 浏览器走查四页面与 `/commit/<不存在>`、未知路由
6. `python scripts/system_exceptions.py --scenario all` → 缺权重 / 空库 / 失败恢复 13/13
7. `python scripts/online_models_matrix.py` → 25 模型门禁（当前 23/25）
8. `python scripts/acceptance_scenarios.py` → 124 条 Scenario 对照清单 + 10 条自动子集
9. `python scripts/linkage_capture.py` → 12 次逐端点联调留痕
