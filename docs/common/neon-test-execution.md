# neon 测试工作执行记录（2026-11-10）

> 结论先行：本轮只完成**当前环境可完成**的部分 —— 环境能力核查、11 端点清单与用例设计、前端契约测试实跑、口径冲突盘点；**后端集成测试、系统测试、验收测试全部未执行**，原因见 §3。本文是执行记录，不是测试报告；未执行项一律写「未执行」，不得引用为通过证据。
>
> 分支：`test/neon-test-baseline` ｜ 基线提交（开分支时）：`21cd082`（`docs(todo): 补充 README 总览`）｜ 负责人：neon

## 1 · 环境能力核查（实查，非预置假设）

| 项 | 实查结果 | 命令 / 佐证 | 对测试的影响 |
|---|---|---|---|
| Node / npm | v24.18.0 / 11.16.0，`frontend/node_modules` 与 `vitest` 就绪 | `node -v`、`npm -v`、`Test-Path node_modules/.bin/vitest.cmd` | 前端测试可跑 |
| 系统 Python | `python` 指向 `WindowsApps` 占位程序，无输出（无真实解释器） | `(Get-Command python).Source` | 后端与 data_model 一律不可跑 |
| 备选解释器 A | `D:\workspace\env\miniconda3\python.exe` = 3.14.6，pytest 9.1.1，但无 `sqlalchemy` / `pandas` / `numpy`(部分) / `sklearn` / `pytest-cov` | 逐模块 `importlib.util.find_spec` | 起不了 FastAPI，pytest 收集即失败 |
| 备选解释器 B | `D:\workspace\env\moonlit_venv\Scripts\python.exe` = 3.14.6，有 fastapi 0.140.0 / httpx / dotenv，无 `sqlalchemy` / `pydantic_settings` / `pandas` / `sklearn` / `pytest-cov` | 同上 | 同上 |
| 后端依赖口径 | Dockerfile 固定 `python:3.12-slim` + `sqlalchemy==2.0.54`、`pymysql`、`sklearn`、`xgboost`、`lightgbm`、`torch`、`shap` | `backend/Dockerfile` | 现有两个解释器与运行时口径均不匹配，补齐需安装，本轮按要求不做 |
| MySQL | `MySQL80` 服务 Running，`127.0.0.1:3306` 可连 | `Get-Service MySQL80`、`Test-NetConnection` | 库在，但没有 Python MySQL 驱动与 ORM，无法建表、灌数、查询 |
| Docker | 无 `docker` 命令 | `Get-Command docker` | 无法用镜像补齐环境 |
| 模型权重 | expert 线 8 个 `.pkl` 在位（`data_model/pipelines/expert/models/`） | 目录列举 | 权重在，但缺 `sklearn`/`xgboost`/`lightgbm`，加载即失败 |
| 浏览器 | Playwright 可用 | 工具可用性 | 无后端时只能看前端错误态，不构成端到端证据 |
| OpenSpec CLI | 1.11.0 | `openspec --version` | 可对本次 change 做规范校验 |

**判定**：`backend/`、`data_model/` 的运行与测试在本机不可执行；不做任何环境安装、下载或配置修改（task 明令）。后端侧唯一可行路径是 CI（`.github/workflows/ci.yml` 起 `mysql:8.0` 服务、Python 3.12、`pytest --cov`），但 CI 结果必须由提交后流水线产出，本轮无法预先充当证据。

## 2 · 已执行项与真实结果

| # | 项 | 命令 | 结果 | 证据 |
|---|---|---|---|---|
| E-01 | 端点清单静态核对（`docs/api/*.md` ↔ `backend/app/api/*.py`） | 人工 + 静态检索 | **11/11 路由互相覆盖**，鉴权 11/11 需 `X-API-Key`；发现 6 处文档与代码不一致、3 处文档缺失 | [`endpoint-inventory.md`](endpoint-inventory.md) §2–§3 |
| E-02 | 前端契约测试实跑 | `cd frontend && npm run test:unit` | **9 个测试文件 / 59 条用例全部通过**，耗时 26.41s（2026-11-10） | 本次终端输出（见下文附注） |
| E-03 | 口径冲突盘点（文档 / 规格 vs 代码） | 静态检索 | 6 处接口文档偏差 + 2 处规格缺口（`backend/scripts/` 不存在、5 个空能力目录） | [`endpoint-inventory.md`](endpoint-inventory.md) §3 |
| E-04 | 用例设计（11 端点 × 四类场景 = 44 条） | AI 生成 + 人工待复核 | 44 条全部「未执行」 | [`endpoint-inventory.md`](endpoint-inventory.md) §4 |
| E-05 | OpenSpec 规范校验 | `openspec validate neon-test-baseline --strict`、`openspec validate --specs --strict` | 本次 change `is valid`；活规格 `12 passed, 0 failed` | 本次终端输出 |
| E-06 | PR #216 审阅与合入 | GitHub API：`POST /pulls/216/reviews`（APPROVE）、`PUT /pulls/216/merge`（squash） | 审阅通过并合入，合并提交 `afdee84`；审阅意见含 3 项跟进缺陷 | PR [#216](https://github.com/heapcluster/jit-defect-prediction/pull/216) 审阅记录；留痕见 [`pr-review-log.md`](pr-review-log.md) |
| E-07 | 缺陷登记 | GitHub Issues API | 登记 4 条：[#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)（语义表路径）、[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)（e2e 文本表）、[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)（契约/部署）、[#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)（D-01~D-06） | [`defect-records.md`](defect-records.md) |
| E-08 | 合并后分支同步 | `git rebase main`（main=`afdee84`） | 本分支 rebase 成功，清单已按 25 模型与 `model_name` 参数更新 | 本文件与 `endpoint-inventory.md` §2.1/§3 |
| E-09 | 项目看板映射（neon-5） | `lark-cli base +record-batch-create`（Bitable `SilBbJZFPaDct1slrIVcN2Nonsc` / `tblLQAW6z5LB59nI`） | 11 项任务逐条入板（Sprint 2/3、负责人、状态、OpenSpec change、关联链接），rev 51→52 | [项目看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) |
| E-10 | 本周周报（neon-5） | `lark-cli docs +create` | 新建《工作周报-20261113》，含本周计划/本周总结/下周计划；他人负责部分标「待填写」，不代填 | [工作周报-20261113](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa) |

E-02 附注：输出含 5 条 `[Vue warn]: Failed to resolve directive: loading`（`RiskList.spec.js`，Element Plus 指令未注册），属测试环境告警，不影响 59 条用例结果；不把告警算作通过证据之外的额外交付。

E-06 附注：PR 描述的 `backend 249 passed / frontend 59 passed / data_model 162 passed` **本轮无法复跑**（本机无后端运行时）；合入依据是静态审阅 + 既有 CI 口径，不代表这些数字已被本次验证。

## 3 · 未执行项与阻断原因（逐项，不得后续补写成通过）

| # | 计划动作 | 状态 | 阻断原因 | 解除条件 |
|---|---|---|---|---|
| N-01 | 取得运行时 `/openapi.json` 并与 `docs/api/` 逐字段比对 | 未执行 | 无可用 Python 后端运行时 | 具备 3.12 + 后端依赖的环境，或 CI 产物 |
| N-02 | `cd backend && python -m pytest -q`（含 `--cov=app --cov-branch`） | 未执行 | 同上；且缺 `pytest-cov` | 同上 |
| N-03 | 真实 MySQL 建 `jit_demo`/`jit_test` 并跑 `infra/setup_mysql.py` | 未执行 | 缺 `pymysql` + 后端依赖 | 同上（服务已在跑） |
| N-04 | 跨模块链路：同步 → 14 维特征 → 预测 → 落库 → 查询 | 未执行 | 需要 N-01~N-03 | 同 N-01 |
| N-05 | 并发场景（两个客户端同时 `POST /api/sync`） | 未执行 | 同 N-01 | 同 N-01 |
| N-06 | 系统测试主线：四页面端到端（风险列表 / 详情 / 趋势 / 模型性能） | 未执行 | 无后端，页面只能展示错误态 | 真实环境 + 浏览器 |
| N-07 | 系统测试 5 类异常：空库、无效令牌、非法参数、缺失权重、失败恢复 | 未执行 | 同 N-06（其中「无效令牌」断言需真实 HTTP 层） | 同 N-06 |
| N-08 | 非功能 ≥2 项实测（性能分位数 / 安全用例） | 未执行 | 无后端；且 `backend/scripts/perf_loop.py`、`security_cases.py` 在仓库中不存在 | 先补脚本 + 起服务 |
| N-09 | 验收测试逐 Scenario 对照 | 未执行 | 需浏览器演示；活规格 12 份 / 124 条 Scenario，其中 5 个能力目录为空 | 真实环境 + 人工组织演示 |
| N-10 | 系统测试计划 / 总结、验收方案 / 报告的正式撰写与签字 | 未产出 | 依 AI-R5 由 neon 本人撰写并签字，AI 不代写 | neon 在实跑后完成 |
| N-11 | 缺陷登记到 GitHub Issue / 飞书缺陷看板 | 已执行（GitHub 侧） | 4 条 Issue 已建（#217~#220）；飞书缺陷看板未建 | 待团队确认是否另建飞书缺陷表 |

## 4 · 本轮不做什么

- 不写入任何「通过」结论，不把静态清单、CI 历史绿灯、旧截图当作本次结果。
- 不新增无法执行的 Python 测试代码：本机连 `import app.main` 都做不到，提交未经收集验证的用例只会把失败风险推给 CI。
- 不安装 / 升级 Python、不放宽 `pytest.ini`、不改 `.env`、不把权重或数据集入库。
- 不代写系统测试计划 / 总结、验收方案 / 报告（AI-R5）。

## 5 · 后续可执行顺序（具备环境后）

1. `pip` 齐依赖（或直接用 `backend/Dockerfile` 镜像）→ 起后端 → 保存 `/openapi.json` → 与 `docs/api/` 比对，回填 [`endpoint-inventory.md`](endpoint-inventory.md) §2 的运行时列。
2. `infra/setup_mysql.py` 建库 → `pytest -q --cov=app --cov-branch --cov-report=html` → 报告按提交 SHA 归档。
3. 按 §4 用例表逐条实跑集成用例，回填 §4 的「状态」与 `integration-log.md`。
4. 补 `backend/scripts/perf_loop.py` / `security_cases.py` 后跑非功能，产出 `backend/scripts/evidence/<日期>-<主题>.md`。
5. 组织浏览器演示，人工写系统测试计划 / 总结与验收方案 / 报告并签字。
6. 把 §3 的 D-01~D-06 逐条提到 GitHub Issue，与本 change 互相关联。
