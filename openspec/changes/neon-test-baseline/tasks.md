# neon-test-baseline — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/test-evidence/spec.md`
> 负责人：neon（集成 / 系统 / 验收测试）
> 关联需求：飞书「想到什么取什么」本周计划 N-2 / N-3 / N-4；四类测试交付要求见 `docs/common/test/test-assessment-guide.md`
> 状态：自动化部分已完成并在 `2734c1b` 上实跑（2026-11-15）；现场逐条判定与人工签字仍未完成

## 1 · 集成测试取证前提

- [x] 1.1 端点清单核对 — 交付：`docs/想到什么取什么/integration_test/endpoint_inventory.md`；验收：11/11 路由与运行时 `/openapi.json` 一致，每个端点给出鉴权、参数边界、成功字段与业务码，附文件级证据。
- [x] 1.2 四类场景用例设计（11 端点 × 正常/缺参/非法/边界） — 交付：`docs/想到什么取什么/integration_test/endpoint_inventory.md` §4；验收：每类给出具体输入与预期码/断言。
- [x] 1.3 文档与代码偏差登记 — 交付：`docs/想到什么取什么/integration_test/endpoint_inventory.md` §3（D-02~D-07 + 交付缺口）；验收：每条有文档位置、代码位置、对断言的影响。
- [x] 1.4 AI 用例 Prompt 归档与来源标注 — 交付：`docs/想到什么取什么/integration_test/prompts/`（`integration_api_cases_01.md`、`integration_api_cases_02.md`、`integration_api_predict_01.md`、`integration_rerun_02.md`）；验收：含工具、模型、日期、提示词原文、人工复核状态。
- [x] 1.5 运行时 `/openapi.json` 逐端点比对 — 交付：`docs/想到什么取什么/integration_test/report.md` §1；验收：11 个路径与清单一致，全部要求 `X-API-Key`。
- [x] 1.6 按用例表实跑并回填状态 — 交付：`backend/scripts/integration_cases.py`（35 条）+ `docs/想到什么取什么/integration_test/report.md`；验收：**34/35 通过、接口覆盖 11/11**，失败项 T-IN-29 定位到图集产物缺失。

## 2 · 系统测试

- [x] 2.1 准备真实环境（MySQL 建库 + 后端依赖 + 模型权重 + 浏览器） — 交付：conda `jit-defect-prediction` + `infra/setup_mysql.py` + `uvicorn` + `vite`；验收：`health=ok, db=up, models_loaded=9`。
- [x] 2.2 主线：同步真实提交 → 14 维特征 → 模型预测 → 四页展示 — 交付：25,404→25,414 同步、`et_v1` 0.97637、`docs/想到什么取什么/system_test/execution_records/` 六张截图；验收：链路三处风险值一致（T-IN-35）。
- [x] 2.3 异常场景 — 交付：`backend/scripts/system_exceptions.py --scenario all` **13/13 通过**（缺权重、空库、失败恢复）；验收：`docs/想到什么取什么/integration_test/execution_records/2026-11-15-system-exceptions.md`。
- [x] 2.4 非功能 ≥2 项实测 — 交付：`backend/scripts/perf_loop.py`、`security_cases.py`；验收：性能 p95 68.1ms 达标（同日两次 53.3 / 68.1ms）、安全 **18/18**；记录见 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-perf.md`、`2026-11-15-security.md`。
- [ ] 2.5 系统测试计划 / 总结签字 — 文档已成文（`docs/想到什么取什么/system_test/test_plan.md`、`summary_report.md`），但由 AI 起草、**neon 未复核签字**（AI-R5）。
- [x] 2.6 25 模型在线矩阵 — 交付：`backend/scripts/online_models_matrix.py`；验收：**23/25 通过**，2 个 tabnet 挂 [#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)。
- [x] 2.7 逐端点联调留痕 — 交付：`backend/scripts/linkage_capture.py` + `docs/想到什么取什么/integration_test/execution_records/2026-11-15-linkage.md`（含 JSON 原始包络）；验收：13 次请求（含 2 个异常）记录包络与响应摘要。
- [x] 2.8 25 模型矩阵固化为门禁 — 交付：`backend/scripts/online_models_matrix.py`；验收：实跑 23/25 且退出码非 0（正确报警），#222 修完目标 25/25。
- [x] 2.9 并发负载与容量口径 — 交付：`backend/scripts/load_test.py`；验收：四档实测（5×5 / 10×5 / 10×10 / 20×10），记录于 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-load-test.md`，20 并发 p95 688.9ms 未达标如实登记。

## 3 · 验收测试

- [x] 3.1 验收用例与自动子集 — 交付：`backend/scripts/acceptance_scenarios.py` 抽取活规格 **137 条 Scenario** 并实跑 **10/10** 自动可判定子集；验收：`docs/想到什么取什么/integration_test/execution_records/2026-11-15-acceptance-checklist.md`。
- [x] 3.2 验收用例逐条实际结果回填 — 交付：`docs/想到什么取什么/acceptance_test/acceptance_cases.md`（20 条，11 通过 / 9 不通过）、`model-accuracy-evidence.md`；验收：每条有实测依据或明确标注缺据。
- [ ] 3.3 现场逐条判定与签字 — **未执行：124+ 条 Scenario 的现场演示与 A-01~A-20 编号取证需 neon 组织并签字，AI 不代签**。
- [ ] 3.4 验收方案 / 报告签字 — 文档已成文（`docs/想到什么取什么/acceptance_test/acceptance_plan.md`、`acceptance_report.md`），待 neon 复核签字（AI-R5）。

## 4 · 过程记录与缺陷

- [x] 4.1 执行边界与未执行清单 — 交付：`docs/想到什么取什么/README.md`；验收：已执行与未执行分别标明，未执行项给出阻断原因与解除条件。
- [x] 4.2 证据索引口径说明 — 交付：`docs/想到什么取什么/README.md` §2；验收：代码真源与文档目录分工写清，未执行项不写「通过」。
- [x] 4.3 缺陷登记 — 交付：`docs/想到什么取什么/system_test/bug_list.md`（10 条：`#217`、`#219`、`#220`、`#222` + BUG-01~BUG-06）；验收：每条有复现步骤、证据与状态，无法复现的放候选观察。
- [ ] 4.4 PR 审阅留痕 — 交付：GitHub 审阅记录链接（当前仓库无独立审阅日志，需补可点击链接）。
- [x] 4.5 回飞书看板映射 11 项任务并写本周周报 — 交付：[看板](https://gcnlk66qul6p.feishu.cn/base/SilBbJZFPaDct1slrIVcN2Nonsc) 11 条记录、[工作周报](https://gcnlk66qul6p.feishu.cn/docx/QTKgdRDNFoiN3uxc6OecURV2nZa)；验收：任务可对应负责人与状态。

## 测试与验证

> 规范校验：`openspec validate neon-test-baseline --strict`；结构校验：`python openspec/check_structure.py`。

### 1. 单元测试

- 覆盖对象：本 change 不改业务代码；新增 `backend/scripts/*.py` 属测试脚本，不进 pytest 收集（`pytest.ini` 的 `testpaths=tests`）。
- 后端（2026-11-15 实跑）：`cd backend && python -m pytest -q --cov=app --cov-branch` → **254 passed / 0 failed**，行覆盖 **87.2%**（1333/1528）、分支 **76.2%**（256/336）。
- 模型线：`cd data_model && python -m pytest -q` → **162 passed**。
- 前端：`cd frontend && npm run test:unit` → 9 文件 / **59 passed**。
- 说明：干净检出缺 `backend/static/` 会让 `app.main` 导入失败（BUG-01），跑测前需补建目录或先修代码。

### 2. 集成测试

- 链路与场景：`docs/想到什么取什么/integration_test/endpoint_inventory.md` §4（11 端点四类）；落地 35 条可执行用例。
- 执行命令：`cd backend && python scripts/integration_cases.py --json out.json`（服务需先起）。
- 实测结果：**34/35 通过**，接口覆盖 **11/11**；失败项 T-IN-29 为图集文件不在盘（BUG-02）；跨模块链路 1 条（0.97637 三处一致）、并发 1 条（200/500 不串扰）。
- 证据路径：`docs/想到什么取什么/integration_test/report.md`（逐条结果）、`docs/想到什么取什么/integration_test/execution_records/`（原始记录）、`docs/想到什么取什么/system_test/execution_records/`（页面截图）。

### 3. 验收测试

- 对照对象：`openspec/specs/**/spec.md` 的 137 条 Scenario，由 `acceptance_scenarios.py` 生成对照清单。
- 已覆盖：自动可判定子集 10/10、四页面主干、「提交不存在」「未知路由」两种异常态、「未预测」页态（浏览器实拍）。
- 未执行：Scenario 现场逐条判定与签字；四个空能力目录（feedback / observability / ops / quality）仍需补规格。
- 执行人：neon（判定/签字），sober（整理文档）。

### 4. 非功能验证

- 性能：`python scripts/perf_loop.py`（100 次）→ p50 36.2ms / p95 **68.1ms** / p99 122.4ms，目标 p95<500ms **达标**；证据 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-perf.md`。
- 并发：`python scripts/load_test.py --users 20 --requests 10` → p95 **688.9ms** 未达标，单进程吞吐 27~38 req/s；证据 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-load-test.md`。
- 安全：`python scripts/security_cases.py` → **18/18**（鉴权 6、畸形参数 4、注入 5、模型不可用 2、越权 1），响应无堆栈/SQL/路径泄漏；证据 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-security.md`。
- 可靠性：`system_exceptions.py --scenario all` **13/13**（缺权重、空库、同步中强杀后重启恢复）；证据 `docs/想到什么取什么/integration_test/execution_records/2026-11-15-system-exceptions.md`。
- 易用性：四页面与三种状态截图见 `docs/想到什么取什么/system_test/execution_records/`；跨浏览器（Edge / Firefox）未覆盖。

### 5. 已知缺口与后续计划

| 缺口 | 影响 | 责任人 | 完成条件 |
|---|---|---|---|
| 2 个 tabnet 模型 CPU 加载失败 | 25 模型在线少 2 个 | 模型线（[#222](https://github.com/heapcluster/jit-defect-prediction/issues/222)） | 重新导出 CPU 权重或加载侧 `map_location="cpu"`，复测后回填 25/25 |
| 图集 PNG 不随交付产物提供 | 模型性能页 6 张图 404（BUG-02） | 后端 / 交付流程 | 生成步骤写进 README 与镜像构建；抽屉正常渲染 |
| 干净检出缺 `backend/static/` | 新环境起不来（BUG-01） | 后端 | `create_app()` 建目录或提交占位文件 |
| Scenario 现场逐条判定未做 | 验收测试未完成 | neon（判定/签字） | 按对照清单组织演示并逐条记录 |
| 跨浏览器未覆盖 | 兼容性维度不达标 | neon | Chrome / Edge / Firefox 逐页截图 |
| 系统测试计划/总结、验收方案/报告缺签字 | 无签字版交付结论 | neon | 复核四份文档并签字 |
| `nfr-evidence` 模型不可用口径冲突 | 规格要求 50000，实现为 40001 | 规格负责人 / 后端 | 裁定后同步规格或代码 |
