# online-eight-model-selection — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/model-coverage/spec.md`、`specs/predict-api/spec.md`
> 负责人：repo 苏哲勋（跨线契约协调）｜ 创建：2026-10-24
> **状态：已裁定执行（蒋励 2026-10-25，Issue #139）；实现中，未勾选项不得当作已完成**
> 用户故事：owner 要求——八个已训练模型均可在线切换（已由组长裁定落地）
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 冻结口径变更（契约评审）

- [x] 1.1 非作者评审与共签 —— **由组长裁定代替三线共签**（蒋励 2026-10-25：「空归因降级」方案批准，R6 冻结解除）；`openspec validate` 归档输出待苏哲勋补跑。
- [x] 1.2 契约三同步八项枚举、40001/50000 规则与空归因边界 —— 文案已按 **v1.7** 写好（§三.4 枚举 3→8 + 归因口径 + 变更日志行）；因 `docs/backend/api-spec.md` 与 `docs/common/local-runbook.md` 正被未合入的 PR #149 修改，**这两份文件的落地改在本 PR 合入、#149 先合后的跟进 PR**（同文件不双开，防互相冲掉）；`docs/frontend/pages.md` 的模型清单描述随前端线核对（4.1 同批）。

## 2. 模型线交付（蒋励）

- [x] 2.1 五个新增权重从 `[evaluated]` 移至 `[models]`，保留原三项、14 项列序与依赖说明 —— `data_model/pipelines/expert/models/feature_order.txt`（`[dependencies]` 补 lightgbm/torch/pytorch_tabnet，`[how_to_load]` 补 Pipeline 加载注意）；`data_model/tests/test_feature_contract.py` 的交付边界断言同步改 8 项并通过。权重本体不入库（走包分发）。
- [x] 2.2 模型线权威说明标明八项在线 —— `docs/model/model-line-plan.md` §6/§7；证据：`backend/scripts/evidence/online-eight-model-selection-2026-10-25.md`（8/8 加载 9.8s、逐模型延迟与归因）。

## 3. 后端八模型加载与预测（吕建江）

- [x] 3.1 运行依赖与逐个加载 —— `environment.yml` 早已声明 lightgbm/torch/pytorch-tabnet（本机 conda 环境实测可用）；`backend/app/model_registry.py` 修复 `_is_tree_family` 漏判 lightgbm（lgbm 归因原被降级为空）；启动日志实测 8/8。**待吕建江复核代码。**
- [x] 3.2 补八模型用例 —— `backend/tests/test_model_registry.py` 新增 3 条（树族识别含 lightgbm / lgbm TreeExplainer / 核模型降级为空不抛异常）；真实八权重逐项 `POST /api/predict` 的接口级复测归 4.2 与苏哲勋验收。

## 4. 前端清单与跨线验收

- [x] 4.1 前端下拉改八项且与 `[models]` 同步 —— `frontend/src/utils/models.js`（8 项 + 空归因注释）；`frontend/tests/models.spec.js` 动态比对通过（19/19）；空解释时显示既有「无归因」文案（页面既有降级路径，未新增文案）。**待刘帅华复核。**
- [ ] 4.2 每模型隔离 `MODEL_DIR` 各跑 n=100 压测并归档 —— 单次延迟已实测（8 模型全部 <130ms，见证据文件）；n=100 正式压测与八份 perf 证据归吕建江，未达标不得勾选。
- [ ] 4.3 苏哲勋核对契约三/模型清单/前端清单/性能证据，组织非作者验收并归档 change —— 待 4.2 完成后执行；归档前跑 `openspec validate --specs --strict` 与 `python infra/check_spec_references.py deltas`。

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`。本 change 已过 propose 阶段进入实现；下列为**已执行**项的证据，未执行项如实标注。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 八模型清单解析、注册表（含 lightgbm 树族识别）、核/深度模型空归因降级、前端清单一致性 |
| 测试文件 | `data_model/tests/test_feature_contract.py`、`backend/tests/test_model_registry.py`、`frontend/tests/models.spec.js` |
| 用例数与结果 | data_model 套件通过（交付边界改 8 项断言）；backend 新增 3 条且全量通过；frontend 19/19 通过 |
| 复现命令 | `cd data_model && python -m pytest -q`；`cd backend && python -m pytest -q tests/test_model_registry.py`；`cd frontend && npm run test:unit` |
| 正向用例 | `[models]` 声明八项 → 启动日志 8/8、逐项返回同名真实风险分数（证据文件 §1/§2） |
| 异常 / 边界用例 | 清单外第 9 个名字 → 40001（机制未变）；核/深度模型归因为空数组且不抛异常（新测试钉住） |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 清单/权重 → 后端加载与预测 → 前端三页面选择 |
| 测试文件 | `backend/tests/test_model_registry.py`、`frontend/tests/models.spec.js` |
| 用例数与结果 | 机制层已过；**真实八权重的端到端页面截图待刘帅华/吕建江各本机补**（联调时） |
| 关键断言 | 三处八项一致（manifest = models.js = 契约枚举）；启动日志 8/8；单模型损坏不拖垮查询服务 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/model-coverage/spec.md` 与 `specs/predict-api/spec.md` 各 Scenario；契约三 §三.4、§四 |
| 用例数与结果 | 已执行：8/8 加载 + 逐模型预测/归因实测（证据文件）；T-ST-04 判据已按 8 模型改写（`docs/common/test-plan.md`） |
| 复现命令 / 步骤 | 证据文件 §1/§2 的命令；`POST /api/predict` 逐模型请求核对模型名、分数和解释边界 |
| 证据归档 | `backend/scripts/evidence/online-eight-model-selection-2026-10-25.md`（已产出）；perf 八份待 4.2 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，部分验证 | 单次推理 8 模型全部 <130ms（证据文件 §4）；n=100 压测与 p95 待 4.2 |
| 安全 | 是，未回归 | 权重路径不回显的既有断言仍有效（`test_security_boundaries.py`）；本 change 未新增回显面 |
| 可靠 | 是，已验证（机制） | 部分权重失败时查询服务仍可用（既有 `failed models` 机制 + 测试） |
| 易用 | 是，部分验证 | 空归因提示路径存在；八项选择截图待联调补 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 三线共签缺 sober/吕/刘 的签字 | 组长裁定代替（2026-10-25） | 苏哲勋在验收归档时补签确认 | change 归档前 |
| n=100 逐模型压测未跑 | perf_loop 无 `--model-name`，需逐模型隔离 `MODEL_DIR` | 吕建江 | Sprint 3 |
| 前端八项联调截图未补 | 依赖各人本机权重包 | 刘帅华 | 联调时 |
| 真实权重端到端页面复测 | 同上 | 刘帅华 + 吕建江 | 联调时 |
