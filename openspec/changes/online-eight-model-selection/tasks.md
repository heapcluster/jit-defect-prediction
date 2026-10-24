# online-eight-model-selection — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/model-coverage/spec.md`、`specs/predict-api/spec.md`
> 负责人：repo 苏哲勋（跨线契约协调）｜ 创建：2026-10-24 ｜ 状态：未开始（待非作者评审）
> 用户故事：owner 新要求——八个已训练模型均可在线切换；现有三模型 MVP 独立验收
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 冻结口径变更（契约评审）

- [ ] 1.1 苏哲勋发起本 change 非作者评审，并取得模型蒋励、后端吕建江、前端刘帅华对“无适用解释器返回空归因、500ms 靶子不变”的共签 — `openspec/changes/online-eight-model-selection/proposal.md`、`openspec/changes/online-eight-model-selection/design.md` 与 PR 审阅记录；运行 `openspec validate online-eight-model-selection --strict --no-interactive` 并归档输出。
- [ ] 1.2 评审通过后由契约维护者同步八项枚举、现行 40001/50000 规则与空归因边界 — `docs/backend/api-spec.md` §三.4 和 `docs/frontend/pages.md`；核对两文件所列模型与 `specs/predict-api/spec.md` 一致，不先于评审修改冻结正文。

## 2. 模型线交付（交给 backend 吕建江）

- [ ] 2.1 蒋励把五个新增权重从 `[evaluated]` 移至 `[models]`，保留原三项、14 项列序与依赖说明 — `data_model/pipelines/expert/models/feature_order.txt`；运行 `python -m pytest -q data_model/tests/test_model_registry_parity.py`，并把八权重校验清单交给 backend 吕建江，权重本体不入库。
- [ ] 2.2 蒋励同步模型线权威说明并标明八项在线、其他训练注册项非交付 — `docs/model/model-line-plan.md`；核对该文件与 `[models]` 和 R6 一致，产物交给 backend 吕建江与 frontend 刘帅华。

## 3. 后端八模型加载与预测（交给 frontend 刘帅华）

- [ ] 3.1 吕建江补齐 LightGBM、PyTorch、pytorch-tabnet 的运行依赖和 TabNet 反序列化可用性，八项逐个加载且启动日志可核 8/8 — 后端依赖清单、`backend/app/model_registry.py`、`backend/tests/test_model_registry.py`；运行 `python -m pytest -q backend/tests/test_model_registry.py`，把实际可用模型清单交给 frontend 刘帅华。
- [ ] 3.2 吕建江补八模型 `POST /api/predict` 的正向、清单外 40001、清单内权重缺失/加载失败、空归因用例 — `backend/tests/test_predict_api.py`；运行 `python -m pytest -q backend/tests/test_predict_api.py`，不得把静默跳过写成 8/8 通过。

## 4. 前端清单与跨线验收

- [ ] 4.1 刘帅华把下拉项改为八项且与 `[models]` 同步，空解释时显示既有文案 — `frontend/src/utils/models.js`、`frontend/tests/models.spec.js` 与相关页面测试；运行 `cd frontend && npm run test:unit`，把八项选择截图与结果记入 `docs/frontend/integration-log.md` 交给苏哲勋归档。
- [ ] 4.2 吕建江使用真实八权重做一次完整目录启动与逐模型预测，并为每模型在隔离 `MODEL_DIR` 下各跑 n=100 压测 — `backend/scripts/evidence/online-eight-model-selection-2026-10-24.md`；单项命令例：`cd backend && python scripts/perf_loop.py --n 100 --model-source lr_v1 --out scripts/evidence/lr_v1-perf.md`，其余七项逐一替换模型名、隔离目录并记录权重摘要、8/8 加载、成功率和 p95，未达标不得勾选。
- [ ] 4.3 苏哲勋核对契约三、模型清单、前端清单与八份性能证据，组织非作者验收并在合入后按流程归档 change — `openspec/specs/model-coverage/spec.md`、`openspec/specs/predict-api/spec.md` 与 PR 描述；运行 `openspec validate --specs --strict` 和 `python infra/check_spec_references.py deltas`，结果全绿才记为完成。

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`。本 PR 是 propose 阶段，**下述实现/权重测试均未执行**；任务框不能预先勾选。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | 八模型清单解析、模型注册表、非法/缺失模型、前端选项与空解释 |
| 测试文件 | `data_model/tests/test_model_registry_parity.py`、`backend/tests/test_model_registry.py`、`backend/tests/test_predict_api.py`、`frontend/tests/models.spec.js` |
| 用例数与结果 | 待各线实现后实跑；本提案未执行，不填通过数 |
| 复现命令 | `python -m pytest -q backend/tests/test_model_registry.py backend/tests/test_predict_api.py data_model/tests/test_model_registry_parity.py`；`cd frontend && npm run test:unit` |
| 正向用例 | `[models]` 声明八项且八权重可加载 → 八项可选择、逐项返回同名真实风险分数 |
| 异常 / 边界用例 | 清单外模型 → 40001；清单内权重损坏 → 不得伪造分数；无适用解释器 → 风险正常且解释为空 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | 模型线清单/权重 → 后端加载与预测 → 前端三页面选择 |
| 测试文件 | `backend/tests/test_model_registry.py`、`backend/tests/test_predict_api.py`、`frontend/tests/models.spec.js` |
| 用例数与结果 | 待真实八权重投放后执行；本提案未执行 |
| 复现命令 | `python -m pytest -q backend/tests/test_model_registry.py backend/tests/test_predict_api.py`；`cd frontend && npm run test:unit` |
| 关键断言 | 三处八项一致，启动日志 8/8；单个模型损坏不拖垮查询服务，但交付验收不通过 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/model-coverage/spec.md` 与 `specs/predict-api/spec.md` 各 Scenario；契约三 §三.4、§四 |
| 用例数与结果 | 待跨线交付；本提案未执行 |
| 复现命令 / 步骤 | `openspec validate online-eight-model-selection --strict --no-interactive`；真实权重逐项请求 `POST /api/predict` 并核对模型名、分数和解释边界 |
| 证据归档 | `backend/scripts/evidence/online-eight-model-selection-2026-10-24.md`（待产出） |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是，未验证 | 示例：`cd backend && python scripts/perf_loop.py --n 100 --model-source lr_v1 --out scripts/evidence/lr_v1-perf.md`；每次先设置仅含待测模型的隔离 `MODEL_DIR`，八份证据待产出 |
| 安全 | 是，未验证 | `python -m pytest -q backend/tests/test_predict_api.py`；权重路径不可回显 |
| 可靠 | 是，未验证 | `python -m pytest -q backend/tests/test_model_registry.py`；部分权重失败时查询服务仍可用 |
| 易用 | 是，未验证 | `cd frontend && npm run test:unit`；空归因提示与八项选项截图待归档 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 空归因方案未获三线共签 | owner 消息为建议，尚非正式裁定 | repo 苏哲勋组织，model 蒋励/backend 吕建江/frontend 刘帅华确认 | apply 前 |
| 冻结契约三仍为三项 | propose 不能先于非作者评审改变生效契约 | repo 苏哲勋与契约维护者 | 评审通过后的实现 PR |
| 真实八权重、依赖与性能未验证 | 权重不入库，必须在交付环境逐项实测 | model 蒋励/backend 吕建江 | 八模型交付验收时 |
| OpenSpec CLI 本机不可用 | 当前终端 npm 入口损坏，无法在本机执行 1.11.0 | repo 苏哲勋 | 提案 CI 与工具修复后复核 |
