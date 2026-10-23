# path-references-alignment — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/commit-collection/spec.md`、`specs/labeled-dataset/spec.md`、`specs/feature-extraction/spec.md`、`specs/model-training/spec.md`、`specs/model-coverage/spec.md`
> 负责人：model 蒋励 ｜ 创建：2026-10-16 ｜ 状态：已完成（2026-10-23 归档，证据见 `path-scan.md`）
> 用户故事：无（工程化）—— 纯路径字符串修订，不改变任何规格行为语义
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 规格修订（5 个能力的 MODIFIED delta）

- [x] 1.1 `specs/commit-collection/spec.md`：「报出采集统计」的统计报告路径改为 `data_model/preparation/reports/`
- [x] 1.2 `specs/labeled-dataset/spec.md`：「报出七项统计」的统计表路径改为 `data_model/preparation/reports/`
- [x] 1.3 `specs/feature-extraction/spec.md`：「全量产物与统计报告 MUST 可入库可复现」的报告路径改为 `data_model/preparation/reports/feature_stats.md`
- [x] 1.4 `specs/model-training/spec.md`：「MUST 产出两类评估指标」的报告路径改为 `data_model/pipelines/expert/reports/`
- [x] 1.5 `specs/model-coverage/spec.md`：登记报告路径改为 `data_model/pipelines/expert/reports/`；「交付模型 MUST 保持不变」的清单路径改为 `data_model/pipelines/expert/models/feature_order.txt`，推理入口改为 `python -m pipelines.expert.predict`

## 2. 进行中 change 的路径引用同步

- [x] 2.1 `semantic-feature-mainline`：`tasks.md` / `design.md` 中 `data_model/reports/`、`16_statistical_test.py`、`06_train_model.py`、`08_model_matrix.py` 引用改为新路径（`data_model/pipelines/<线>/reports/`、`python -m pipelines.expert.significance` 等）；实际残留仅 `05_split_dataset.py` 一处，已改为 `data_model/preparation/05_split_dataset.py`（`tasks.md` §7.2、`design.md`）
- [x] 2.2 `public-dataset-quality`：`tasks.md` / `proposal.md` / `specs/public-dataset/spec.md` 中 `data_model/reports/` 引用改为新归属路径 —— 扫描为 0 处命中，无需修订
- [x] 2.3 `feature-addons-sprint3`：`tasks.md` / `design.md` 中旧路径引用改为新归属路径 —— 扫描为 0 处命中，无需修订

## 3. 校验

- [x] 3.1 `openspec validate --all --strict` 全绿（19 项）
- [x] 3.2 `git diff` 确认本 change 只动路径字符串，规格语义（阈值 / 判定 / 交付边界）逐字未改

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、
> **集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**
> 本 change 是纯路径字符串修订（不改任何 Python 代码与运行时行为），
> 因此单元 / 集成 / 验收三层的**功能用例均不新增**，验证手段改为
> 「路径引用全量扫描 + 严格规格校验 + 语义逐字比对」三类静态检查；
> 不适用之处逐项注明，不省略板块。

### 1. 单元测试（本 change 新增/改动代码的作者负责）

| 项 | 内容 |
|---|---|
| 覆盖对象 | 不适用 —— 本 change 不新增、不改动任何 Python / 前端代码，只改 `openspec/specs/**` 与进行中 change 文档里的路径字符串 |
| 测试文件 | 不适用（无新增代码） |
| 用例数与结果 | 0 条 ｜ 不适用 |
| 复现命令 | 不适用 —— 既有 `data_model` 测试套件不受影响，见集成层 |
| 正向用例 | 不适用 |
| 异常 / 边界用例 | 不适用 |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 修订后的 5 份规格 + 3 份进行中 change 文档，与仓库实际产物路径的一致性 |
| 测试文件 | `data_model/tests/`（含本 PR 新增的缓存/注册/工作量/官方入口回归） |
| 用例数与结果 | **逐分支实测**（同一份本 change 文件随三个分支走，用例数不同）：

| 分支 | 环境 | 结果 | 与 #68 的差值原因 |
|---|---|---|---|
| #71 `refactor/model-package-structure` | conda `jit-defect-prediction`（Python 3.12.x） | 96 passed, 0 failed | 差 1 条 = `data_model/tests/test_camel_source.py`（camel 采集回归，该 change 为 #68 独有） |
| #67 `docs/update-project-docs` | 同上 | 96 passed, 0 failed | 同上 |
| #68 `feat/model/expert-line-training` | 同上 | 97 passed, 0 failed | 基准 |

  （计数为**通过数**，非收集数；均为 0 failed、0 skipped。本表随分支实测更新，
  不再用单一数字冒充三线一致 —— 三线用例数本就不同，原因见右列。） |
| 复现命令 | `python -m pytest data_model` |
| 关键断言 | 修订后的报告路径在仓库中真实存在：`data_model/preparation/reports/`、`data_model/pipelines/expert/reports/`、`data_model/pipelines/expert/models/feature_order.txt` |

### 3. 验收测试（交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | 5 份 MODIFIED delta 的 SHALL/MUST 条目中「MUST 可入库可复现 / 报告路径」相关条目 |
| 用例数与结果 | 5 条 ｜ **5/5 通过**（2026-10-23 于 `main` @ `3a9b7b0` 实测） |
| 复现命令 / 步骤 | `openspec validate path-references-alignment --strict`；随后对每条修订路径执行 `Test-Path <修订后路径>`（5/5 必须为 True） |
| 证据归档 | `openspec/changes/path-references-alignment/path-scan.md`（§1 路径存在性 6/6 True、§2 残留扫描 6 处全被 delta 覆盖、§4 校验与回归） |

### 4. 非功能验证（本 change 触及则必填，否则写「本 change 不触及」）

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 不触及 —— 无运行时代码变更 |
| 安全 | 否 | 不触及 —— 无鉴权 / 输入处理变更 |
| 可靠 | 否 | 不触及 —— 无幂等 / 降级逻辑变更 |
| 易用 | 否 | 不触及 —— 无用户界面变更 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| ~~§3 验收层的路径扫描证据文件尚未产出~~ **已闭环（2026-10-23）** | 证据落 `path-scan.md`：6 条修订路径 `Test-Path` 全 True | model 蒋励 | 已完成 |
| ~~§2 集成层的 `python -m pytest data_model` 需在合入后重跑~~ **已闭环（2026-10-23）** | 以 `main` @ `3a9b7b0` 重测：`100 collected ｜ 99 passed, 1 skipped, 0 failed`（26.5s） | model 蒋励 | 已完成 |
