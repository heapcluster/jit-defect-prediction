# 四类测试交付说明与记录表

> 状态：组织与记录格式；**不是测试通过报告**。实际结果、截图、覆盖率和签名必须对应同一提交和真实运行。课程细则见 [`test-assessment-guide.md`](test-assessment-guide.md)，当前功能与接口入口见 [`../README.md`](../README.md)。

## 交付责任与顺序

| 顺序 | 测试类型 | 实施与结果提供 | 文档汇总 / 人工审核 | 必交证据 |
|---|---|---|---|---|
| 1 | 单元 | `蛋神的蛋-2` 统筹；各模块代码作者提供本线用例与运行结果 | `sober-1` 整理说明；用例作者复核 AI 来源和核心断言 | 测试代码、命令与输出、当前提交的覆盖率 HTML 和截图、来源与 Prompt 记录（如使用 AI） |
| 2 | 集成 | `neon-1` 统筹；前后端双方联调，模型负责人提供权重和特征口径 | `sober-1` 整理接口报告；双方确认请求/响应一致 | 按运行时 `/openapi.json` 列端点、四类场景结果、跨模块链路、截图/日志及缺陷链接 |
| 3 | 系统 | `neon-2` 组织真实环境与完整业务流程，各模块负责人配合定位 | **neon 人工编写计划、总结并签字**；`sober-1` 只整理证据与检查缺项 | 环境、执行记录、端到端与非功能结果、缺陷和复测证据 |
| 4 | 验收 | `neon-3` 组织用户视角演示，产品与各模块负责人确认需求 | **neon 人工编写验收方案、报告并签字**；`sober-1` 只整理证据与检查缺项 | OpenSpec Scenario 对照、实际演示记录、通过/失败/未执行及后续处理 |

后一步引用前一步的同一提交 SHA、环境和证据链接；不能拿旧版本的绿灯或截图填本次结果。提交测试 PR 时附上本记录表对应的已填写行。测试用例来源须逐条标注 `[手写]`、`[AI生成]` 或 `[AI生成-人工修改]`；来源无法确认时写“待核”，由作者确认。AI 生成的核心业务断言须人工逐条复核。

上表任务编号与 [`todo/README.md`](../../todo/README.md) 的 2026-11-10 分工一致；具体验收项见 [`todo/sober-1-测试文档.md`](../../todo/sober-1-测试文档.md)、[`todo/neon-1-测试-集成测试.md`](../../todo/neon-1-测试-集成测试.md)、[`todo/neon-2-测试-系统测试.md`](../../todo/neon-2-测试-系统测试.md)、[`todo/neon-3-测试-验收测试.md`](../../todo/neon-3-测试-验收测试.md)。实际进度、截止时间和责任调整以飞书看板为准。

## 单元测试说明记录格式

本表由各线作者在实跑后填写，可复制到各线的测试说明或 PR 描述；`sober-hub` 只汇总真实输出。

| 字段 | 填写要求 |
|---|---|
| 测试提交 / 环境 | SHA、Python/Node 版本、隔离测试库或 Mock 说明 |
| 测试范围 | 核心函数或模块、对应 OpenSpec Requirement / Scenario |
| 用例设计 | 正常、边界、异常；输入、预期和核心业务断言；外部依赖如何隔离 |
| 执行证据 | 运行命令、用例通过/失败/跳过数、失败复现步骤 |
| 覆盖率 | 行与分支覆盖率、HTML 产物或 CI artifact 链接、截图；注明未覆盖关键路径 |
| AI 审核 | 每条来源标签、Prompt 路径（如有）、人工复核人及修改点 |

代码入口：[`backend/tests/`](../../backend/tests/)、[`data_model/tests/`](../../data_model/tests/)、[`frontend/tests/`](../../frontend/tests/)。后端测试需要隔离 MySQL 测试库；覆盖率报告应与本次 SHA 一致。课程的 80% 行覆盖率是评分依据，当前 CI 先只归档报告，不把该值当自动合入门槛。

## 集成接口测试报告记录格式

接口清单以本次运行的 `/openapi.json` 为准，契约按 [`../api/`](../api/) 的对应页面核对；不要把课程截图中的通用 `/api/upload`、`/api/history` 当成本项目接口。

| 端点 / 场景 | 来源标签 | 输入与前置 | 预期状态码、字段、业务断言 | 实际结果 / 截图或日志 | 执行人 / 缺陷链接 |
|---|---|---|---|---|---|
| `<METHOD /api/path>` 正常 | 待填写 | 待填写 | 待填写 | 待实测 | 待填写 |
| 同端点缺参 | 待填写 | 待填写 | 待填写 | 待实测 | 待填写 |
| 同端点非法参数 | 待填写 | 待填写 | 待填写 | 待实测 | 待填写 |
| 同端点边界值 | 待填写 | 待填写 | 待填写 | 待实测 | 待填写 |

跨模块至少登记一次“特征抽取 → 模型推理 → 落库 → API 查询 → 前端展示”的真实链路，并记录一个并发场景。双方核对 `X-API-Key`、错误信封、字段类型、可空值和模型选择。浏览器与 API 的实际执行结果另附截图/录屏；待执行不能写成通过。

## 系统与验收：人工编写清单

以下只列交接时必须提供的材料，**不代写系统测试计划、系统测试总结、验收方案或验收报告**。这些正式文件应由 `neon` 根据实际测试亲自编写、判断并签名，`sober-hub` 仅检查链接、版本和缺项。

- 系统计划：目标、范围、环境与数据、用例和责任人、非功能测量方法、进入/退出条件、风险与回滚。
- 系统总结：实际执行日期和 SHA、通过/失败/未执行数、端到端证据、性能/安全/可靠性/易用性结果、缺陷及复测、人工结论与签名。
- 验收方案：用户角色与场景、对应 OpenSpec Requirement / Scenario、现场步骤、明确的通过标准、参与者和签名方式。
- 验收报告：逐场景实际结果、截图或录屏、未满足项、处置决定、负责人签名与日期。

现有联调证据入口为 [`integration-log.md`](integration-log.md)，缺陷入口为 [`defect-records.md`](defect-records.md)。二者都是索引，不替代本次实测和人工验收结论。

## 2026-11-13 测试基线交接：PR #221

> 性质：`sober-1` 的**测试文档与证据索引**，不是系统测试总结或验收报告。以下仅整理 [PR #221](https://github.com/heapcluster/jit-defect-prediction/pull/221) 在提交 `0c759252b7a614a9759a946d8819684a9abfa357` 中提供的材料；其测试对象据作者记录为 `main@afdee84`。PR 更新后须按新 SHA 复核。执行数值注明“作者记录”的，不能仅凭本文认定已独立复测。

### 任务与 OpenSpec 对照

| 任务 | 应交材料 | PR #221 的证据入口 | 当前可确认的边界 |
|---|---|---|---|
| `蛋神的蛋-2` 单元 | 正常/边界/异常用例、覆盖率 HTML 与截图、AI 来源 | [`backend/tests/`](../../backend/tests/)、[`frontend/tests/`](../../frontend/tests/)；本次 [CI 后端检查](https://github.com/heapcluster/jit-defect-prediction/actions/runs/43249776845) | 作者记录后端 249 passed、行覆盖 85%；前端 59 passed。CI 验证了后端步骤通过，前端数字及截图仍以对应执行输出为准。 |
| `neon-1` 集成 | 运行时端点清单、四类场景、联调与并发证据 | PR #221 的 `docs/common/endpoint-inventory.md`、`integration-report.md`、`integration-log.md` | 作者记录 11/11 端点、35/35 用例；并发用例目前允许超时判 PASS，需复核该条的有效性。 |
| `neon-2` 系统 | 真实环境主线、五类异常、至少两项非功能；本人写计划/总结并签字 | PR #221 的 `docs/common/evidence/2026-11-12/system-test-run.md` 与 `backend/scripts/evidence/` | 有执行记录与截图；“同步中强杀恢复”脚本尚未在杀进程前断言 `running=true`。正式计划、总结和签字未交。 |
| `neon-3` 验收 | 逐条 Scenario 的现场结果；本人写方案/报告并签字 | PR #221 的 `backend/scripts/evidence/2026-11-12-acceptance-checklist.md` | 已生成 124 条对照行，作者记录 10 条自动子集通过；124 条现场判定与签字仍未完成。 |
| `sober-1` 文档 | 单元说明、接口报告、系统/验收材料检查、联调索引、OpenSpec 证据映射 | 本文及上列源文件 | 本文只整理与核对，不能把“材料齐备”勾成“验收通过”。 |

PR #221 提议的 [`test-evidence` 规格](https://github.com/heapcluster/jit-defect-prediction/blob/0c759252b7a614a9759a946d8819684a9abfa357/openspec/changes/neon-test-baseline/specs/test-evidence/spec.md) 有三项 Requirement：端点清单来源与偏差登记、执行记录区分已执行与未执行、人工签署文档不由 AI 代写。前两项以运行时 `/openapi.json`、逐项命令/日期/结果和缺陷链接核对；第三项以 neon 的正式签字文件核对。这里的十条自动检查不替代 124 条 Scenario 的人工结论。

### 测试与验证

#### 1. 单元测试

- 范围：后端 `backend/tests/`、前端 `frontend/tests/`；各线作者应补“核心函数 × 正常/边界/异常”对应表。模型线 `data_model/tests/` 的本次结果尚未从 #221 取得。
- 复现：在 `backend/` 运行 `python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov`；在 `frontend/` 运行 `npm run test:unit -- --coverage`。数据库和模型权重按各自测试前置准备。
- 结果：后端 **249 passed / 行覆盖 85%**、前端 **59 passed** 均为 PR 作者记录；本次 PR 的 CI 后端步骤通过。前端覆盖率、分支覆盖率数值及可点开的 HTML/PDF 截图应由对应负责人另附，未附前不写“覆盖率材料齐全”。
- AI 来源：测试代码旁已有来源标签；完整 Prompt 与人工复核结果仍按 [`test-assessment-guide.md`](test-assessment-guide.md) 的 AI-R1/AI-R2 逐条核对。

#### 2. 集成测试

- 链路：11 个运行时端点的正常、缺参/缺鉴权、非法参数、边界场景；另含“预测→落库→详情/列表”及并发同步。执行入口为 PR #221 的 `backend/scripts/integration_cases.py`，须先启动后端与测试库。
- 作者记录：35/35、端点 11/11。逐条输入、预期与实际结果以该 PR 的 `integration-report.md` 为准；浏览器截图与 HTTP 记录分别见该 PR 的 `docs/common/evidence/2026-11-12/` 与 `backend/scripts/evidence/`。
- 待复核：T-IN-21 把 `ReadTimeout` 算作可通过，不能证明服务正确拒绝并发请求；应核对 500/50000 响应及同步结束状态，再确认该用例结论。

#### 3. 验收测试

- 对照：PR #221 的脚本从 `openspec/specs/` 生成 124 条 Scenario 清单；10 条自动子集由作者记录为通过，**逐条现场判定仍未执行**。
- 现场记录由 `neon-3` 填“通过/失败/未执行”、实际结果、截图或缺陷编号。系统测试计划/总结和验收方案/报告须 neon 本人撰写、下结论并签字；本节不构成这些正式文件。

#### 4. 非功能验证

- 作者记录的性能结果为 100 次预测 p95 48.1ms（目标 <500ms），安全用例 12/12；原始命令、环境与输出在 PR #221 的 `backend/scripts/evidence/2026-11-12-perf.md`、`2026-11-12-security.md`。
- 系统异常脚本记录 13/13，但“失败恢复”应先证明强杀时同步仍在运行。25 模型在线矩阵记录 23/25，两个 TabNet 失败见 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)；不得把模型清单有 25 项写成 25 项都可用。

#### 5. 已知缺口与后续计划

| 缺口 | 责任人 | 补齐条件 |
|---|---|---|
| 并发和失败恢复用例的前置/断言不足 | neon（`neon-1/2`） | 修正脚本并按新提交重跑；保留失败或未执行结果。 |
| 单元覆盖率截图、分支数值与模型线当次结果 | 蛋神的蛋（`蛋神的蛋-2`），sober 汇总 | 提供对应 SHA 的 HTML/PDF 截图、命令和结果。 |
| 124 条 Scenario 现场判定、系统和验收正式文件 | neon（`neon-2/3`） | 实测记录逐条可追溯，正式文件本人撰写并签字。 |
| 两个 TabNet 在线模型失败 | 模型/后端负责人（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） | 修复后重新跑 25 模型矩阵并留证。 |

`openspec/changes/neon-test-baseline/tasks.md` 的勾选只代表相应**子任务及证据已完成**，不能替代上表的系统/验收完成判断。PR 合入后，`sober-1` 再以合入 SHA 核对链接、数据和状态。
