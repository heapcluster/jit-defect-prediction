# remove-offline-ingest-and-align-live-specs — 任务清单

> 提案：`proposal.md` ｜ 设计决策：无 `design.md`（本 change 只改规格与文档，不含技术选型） ｜ 规格：`specs/db-schema/spec.md`
> 负责人：repo（文档与契约线；PR 把关：苏哲勋）｜ 创建：2026-10-26 ｜ 状态：进行中（规格 delta 与活文档已改，待 PR 合入后归档）
> 用户故事：无（工程化：把活规格与活文档对齐到已落地的实现）
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. 规格 delta（`openspec/changes/<change>/specs/`）

- [x] 1.1 `db-schema`：REMOVED「四份 CSV 灌入」（附 Reason / Migration，指明数据入口改为实时同步）
- [x] 1.2 `db-schema`：ADDED「实时同步入库」（幂等键按表列全、单条失败只计入 `skipped`、MUST NOT 中断整批）
- [x] 1.3 `db-schema`：MODIFIED「一条命令建库」（前提由「先跑完数据线 01–04」改为「配好 `SOURCE_REPO` 后由实时同步产数据」）
- [x] 1.4 `db-schema`：MODIFIED「特征列名与顺序」（把「特征 CSV 缺行 → 出灌入报告」改为「同步中现算失败 → 计入 `skipped`，不写缺列/补 0 的特征行」）

> **不在本 change 内的两处活规格**：`model-coverage`「交付模型 MUST 保持不变」的措辞、`predict-api`「模型加载」的默认目录，都已被 `online-eight-model-selection` / `delivery-model-allowlist` 两个 open change 占用 —— 同时 MODIFIED 同一 Requirement 标题会被 `infra/check_spec_references.py deltas` 判冲突（CI 必红），且改别人 change 违反「改别人文件先由对方改」的铁规矩。故本 change 不动这两处，改由归属 change 收口（对照表见 proposal，本文件 §5 已知缺口记了归属与收口条件）。

## 2. 活文档同步（删/改已不可执行的命令）

- [x] 2.1 `backend/README.md` §2.5：灌入口径改为实时同步（附 curl 示例）
- [x] 2.2 `docs/common/local-runbook.md`：删掉「已移除」之后仍照抄的 ingest 命令块，改同步入口、模型数、错误码行、Node 版本
- [x] 2.3 `docs/backend/mysql-setup.md`：删 ingest 命令块与 `--ingest` / `--ingest-csv` 参数行，特征重灌步改实时同步，加「历史记录说明」
- [x] 2.4 `docs/repo/demo-script-sprint1.md`：演示脚本的四条 ingest 命令改为同步调用，§0.0 标题与 preflight 用法同步
- [x] 2.5 `docs/backend/acceptance.md` / `docs/frontend/acceptance.md`：数据步改同步、模型口径改 8 个
- [x] 2.6 `docs/common/test-strategy.md` / `docs/common/test-plan.md`：后端用例条数与前端用例数、测试路径、命名约定对齐实测
- [x] 2.7 `data_model/pipelines/expert/README.md`：删灌库命令，交付清单改 8 个
- [x] 2.8 全仓复扫后的残留口径清零：`README.md`（产物说明）、`backend/README.md`（「建表与灌入 → 建表与入库」、方案 C 的「由本线灌入」）、`data_model/README.md`（铁规矩 4 的「灌库责任」）、`data_model/ENVIRONMENT.md`（交付表里的「灌库用数据」）、`docs/model/acceptance.md`（「可直接被 `app.ingest predictions` 消费」）、`docs/repo/demo-script-sprint1.md` §0.3 的演示前置步骤
- [x] 2.9 复扫口径：活文档与活规格里 `app.ingest` / `--ingest` / `--ingest-csv` 只剩「已彻底移除」告示、历史记录说明与守门测试断言；`docs/common/test-report-sprint2.md` 等历史证据档按「不改写」保留

## 3. 设计与契约文档的旧口径（离线 CSV 灌库 / 方案 C 导入）

- [x] 3.1 `docs/design/diagrams.md`：图 1 的数据源节点由「CSV：01–03 + 方案 C prediction_result.csv」改为「历史索引仓库 `SOURCE_REPO`」，落库边标注「实时同步落库」
- [x] 3.2 `docs/design/architecture.md` §5 ③：离线训练交付物改为「`.pkl` + `feature_order.txt`（`prediction_result.csv` 仅作评估对照）」，并写明入库只走实时同步
- [x] 3.3 `docs/design/database.md` §1：四表说明里的「A（实时推理）+C（离线批量）写同一张表」改为「A 与实时同步写同一张表」
- [x] 3.4 `docs/design/sprint0-scope.md` §4：跨线接口 A+C 的措辞改为「C 出 `.pkl` 与 `feature_order.txt`，`prediction` 表由后端实时同步写入」（三个冻结点不动）
- [x] 3.5 `docs/common/glossary.md`：「A+C 交付」词条同步
- [x] 3.6 `docs/design/data-fields.md`（契约一）升 1.6：只改「建表归属」表的数据来源与「入库链路」段，**列名、类型、索引、取值枚举一律未动**，变更日志按既有格式记一行
- [x] 3.7 核查（结论写实，不改文件）：`docs/design/database.md` 原本就是四张表且与 `infra/schema.sql` / `backend/app/models.py` 一致，「三表旧形态」的判断不成立，故该文件只改 §1 的一处措辞（见 3.3），未做结构性改写

## 4. 顺带修的文档陈旧项

- [x] 4.1 `README.md`：CI 状态（`ci.yml` / `pr-auto-review-prototype.yml` / `codeql.yml` 已入库）、Node 版本（`>=20.19`）、Python 版本（`3.12.x`）、preflight 用法（`--init-db`）
- [x] 4.2 `docs/common/local-runbook.md`：Node 版本与 CI 描述、模型数、错误码行
- [x] 4.3 `docs/common/test-plan.md` / `docs/common/test-strategy.md`：前端测试路径（`src/__tests__/` → `frontend/tests/`）、命名约定、计数

## 5. 归档

- [x] 5.1 `openspec archive remove-offline-ingest-and-align-live-specs --yes`：`db-schema` 的 delta 应用到活规格并归档为 `openspec/changes/archive/2026-10-26-remove-offline-ingest-and-align-live-specs/`
- [x] 5.2 归档后自验：`openspec validate --specs --strict --no-interactive` + `python infra/check_spec_references.py links` / `deltas` 全通过
- [x] 5.3 归档后活规格的两处**指针**同步（openspec delta 只覆盖 Requirement，不含 Purpose 与正文里的契约版本号）：Purpose 的「建库与灌入」改为「建库与实时同步入库」；「建表字段逐字对齐契约」正文里的契约版本号 `v1.5` 改为 `v1.6`（字段定义未变）

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、
> **集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**

### 1. 单元测试（本 change 新增/改动代码的作者负责）

| 项 | 内容 |
|---|---|
| 覆盖对象 | 无 —— 本 change **零代码改动**（只改规格与文档），不新增/修改任何 `.py` / `.js` / `.vue` |
| 测试文件 | 不适用 |
| 用例数与结果 | 不适用；代之以静态检查与回归：`ruff check backend data_model infra` → **0 项**；`pytest backend` → **253 passed**；`pytest data_model` → **155 passed**（均为**回归**，证明文档改动未牵动代码行为） |
| 复现命令 | `python -m ruff check backend data_model infra` ；`python -m pytest backend -q` ；`python -m pytest data_model -q` |
| 正向用例 | `python infra/check_spec_references.py links` → `links: passed`（活文档与活规格里的仓内链接全部可解析） |
| 异常 / 边界用例 | `python infra/check_spec_references.py deltas` → `deltas: passed`（无两个 change 同时 MODIFIED 同一 Requirement 标题）；`npx @fission-ai/openspec@1.11.0 validate --specs --strict --no-interactive` → 通过（归档后的活规格结构与 Requirement 数量合规） |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 本 change 不触及接口与数据流（只改文档/规格）；涉及的三条契约（契约一/二/三）**未改字段、类型、接口路径** |
| 测试文件 | 不适用（沿用 `backend/tests/`、`data_model/tests/` 现有套件作回归） |
| 用例数与结果 | 回归：`pytest backend` **253 passed** ｜ `pytest data_model` **155 passed** |
| 复现命令 | `python -m pytest backend -q` ；`python -m pytest data_model -q` |
| 关键断言 | 规格 delta 与实现一致：`db-schema` 的幂等键与失败隔离口径对得上 `backend/app/api/sync.py`（逐条 `skipped` 不中断整批）；「特征行缺失」场景对得上 `backend/app/api/predict.py` 的现算失败路径；「一条命令建库」对得上 `backend/app/db.py` 的四表建表命令 |

### 3. 验收测试（交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | `db-schema`「实时同步入库」3 个 Scenario、「一条命令建库」2 个、「特征列名与顺序」2 个（合计 7 个） |
| 用例数与结果 | 规格侧 **7 个 Scenario 逐条核对通过**（对照实现与仓内证据，见下「复现命令 / 步骤」）；运行时行为由既有 `backend/tests/test_sync_api.py`、`test_predict_api.py` 覆盖，未新增 |
| 复现命令 / 步骤 | ① `npx @fission-ai/openspec@1.11.0 validate --specs --strict --no-interactive`；② `python infra/check_spec_references.py links`；③ `python infra/check_spec_references.py deltas`；④ 全仓检索活文档与活规格无 `app.ingest` / `--ingest` 残留（仅存于历史证据档与归档 change，已加说明） |
| 证据归档 | 归档件 `openspec/changes/archive/2026-10-26-remove-offline-ingest-and-align-live-specs/`（proposal / tasks / `db-schema` delta）；活规格 `openspec/specs/db-schema/spec.md` |

### 4. 非功能验证（本 change 触及则必填，否则写「本 change 不触及」）

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 本 change 只改文档与规格，不改任何运行时路径 |
| 安全 | 否 | 同上；口令、鉴权、路径回显口径未改 |
| 可靠 | 否 | 同上；幂等键口径只在规格层与既有实现对齐，未改实现 |
| 易用 | 是（文案层） | 活文档里的操作指引改为可直接执行（实时同步 + `SOURCE_REPO`），不再给已失效的 ingest 命令 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| `predict-api`「模型加载」仍写默认目录 `data_model/models/`（该目录不存在，实为 `data_model/pipelines/expert/models/`） | 该 Requirement 已被 open change `delivery-model-allowlist` 占用；其 delta 已写正确默认路径与清单驱动加载，本 change 再 MODIFIED 同名标题会触发 `deltas` 冲突检查（CI 必红），且属改别人 change | backend 吕建江 | 该 change 补齐 2.1 交付证据后归档 |
| `model-coverage`「交付模型 MUST 保持不变」措辞仍是 change-scoped（「保持既有交付模型不变」「本 change 合入」） | 该 Requirement 已被 open change `online-eight-model-selection` 占用；其 delta 已把 `[models]` 固定为 8 项并写明评估线不入清单，归档时整条替换 | repo 苏哲勋 | 该 change 的 4.2 压测与 4.3 非作者验收完成后归档 |
| 移除离线灌库后，`commit_label` 表**没有运行时写入方**（四接口只读 `commit` / `commit_feature` / `prediction`，不读标签表） | 离线 CSV 灌库是它原先唯一的写入路径；补写入方属功能改动，不在本 change（零代码）范围 | backend 吕建江 + 组长 | 需另开 change 裁定 |
| 契约一 1.6 的「入库链路改口」待冻结人**追认** | 契约一冻结人是蒋励 + 吕建江；本次只改措辞（列名/类型/索引/枚举未动），需 吕建江 确认 | 文档与契约线 | 归档前回复即可 |
| `docs/backend/mysql-setup.md` §5 的行数判据（`commit` 84,461 / `prediction` 83,943）是**离线全量口径**；改走实时同步后行数随同步量增长 | 该判据是组长本机 MySQL `jit_demo` 的实测基线，移除灌库后不可复现同样行数 | repo 苏哲勋 | 新环境重测后更新判据 |
| 本机 MySQL `jit_demo` 未实跑本 change 的验收步骤 | 本 change 零代码改动，运行时行为由 CI 回归 + 既有套件覆盖；本机环境不参与 | repo 苏哲勋 | 需要时按 `docs/common/local-runbook.md` 走一遍 |
| `commit_label` / `predictions` 等历史 CSV 产物仍留在数据线目录 | 它们是数据线归档产物，不是入库路径；按「历史证据档不改写」保留 | model 蒋励 | 不排期 |
