# neon-test-baseline — 测试基线取证与执行边界

## Why

课程测试考核要求四类测试都有**当前提交**的真实证据（见 `docs/common/test-assessment-guide.md`），但仓库里集成 / 系统 / 验收三条线的执行记录仍停留在模板占位：`docs/common/integration-log.md` 五条场景全是「待填 / 未执行」，系统测试计划与验收报告未产出，接口清单也没有与代码逐条对齐的版本。

本轮（2026-11-10，neon 承接集成 / 系统 / 验收测试）先解决**取证前提**问题：把「测什么、怎么测、哪些测不了」写清楚，避免后续用清单或计划冒充通过结果；同时把已经能执行的部分（前端契约测试、端点静态核对）落成可复现证据。

## What Changes

- 新增 `docs/common/endpoint-inventory.md`：11 个真实端点的参数、错误码、成功字段与四类场景用例设计，并单列 6 处「文档与代码不一致」和 2 处规格缺口。
- 新增 `docs/common/neon-test-execution.md`：本机环境能力核查结果、已执行项真实结果、未执行项与阻断原因、解除条件。
- 新增 `docs/common/ai-prompts/neon-integration-cases.md`：AI 生成用例的 Prompt 归档与人工复核状态（AI-R1 / AI-R2）。
- 新增活规格能力 `test-evidence`：把「清单来源、执行记录、不得以文档冒充实测」固化为可校验的 Requirement。
- 更新 `docs/common/integration-log.md`：注明本轮未执行及原因，避免旧占位被误读为已执行。

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
- 代码：**零改动**。不触及 `backend/`、`frontend/`、`data_model/`、`infra/`，因此不影响 CI 的构建与既有测试口径。
- 后续依赖：真实取证需具备 Python 3.12 + 后端依赖 + MySQL 的环境（本机 MySQL 已在跑但缺驱动），或由 CI 产出后端测试结果。
