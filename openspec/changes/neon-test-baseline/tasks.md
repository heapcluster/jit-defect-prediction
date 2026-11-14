# neon-test-baseline — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/test-evidence/spec.md`
> 负责人：neon（集成 / 系统 / 验收测试） ｜ 创建：2026-11-10
> 关联需求：`todo/neon-1-测试-集成测试.md`、`todo/neon-2-测试-系统测试.md`、`todo/neon-3-测试-验收测试.md`；飞书「想到什么取什么」→ 本周计划 N-2 / N-3 / N-4
> 状态：待验收（旧实测记录已迁入 `docs/test/`；现场逐条判定、人工签字和部分证据仍未完成）

## 1 · 集成测试取证前提

- [x] 1.1 端点清单静态核对 — 交付：`docs/test/integration_test/endpoint_inventory.md`；验收：11/11 路由与 `docs/api/README.md`「十一个路由」一致，每个端点给出鉴权、参数边界、成功字段与业务码，附文件级证据；负责人：neon。
- [x] 1.2 四类场景用例设计（11 端点 × 正常/缺参/非法/边界） — 交付：`docs/test/integration_test/endpoint_inventory.md` §4；验收：每类给出具体输入与预期码/断言，状态列统一「未执行」；负责人：neon。
- [x] 1.3 文档与代码偏差登记 — 交付：同文件 §3（D-01~D-06 + 2 处规格缺口）；验收：每条有文档位置、代码位置、对断言的影响；负责人：neon。
- [x] 1.4 AI 用例 Prompt 归档与来源标注 — 交付：`docs/test/integration_test/prompts/integration_api_cases_01.md`；验收：含工具、模型、日期、原始提示词、人工复核状态（未审阅）；负责人：neon。
- [x] 1.5 运行时 `/openapi.json` 导出并与清单逐端点比对 — 交付：11 个路径与清单逐条一致，详情含 `model_name`，11/11 需 `x-api-key`；验收：`integration-report.md` §1；负责人：neon。
- [x] 1.6 按用例表实跑并回填状态 — 交付：`backend/scripts/integration_cases.py`（35 条）+ `docs/test/integration_test/report.md` + `integration-log.md` 实测行；验收：35/35 通过、接口覆盖 11/11；负责人：neon。

## 2 · 系统测试

- [x] 2.1 准备真实环境（MySQL 建库 + 后端依赖 + 模型权重 + 浏览器） — 交付：conda `jit-defect-prediction` + `infra/setup_mysql.py --skip-start` + `uvicorn` + `vite`；验收：`health=ok, db=up, models_loaded=8`；负责人：neon（环境由用户提供）。
- [x] 2.2 主线：同步真实提交 → 14 维特征 → 模型预测 → 四页展示 — 交付：25,285→25,307 同步、`et_v1` 0.97637、四页截图；验收：`docs/test/system_test/execution_records/system-test-run.md` §1；负责人：neon。
- [x] 2.3 异常 5 类 — 交付：`system_exceptions.py --scenario all` **13/13 通过**（缺权重、空库、失败恢复），加上 35 条集成用例里的无效令牌/非法参数与浏览器两种异常态；验收：`docs/test/integration_test/execution_records/2026-11-12-system-exceptions.md`；负责人：neon。
- [x] 2.4 非功能 ≥2 项实测 — 交付：新增 `backend/scripts/perf_loop.py`、`security_cases.py` 与两份 evidence；性能 p95=48.1ms 达标、安全 12/12；验收：`docs/test/integration_test/execution_records/2026-11-12-*.md`；负责人：neon。
- [ ] 2.5 系统测试计划 / 总结 — **未产出：文档由 sober 整理，neon 给实测内容并下结论/签字；AI-R5 禁止 AI 代写代签**。
- [x] 2.6 25 模型在线矩阵 — 交付：`docs/test/integration_test/execution_records/2026-11-12-online-25.md`；验收：补齐两张输入表后逐个 `POST /api/predict`，**23/25 通过**，2 个 tabnet 挂 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)；负责人：neon。
- [x] 2.7 逐端点联调留痕 — 交付：`backend/scripts/linkage_capture.py` + `evidence/2026-11-12-linkage.{md,json}`；验收：12 次请求（含 2 个异常）记录包络与响应摘要；负责人：neon。
- [x] 2.8 25 模型矩阵固化为门禁 — 交付：`backend/scripts/online_models_matrix.py`；验收：实跑 23/25 且退出码 1（正确报警），#222 修完目标 25/25；负责人：neon。

## 3 · 验收测试

- [x] 3.1 验收用例设计 — 交付：`backend/scripts/acceptance_scenarios.py` 抽取活规格 **124 条 Scenario** 生成现场对照清单，并实跑 **10/10** 自动可判定子集；验收：`docs/test/integration_test/execution_records/2026-11-12-acceptance-checklist.md`；负责人：neon。
- [ ] 3.2 逐条现场判定（124 条「通过/失败/未执行」） — **未执行：需 neon 组织演示、现场判定并签字，AI 不代签**。
- [ ] 3.3 验收方案 / 报告 — **未产出：由 sober 整理成文，neon 下结论并签字（AI-R5）**。

## 4 · 过程记录与缺陷

- [x] 4.1 执行边界与未执行清单归档 — 交付：`docs/test/system_test/execution_records/neon-test-execution.md`；验收：环境核查逐项有命令与结果，未执行项有阻断原因与解除条件；负责人：neon。
- [x] 4.2 联调证据索引口径说明 — 交付：`docs/test/overview.md` 追加说明段；验收：已执行与未执行分别标明，未执行项不写“通过”，原因可追溯；负责人：neon。
- [x] 4.3 缺陷登记到 GitHub Issue — 交付：[#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)（语义表默认路径）、[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)（e2e 文本表）、[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)（契约/部署）、[#220](https://github.com/heapcluster/jit-defect-prediction/issues/220)（D-01~D-06）；验收：`docs/test/system_test/bug_list.md` 有链接与关联提交；负责人：neon。
- [ ] 4.4 PR 审阅留痕 — 交付：PR #216 的 GitHub 审阅记录（当前仓库无独立审阅日志，需补可点击链接）；验收：PR #216 的审阅结论、跟进缺陷与合并提交号可反查；负责人：neon。
- [x] 4.5 回飞书看板映射 11 项任务并写本周周报 — 交付：[看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) 11 条新记录（Sprint 2/3 + 负责人 + 状态 + change）、[工作周报-20261113](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa)；验收：任务可对应负责人与状态，周报含三要素；负责人：neon。

## 测试与验证

> 规范校验（2026-11-10 实跑）：`openspec validate neon-test-baseline --strict` → `is valid`；`openspec validate --specs --strict` → 12 passed, 0 failed。

### 1. 单元测试

- 覆盖对象：本 change 不改业务代码；新增 `backend/scripts/*.py` 属测试脚本，不进 pytest 收集（`pytest.ini` 的 `testpaths=tests`）。
- 后端基线（2026-11-12 实跑）：`cd backend && python -m pytest -q --cov=app --cov-branch` → **249 passed / 0 failed**，28.2s，行覆盖 **85%**（分支 336、部分 40）。
- 前端基线：`cd frontend && npm run test:unit` → 9 文件 / **59 用例通过**，26.41s。

### 2. 集成测试

- 链路与场景：`docs/test/integration_test/endpoint_inventory.md` §4（11 端点四类）；落地 35 条可执行用例（健康探针的「非法参数」不适用）。
- 执行命令：`cd backend && python scripts/integration_cases.py --json out.json`（服务需先起）。
- 实测结果：**35/35 通过**，接口覆盖 **11/11**；跨模块链路 1 条（预测 0.97637 = 详情 = 列表）、并发 1 条（200/500 不串扰）。
- 证据路径：`docs/test/integration_test/report.md`（逐条结果）、`docs/test/overview.md`（索引）、`docs/test/system_test/execution_records/`（页面截图）。

### 3. 验收测试

- 对照对象：`openspec/specs/**/spec.md` 的 124 条 Scenario，已由 `acceptance_scenarios.py` 生成完整对照清单。
- 已覆盖：自动可判定子集 10/10 + 四页面主干 + 「提交不存在」「未知路由」两种异常态（浏览器实拍）。
- 未执行：124 条的现场逐条判定与签字；空能力目录 5 个仍需补规格。
- 执行人：neon（判定/签字），sober（整理文档）。

### 4. 非功能验证

- 性能：**已实测**。`python scripts/perf_loop.py`（100 次）→ p50 28.3ms / p95 48.1ms / p99 48.9ms / max 56.0ms，目标 p95<500ms **达标**；证据 `docs/test/integration_test/execution_records/2026-11-12-perf.md`。
- 安全：**已实测**。`python scripts/security_cases.py` → 12/12（鉴权 6 项、畸形参数 4 项、模型不可用 1 项、未知模型 1 项），响应无堆栈/SQL/路径泄漏；证据 `docs/test/integration_test/execution_records/2026-11-12-security.md`。
- 可靠性：**已实测**。`system_exceptions.py --scenario all` 13/13（缺权重、空库、同步中强杀后重启恢复），证据 `docs/test/integration_test/execution_records/2026-11-12-system-exceptions.md`。
- 易用性：部分实测。四页面与两种异常态截图见 `docs/test/system_test/execution_records/`，未做多浏览器与无障碍专项。

### 5. 已知缺口与后续计划

| 缺口 | 影响 | 责任人 | 完成条件 |
|---|---|---|---|
| 2 个 tabnet 模型 CPU 加载失败 | 25 模型在线少 2 个 | 蛋神的蛋（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） | 重新导出 CPU 权重或加载侧 `map_location="cpu"`，复测后回填 25/25 |
| 输入表未按交付布局生成 | 干净检出下 semantic/fused/e2e 不可用 | 蛋神的蛋（[#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)） | 交付时放到约定路径或后端加回退 |
| 逐 124 条 Scenario 现场判定未做 | 验收测试未完成 | neon（判定/签字） | 按生成的对照清单组织演示并逐条记录 |
| 逐接口浏览器截图未自动化 | 联调截图证据不全 | neon | 需浏览器自动化环境；HTTP 层留痕已由 `linkage_capture.py` 覆盖 |
| 五个空能力目录的历史记录 | 当前 `openspec/specs/` 已有 15 份有效活规格，此项无需再补空目录 | sober | 复核本 PR 的 `openspec validate --specs --strict` 输出 |
| 系统测试计划/总结、验收方案/报告虽已在 `docs/test/`，仍缺现场签字 | 无签字版交付结论 | sober（成文）/ neon（结论+签字） | neon 对现行四份文档复核并签字 |
| `nfr-evidence` 原模型不可用口径冲突 | 本 PR 已按“指定模型不可用 40001；整个注册表为空 50000”订正规格；安全脚本中的旧偏差提示仍需另行修正 | sober / 后端 | 后续脚本 PR 删除旧提示并补两类场景断言 |
