# neon-test-baseline — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/test-evidence/spec.md`
> 负责人：neon（集成 / 系统 / 验收测试） ｜ 创建：2026-11-10
> 关联需求：`todo/neon-1-测试-集成测试.md`、`todo/neon-2-测试-系统测试.md`、`todo/neon-3-测试-验收测试.md`；飞书「想到什么取什么」→ 本周计划 N-2 / N-3 / N-4
> 状态：实现中（文档与清单已交付；实测项因环境阻断未执行，不得视为验收通过）

## 1 · 集成测试取证前提

- [x] 1.1 端点清单静态核对 — 交付：`docs/common/endpoint-inventory.md`；验收：11/11 路由与 `docs/api/README.md`「十一个路由」一致，每个端点给出鉴权、参数边界、成功字段与业务码，附文件级证据；负责人：neon。
- [x] 1.2 四类场景用例设计（11 端点 × 正常/缺参/非法/边界） — 交付：`docs/common/endpoint-inventory.md` §4；验收：每类给出具体输入与预期码/断言，状态列统一「未执行」；负责人：neon。
- [x] 1.3 文档与代码偏差登记 — 交付：同文件 §3（D-01~D-06 + 2 处规格缺口）；验收：每条有文档位置、代码位置、对断言的影响；负责人：neon。
- [x] 1.4 AI 用例 Prompt 归档与来源标注 — 交付：`docs/common/ai-prompts/neon-integration-cases.md`；验收：含工具、模型、日期、原始提示词、人工复核状态（未审阅）；负责人：neon。
- [ ] 1.5 运行时 `/openapi.json` 导出并与清单逐端点比对 — 交给：具备后端运行环境者（CI 或本地补齐依赖后由 neon 执行）；输入：`docs/api/*.md`、`backend/app/api/*.py`；输出：§2 回填后的清单；**未执行：本机无可用后端运行时**。
- [ ] 1.6 按 §4 用例表实跑 44 条并回填状态 — 输入：可访问的服务 + `X-API-Key`；输出：`docs/common/integration-log.md` 逐条结果与截图；**未执行：同 1.5**。

## 2 · 系统测试

- [ ] 2.1 准备真实环境（MySQL 建库 + 后端依赖 + 模型权重 + 浏览器） — **未执行：MySQL80 服务在跑但缺 `pymysql` 与后端依赖，且不得安装环境**。
- [ ] 2.2 主线：同步真实提交 → 14 维特征 → 模型预测 → 四页展示 — **未执行：依赖 2.1**。
- [ ] 2.3 异常 5 类：空库 / 无效令牌 / 非法参数 / 缺失权重 / 失败恢复 — **未执行：依赖 2.1**。
- [ ] 2.4 非功能 ≥2 项实测（性能分位数、安全用例） — **未执行：依赖 2.1；且 `backend/scripts/perf_loop.py`、`backend/scripts/security_cases.py` 在仓库中不存在，需另行补齐**。
- [ ] 2.5 系统测试计划 / 总结（人工撰写 + 签字） — **未产出：AI-R5 要求 neon 本人实跑后撰写，本 change 不代写**。

## 3 · 验收测试

- [ ] 3.1 逐 Scenario 对照（活规格 12 份 / 124 条 Scenario） — **未执行：需真实环境演示；`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个能力目录为空目录，无 `spec.md` 可对照**。
- [ ] 3.2 验收方案 / 报告（人工撰写 + 签字） — **未产出：同 AI-R5 边界**。

## 4 · 过程记录与缺陷

- [x] 4.1 执行边界与未执行清单归档 — 交付：`docs/common/neon-test-execution.md`；验收：环境核查逐项有命令与结果，未执行项有阻断原因与解除条件；负责人：neon。
- [x] 4.2 联调证据索引口径说明 — 交付：`docs/common/integration-log.md` 追加说明段；验收：不出现「通过」字样，未执行原因可追溯；负责人：neon。
- [ ] 4.3 D-01~D-06 逐条登记 GitHub Issue / 飞书缺陷看板并回填链接 — **未执行：需外部平台写权限与外发确认，本轮仅登记候选**。
- [ ] 4.4 回飞书看板更新 N-2 / N-3 / N-4 状态 — **未执行：状态以负责人在看板的更新为准，仓库侧不代填**。

## 测试与验证

> 规范校验（2026-11-10 实跑）：`openspec validate neon-test-baseline --strict` → `is valid`；`openspec validate --specs --strict` → 12 passed, 0 failed。

### 1. 单元测试

- 覆盖对象：本 change 不含代码改动，无新增单测对象。
- 参考基线：`frontend/tests/`（9 个文件）在 2026-11-10 实跑 `npm run test:unit`，结果 9 个文件 / 59 条用例全部通过，耗时 26.41s；该结果属基线记录，不是本 change 新增用例。
- 后端：`cd backend && python -m pytest -q` **未执行**——本机无可用 Python + 后端依赖（详见 `docs/common/neon-test-execution.md` §1）。

### 2. 集成测试

- 链路与场景：见 `docs/common/endpoint-inventory.md` §4（44 条）与 §5（跨模块链路 + 并发场景各一条）。
- 执行命令：未执行。计划命令为 `cd backend && python -m pytest -q`（CI 口径 `--cov=app --cov-branch`）。
- 实测结果：0/44；接口覆盖率按实测计 0/11，静态清单 11/11 仅证明分母完整。
- 证据路径：无 HTTP 响应截图；静态核对证据在清单 §2–§3。

### 3. 验收测试

- 对照对象：`openspec/specs/**/spec.md` 的 124 条 Scenario。
- 结果：全部未执行（缺真实环境）；空能力目录 5 个需先补规格再对照。
- 执行人：neon（待环境具备后现场执行并签字）。

### 4. 非功能验证

- 性能：未执行。需要 `POST /api/predict` 可达与分位数脚本（仓库缺失）。
- 安全：未执行。可静态确认的部分已记入清单 §1（鉴权 11/11、`/static/**` 同鉴权、令牌未配置时 fail closed），静态确认**不等于**实测通过。
- 可靠性：未执行。失败恢复场景依赖真实服务。
- 易用性：未执行。需浏览器演示。

### 5. 已知缺口与后续计划

| 缺口 | 影响 | 责任人 | 完成条件 |
|---|---|---|---|
| 后端运行时不可用（无 Python 3.12 + `sqlalchemy`/`pymysql`/`sklearn` 等） | 集成 / 系统测试全部无法执行 | neon | 补齐环境或改由 CI 产出，且不引入仓库级环境变更 |
| `/openapi.json` 未取得 | 清单为静态来源，可能与运行时漂移 | neon | 环境就绪后第一步导出并回填 |
| `backend/scripts/` 缺失（`perf_loop.py`、`security_cases.py`） | 非功能两项无执行入口 | neon → 需另提 change | 补齐脚本并能对运行中服务复跑 |
| `openspec/specs/` 五个空能力目录 | 验收无对应 Scenario 可对照 | sober（规格规范性） | 补 `spec.md` 或删除空目录并说明 |
| D-01~D-06 未登记 Issue | 缺陷无对外可追踪链接 | neon | 授权后逐条建 Issue 并回填 |
| 系统测试计划/总结、验收方案/报告未产出 | 系统 / 验收测试无正式交付物 | neon（本人撰写） | 实跑后人工撰写并签字 |
