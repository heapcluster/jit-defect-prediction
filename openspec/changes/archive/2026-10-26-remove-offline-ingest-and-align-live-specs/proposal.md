# 移除离线 CSV 灌库口径，把 db-schema 活规格与活文档对齐到当前实现

## Why

2026-10-25 裁定**彻底移除离线 CSV 灌库**（`backend/app/ingest.py` 与 `tests/test_ingest.py` 已删，数据入口统一为实时同步 `POST /api/sync` / `POST /api/sync-prs`）。但三处**活规格**与若干**活文档**仍停留在旧口径，导致：

- `db-schema` 规格仍把「四份 CSV 灌入」列为 Requirement（幂等键 upsert、缺主键整批回滚等场景），而实现已无该脚本 —— 规格描述了一个不存在的功能；
- `db-schema` 的「特征列名与顺序」仍按 CSV 文件灌入写场景（缺行 → 出「灌入报告」），与新入口不符；
- 活文档里还留着 `python -m app.ingest ...`、`--init-db --ingest` 等**已不可执行**的命令（`docs/common/local-runbook.md` 更出现「已移除」与「照此执行」自相矛盾两段）；
- 设计与契约文档则留着「方案 C 出 `prediction_result.csv` 由后端导入 `prediction` 表」的**旧入库链路**（`docs/design/{diagrams,architecture,database,sprint0-scope}.md`、`docs/common/glossary.md`、契约一「建表归属」节），与「入库只走实时同步」的新纪律直接打架。

活规格与活文档是「唯一依据」，留旧口径等于给下一位接手人发错误指令。

## What Changes

- `db-schema`：**移除**「四份 CSV 灌入」Requirement，**新增**「实时同步入库」Requirement —— 数据入口只有实时同步两条端点，幂等键与失败隔离口径写进规格。
- `db-schema`：**修改**「一条命令建库」—— 前提从「灌入前需先跑数据线 01–04」改为「配置历史索引后由实时同步产数据」。
- `db-schema`：**修改**「特征列名与顺序」—— 把「特征 CSV 缺行 → 灌入报告缺清单」改为「同步中现算失败 → 计入 `skipped`，不写缺列/补 0 的特征行」。
- 活文档同步（见 Impact）。

### 不在本 change 内的两处活规格（各归其 change，避免 MODIFIED 冲突）

`model-coverage` 与 `predict-api` 的活规格确实也停留在旧口径，但这两个 Requirement **已被别的 open change 占用**，
同时 MODIFIED 同一标题会被 `infra/check_spec_references.py deltas` 判为冲突（CI 必红）。故本 change 不动它们，
改由归属 change 收口：

| 活规格旧口径 | 归属 change | 那边已写好的内容 | 收口条件 |
|---|---|---|---|
| `model-coverage`「交付模型 MUST 保持不变」措辞 change-scoped | `online-eight-model-selection`（repo 苏哲勋） | 其 delta 已把 `[models]` 固定为 8 项、评估线不入清单 | 4.2 压测 + 4.3 非作者验收后归档 |
| `predict-api`「模型加载」默认目录写成 `data_model/models/`（该目录不存在） | `delivery-model-allowlist`（backend 吕建江） | 其 delta 已写默认 `data_model/pipelines/expert/models/` + 清单驱动加载 | 2.1 交付/实测补证后归档 |

## Capabilities

### Modified Capabilities

- `db-schema`: 数据入口从离线 CSV 灌入改为实时同步；建表与特征列口径不变。

## Impact

- 规格：`openspec/specs/db-schema/spec.md`（经本 change 归档后生效；归档另手工同步两处指针 —— Purpose 的「灌入 → 实时同步入库」与契约版本号 `v1.5 → v1.6`，openspec delta 只覆盖 Requirement）。
- 活文档（删/改已不可执行的命令）：
  - `backend/README.md` §2.5（灌入口径 → 实时同步）
  - `docs/common/local-runbook.md`（删掉「已移除」之后的命令块）
  - `docs/backend/mysql-setup.md`（`app.ingest` 命令块、`--init-db --ingest` 参数表、特征重灌步骤）
  - `docs/repo/demo-script-sprint1.md`（演示脚本的灌数步骤）
  - `docs/backend/acceptance.md`（验收步骤）
  - `docs/common/test-strategy.md`（后端用例条数清单，`test_ingest.py` 已删）
  - `data_model/pipelines/expert/README.md`（灌库命令）
- 设计与契约文档里的旧口径（离线 CSV 灌库 / 方案 C 导入）：
  - `docs/design/diagrams.md`（图 1 的数据源节点与落库边）
  - `docs/design/architecture.md` §5 ③（离线训练交付物与入库路径）
  - `docs/design/database.md` §1（四表说明里的「A+C 写同一张表」）
  - `docs/design/sprint0-scope.md` §4（跨线接口 A+C 的措辞；三个冻结点不动）
  - `docs/common/glossary.md`（「A+C 交付」词条）
  - `docs/design/data-fields.md`（契约一升 1.6：**只改入库链路措辞**，列名、类型、索引、取值枚举一律不动）
- 归档件（`backend/scripts/evidence/**`、`docs/common/test-report-sprint2.md` 等**历史记录**）不改 —— 它们记录的是当时的事实。
- 代码：零改动（本 change 只动规格与文档）。

## 不做什么

- 不改任何已交付模型与预测口径。
- 不动历史证据档与归档 change。
- 不改契约一的字段定义（列名、类型、索引、取值枚举）与三个冻结点。
- 不补 `commit_label` 的运行时写入方（移除离线灌库后该表无写入方，属功能缺口，另开 change）。
- 不改 `model-coverage` / `predict-api` 的 Requirement（已被 `online-eight-model-selection` / `delivery-model-allowlist` 占用，同名 MODIFIED 会触发 CI 冲突检查）。
- 不把「实时同步」再设计一遍（`realtime-commit-sync` / `realtime-pr-prediction` 两个 change 已定义，本 change 只把落库纪律写进 `db-schema` 规格）。
