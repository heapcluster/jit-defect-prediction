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
- [x] 1.5 运行时 `/openapi.json` 导出并与清单逐端点比对 — 交付：11 个路径与清单逐条一致，详情含 `model_name`，11/11 需 `x-api-key`；验收：`integration-report.md` §1；负责人：neon。
- [x] 1.6 按用例表实跑并回填状态 — 交付：`backend/scripts/integration_cases.py`（35 条）+ `docs/common/integration-report.md` + `integration-log.md` 实测行；验收：35/35 通过、接口覆盖 11/11；负责人：neon。

## 2 · 系统测试

- [x] 2.1 准备真实环境（MySQL 建库 + 后端依赖 + 模型权重 + 浏览器） — 交付：conda `jit-defect-prediction` + `infra/setup_mysql.py --skip-start` + `uvicorn` + `vite`；验收：`health=ok, db=up, models_loaded=8`；负责人：neon（环境由用户提供）。
- [x] 2.2 主线：同步真实提交 → 14 维特征 → 模型预测 → 四页展示 — 交付：25,285→25,307 同步、`et_v1` 0.97637、四页截图；验收：`evidence/2026-11-12/system-test-run.md` §1；负责人：neon。
- [x] 2.3 异常 5 类 — 交付：空库 ✅ / 无效令牌 ✅ / 非法参数 ✅ / 详情不存在与未知路由 ✅；**缺权重、失败恢复未执行**；验收：同文件 §2；负责人：neon。
- [x] 2.4 非功能 ≥2 项实测 — 交付：新增 `backend/scripts/perf_loop.py`、`security_cases.py` 与两份 evidence；性能 p95=48.1ms 达标、安全 12/12；验收：`backend/scripts/evidence/2026-11-12-*.md`；负责人：neon。
- [ ] 2.5 系统测试计划 / 总结（人工撰写 + 签字） — **未产出：AI-R5 要求 neon 本人依据 `evidence/2026-11-12/` 撰写，本 change 不代写**。

## 3 · 验收测试

- [ ] 3.1 逐 Scenario 对照（活规格 12 份 / 124 条 Scenario） — **未执行：需真实环境演示；`openspec/specs/` 下 `feedback`、`observability`、`ops`、`quality`、`ui` 五个能力目录为空目录，无 `spec.md` 可对照**。
- [ ] 3.2 验收方案 / 报告（人工撰写 + 签字） — **未产出：同 AI-R5 边界**。

## 4 · 过程记录与缺陷

- [x] 4.1 执行边界与未执行清单归档 — 交付：`docs/common/neon-test-execution.md`；验收：环境核查逐项有命令与结果，未执行项有阻断原因与解除条件；负责人：neon。
- [x] 4.2 联调证据索引口径说明 — 交付：`docs/common/integration-log.md` 追加说明段；验收：不出现「通过」字样，未执行原因可追溯；负责人：neon。
- [x] 4.3 缺陷登记到 GitHub Issue — 交付：[#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)（语义表默认路径）、[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)（e2e 文本表）、[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)（契约/部署）、[#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)（D-01~D-06）；验收：`docs/common/defect-records.md` 有链接与关联提交；负责人：neon。
- [x] 4.4 PR 审阅留痕 — 交付：`docs/common/pr-review-log.md`；验收：PR #216 的审阅结论、跟进缺陷与合并提交号可反查；负责人：neon。
- [x] 4.5 回飞书看板映射 11 项任务并写本周周报 — 交付：[看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) 11 条新记录（Sprint 2/3 + 负责人 + 状态 + change）、[工作周报-20261113](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa)；验收：任务可对应负责人与状态，周报含三要素；负责人：neon。

## 测试与验证

> 规范校验（2026-11-10 实跑）：`openspec validate neon-test-baseline --strict` → `is valid`；`openspec validate --specs --strict` → 12 passed, 0 failed。

### 1. 单元测试

- 覆盖对象：本 change 不改业务代码；新增 `backend/scripts/*.py` 属测试脚本，不进 pytest 收集（`pytest.ini` 的 `testpaths=tests`）。
- 后端基线（2026-11-12 实跑）：`cd backend && python -m pytest -q --cov=app --cov-branch` → **249 passed / 0 failed**，28.2s，行覆盖 **85%**（分支 336、部分 40）。
- 前端基线：`cd frontend && npm run test:unit` → 9 文件 / **59 用例通过**，26.41s。

### 2. 集成测试

- 链路与场景：`docs/common/endpoint-inventory.md` §4（11 端点四类）；落地 35 条可执行用例（健康探针的「非法参数」不适用）。
- 执行命令：`cd backend && python scripts/integration_cases.py --json out.json`（服务需先起）。
- 实测结果：**35/35 通过**，接口覆盖 **11/11**；跨模块链路 1 条（预测 0.97637 = 详情 = 列表）、并发 1 条（200/500 不串扰）。
- 证据路径：`docs/common/integration-report.md`（逐条结果）、`docs/common/integration-log.md`（索引）、`docs/common/evidence/2026-11-12/`（页面截图）。

### 3. 验收测试

- 对照对象：`openspec/specs/**/spec.md` 的 124 条 Scenario。
- 已覆盖：四页面主干 + 「提交不存在」「未知路由」两种异常态（浏览器实拍）。
- 未执行：逐 Scenario 全量对照（124 条）与验收方案/报告签字；空能力目录 5 个仍需补规格。
- 执行人：neon。

### 4. 非功能验证

- 性能：**已实测**。`python scripts/perf_loop.py`（100 次）→ p50 28.3ms / p95 48.1ms / p99 48.9ms / max 56.0ms，目标 p95<500ms **达标**；证据 `backend/scripts/evidence/2026-11-12-perf.md`。
- 安全：**已实测**。`python scripts/security_cases.py` → 12/12（鉴权 6 项、畸形参数 4 项、模型不可用 1 项、未知模型 1 项），响应无堆栈/SQL/路径泄漏；证据 `backend/scripts/evidence/2026-11-12-security.md`。
- 可靠性：未执行（同步中断 / 服务强杀后的恢复路径未构造）。
- 易用性：部分实测。四页面与两种异常态截图见 `evidence/2026-11-12/`，未做多浏览器与无障碍专项。

### 5. 已知缺口与后续计划

| 缺口 | 影响 | 责任人 | 完成条件 |
|---|---|---|---|
| 「缺权重」「失败恢复」两类异常未执行 | 异常覆盖不完整 | neon | 单独测试窗口执行，记录写入 `system-test-run.md` |
| e2e 在线路径不可用（`commit_text.csv` 缺失） | 25 模型口径无法完全验证 | 蛋神的蛋（[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)） | 补产物与生成脚本后重跑 |
| 逐 124 条 Scenario 未对照 | 验收测试未完成 | neon | 组织演示并逐条记录 |
| `openspec/specs/` 五个空能力目录 | 部分能力无规格可对照 | sober | 补 `spec.md` 或删除并说明 |
| 系统测试计划/总结、验收方案/报告未产出 | 无签字版交付物 | neon（本人撰写） | 依据 `evidence/2026-11-12/` 撰写并签字 |
| `nfr-evidence` 规格与实际契约冲突（模型缺失应为 50000，实现为 40001） | 规格侧失真 | sober / 后端 | 规格订正或后端对齐，二者择一 |
