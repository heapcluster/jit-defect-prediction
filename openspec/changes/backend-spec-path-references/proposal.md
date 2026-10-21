# Proposal: backend-spec-path-references

## Why

PR #55 把三条契约重组进四线目录后，`docs/contracts/` 已不存在，但**后端线现行规格仍有 5 处指向已删目录**：`openspec/specs/query-api/spec.md` 3 处（错误码来源 `docs/contracts/api-format.md` 1.4 ×2、详情特征键名 `docs/contracts/feature-columns.md` ×1）、`openspec/specs/db-schema/spec.md` 2 处（建表依据 `docs/contracts/data-fields.md` 1.4、特征列名 `docs/contracts/feature-columns.md` §2/§3）。任何人照 `AGENTS.md` 硬红线打开现行规格找契约，都会扑空 —— 规格自己在违反「唯一来源」。这是看板行 18「openspec/specs 与 archive 中旧路径修订」的**后端线部分**；模型线部分蒋励已立 change `path-references-alignment`（同主题、不同文件集，互不重叠）。

**审阅后自查补入的第 6 处（成因不同、缺陷同类）**：`openspec/specs/predict-api/spec.md:10` 仍写 `MODEL_DIR` 默认 `data_model/models/`，而代码现状是 `backend/app/config.py:16` 的 `data_model/pipelines/expert/models/`。旧路径不是 #55 造成的，是 **#71 分包迁移后我在 PR #77 只改了代码、没同步规格**（`git show --stat 2d52db5` → 仅 `backend/app/config.py | 2 +-`）。这正是 `AGENTS.md` 硬红线 2「改代码必须同步改规格」要防的那种不一致，23 号验收会被直接判缺陷，所以并入本 change 一起收，不另开第四个 PR。

## What Changes

- 上述 5 处引用改指现行权威路径，版本标注按契约现状钉准：  - `docs/contracts/api-format.md` 1.4 → `docs/backend/api-spec.md`（契约三 **v1.5**，已随 #62 进 main `7844f8e`）
  - `docs/contracts/data-fields.md` 1.4 → `docs/design/data-fields.md`（契约一 **v1.5**，2026-10-15 Camel 切换补齐，版本行 `docs/design/data-fields.md:3`）
  - `docs/contracts/feature-columns.md` → `docs/model/feature-columns.md`（契约二）
- **+1 处模型目录旧默认路径**（自查补入，成因 = #77 只改代码未改规格）：`openspec/specs/predict-api/spec.md:10` 的 `data_model/models/` → `data_model/pipelines/expert/models/`（权威现状见 `backend/app/config.py:16`；`.env` 的 `MODEL_DIR` 仍可覆盖，见 `backend/.env.example:3`）。同样是**只换路径字符串**，该 requirement 的 SHALL/Scenario 逐字不动。
- 另有 **2 处旧版本号在规格 `## Purpose` 段**（`openspec/specs/db-schema/spec.md:4`「契约一 1.4」、`openspec/specs/query-api/spec.md:4`「契约三 1.4」）：OpenSpec 的 delta 只承载 requirement，Purpose 行改不到，故排在归档时手工同步并在同一 PR 出证（tasks 3.3），不假装 delta 已覆盖。**两处分工已核实**：`query-api:4` 由前置归档 PR #84（`backend-time-range-semantics` 的 tasks 3.3）处理，本 change 按 D3 必在其后归档，故本 PR 只认领 `db-schema:4`，判据仍扫两处。
- **纯路径/版本字符串修订**：SHALL/MUST 措辞、阈值、判定、Scenario 期望一律逐字保留，不改任何行为语义。
- 不做：不动冻结件本体（`docs/backend/api-spec.md` 等不在本 change 范围）、不动 archive（默认按 #65「归档记录不改」，若 PO 另裁再立 change）、不动 `openspec/config.yaml` 与模型线 specs（蒋励 `path-references-alignment` 范围）。**订正我先前的一句**：初版写过「`predict-api` 已核干净不涉及」—— 那句只核了 `docs/contracts/*`，漏了模型目录旧默认路径；现按上面第 6 处纳入，不再声称它干净。

## Capabilities

- New: （无）
- Modified: `query-api`（统一包络与错误码 / 提交详情查询 / Swagger 实现镜像 三条 requirement，仅引用路径与版本变化）、`db-schema`（建表字段逐字对齐契约 / 特征列名与顺序 两条 requirement，同上）、`predict-api`（模型加载 一条 requirement，仅 `MODEL_DIR` 默认路径字符串变化）—— 合计 **6 条 requirement**

## Impact

- 规格：`openspec/specs/query-api/spec.md`、`openspec/specs/db-schema/spec.md`、`openspec/specs/predict-api/spec.md`（delta 于归档时落地；`## Purpose` 段版本行 delta 承载不到，`db-schema:4` 由 tasks 3.3 在本 change 归档 PR 手工同步，`query-api:4` 已由前置归档 PR #84 处理）
- 代码：无；契约冻结件：无；数据库：无
- 看板行 18（吕建江 + 蒋励）：本 change 覆盖后端线份额；archive 12 份是否改待 PO 在 Issue #65 裁决
- 顺序约束：本 change 的归档必须排在 `backend-time-range-semantics` 归档**之后**（两者改同一规格文件的不同 requirement，排序只为避免同文件并发改动，无语义冲突）
