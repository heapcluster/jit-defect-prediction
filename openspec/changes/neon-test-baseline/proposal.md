# neon-test-baseline — 测试基线取证与执行边界

## Why

课程测试考核要求四类测试都有**当前提交**的真实证据（见 `docs/common/test-assessment-guide.md`），但仓库里集成 / 系统 / 验收三条线的执行记录仍停留在模板占位：`docs/common/integration-log.md` 五条场景全是「待填 / 未执行」，系统测试计划与验收报告未产出，接口清单也没有与代码逐条对齐的版本。

本轮（2026-11-10，neon 承接集成 / 系统 / 验收测试）先解决**取证前提**问题：把「测什么、怎么测、哪些测不了」写清楚，避免后续用清单或计划冒充通过结果；同时把已经能执行的部分（前端契约测试、端点静态核对）落成可复现证据。

## What Changes

- 新增 `docs/common/endpoint-inventory.md`：11 个真实端点的参数、错误码、成功字段与四类场景用例设计，并单列 6 处「文档与代码不一致」和 2 处规格缺口。
- 新增 `docs/common/neon-test-execution.md`：本机环境能力核查结果、已执行项真实结果、未执行项与阻断原因、解除条件。
- 新增 `docs/common/ai-prompts/neon-integration-cases.md`：AI 生成用例的 Prompt 归档与人工复核状态（AI-R1 / AI-R2）。
- 新增活规格能力 `test-evidence`：把「清单来源、执行记录、不得以文档冒充实测」固化为可校验的 Requirement。
- 更新 `docs/common/integration-log.md`：登记 2026-11-12 的实测结果与环境；未执行项（缺权重、失败恢复）单独标注。
- 新增三个可复跑脚本（**不改业务代码**）：`backend/scripts/integration_cases.py`（11 端点四类场景 35 条）、`perf_loop.py`（100 次预测分位数，对应 `nfr-evidence` 性能要求）、`security_cases.py`（鉴权/畸形参数/模型不可用，对应安全要求），并产出 `backend/scripts/evidence/2026-11-12-*.md`。
- 新增 `docs/common/integration-report.md`（35 条逐条结果）与 `docs/common/evidence/2026-11-12/`（四页面 + 两种异常态截图、系统测试执行记录）。

## 不做什么

- 不安装 / 升级 Python、不放开 `pytest.ini`、不改 `backend/.env`、不下载数据集或权重（本机缺后端运行时，安装属任务明令禁止的动作）。
- 不新增当前环境无法收集的后端 pytest 用例：本机连 `import app.main` 都无法完成，提交未经收集验证的用例只会把失败推给 CI。
- 不代写系统测试计划 / 总结、验收方案 / 报告（AI-R5），也不在飞书看板或 GitHub Issue 上补造状态。
- 不直接修 `docs/api/` 的 6 处偏差：改契约需另行评审并将影响前端断言，本轮只登记候选项。

## Capabilities

- `test-evidence`（新增）：测试清单来源、执行记录与执行边界的记录规则。
- 关联但本轮不改动：`nfr-evidence`（非功能脚本缺失，另立 change 处理）、`query-api` / `predict-api` / `ui`（偏差项待裁定）。

## Impact

- 文档：`docs/common/` 新增 3 份、修改 1 份；`docs/README.md` 导航补 2 行。
- OpenSpec：新增 `changes/neon-test-baseline/`，并在 `changes/README.md` 活跃 change 表登记。
- 代码：**业务代码零改动**。仅在 `backend/scripts/` 新增三个测试脚本，不进 `pytest` 收集（`testpaths=tests`），不改变接口行为；`backend/tests`、`frontend/src`、`data_model/` 均未触碰。CI 会因 `backend/` 路径被判为需跑后端测试，现有 249 条用例全部通过（本地实测）。
- 后续依赖：`缺权重`、`失败恢复` 两类异常仍未执行；系统测试计划/总结、验收方案/报告待 neon 本人撰写签字；e2e 在线路径待 #218 修复。
