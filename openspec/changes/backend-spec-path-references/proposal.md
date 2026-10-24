# Proposal: backend-spec-path-references

## Why

PR #55 把三条契约重组进四线目录后，`docs/contracts/` 已不存在，但**后端线现行规格仍有 5 处指向已删目录**：`openspec/specs/query-api/spec.md` 3 处（错误码来源 `docs/contracts/api-format.md` 1.4 ×2、详情特征键名 `docs/contracts/feature-columns.md` ×1）、`openspec/specs/db-schema/spec.md` 2 处（建表依据 `docs/contracts/data-fields.md` 1.4、特征列名 `docs/contracts/feature-columns.md` §2/§3）。任何人照 `AGENTS.md` 硬红线打开现行规格找契约，都会扑空 —— 规格自己在违反「唯一来源」。这是看板行 18「openspec/specs 与 archive 中旧路径修订」的**后端线部分**；模型线部分蒋励已立 change `path-references-alignment`（同主题、不同文件集，互不重叠）。

**第 6 处已撤销，改由 #96 的 delta 落地**：`openspec/specs/predict-api/spec.md` 的「模型加载」requirement 里 `MODEL_DIR` 默认值仍写旧路径 `data_model/models/`（成因是 #71 分包迁移后我在 PR #77 只改代码没同步规格，`git show --stat 2d52db5` → 仅 `backend/app/config.py | 2 +-`）。本 change 初版把它一并收了，但 **#96（`delivery-model-allowlist`，已合入 main `39aa2b7`）对同一条 requirement 出了 MODIFIED delta**，其中默认路径已经写成 `data_model/pipelines/expert/models/`，并把加载语义整体改成 `feature_order.txt` 清单驱动。两份 delta 改同一条 requirement，谁后归档谁覆盖前者：本 change 若排在 #96 之后归档，就会把清单语义**退回**成 glob 时代的措辞，活规格与 `backend/app/model_registry.py` 现状不符（正是硬红线 2 要防的那种不一致，只是换成了由归档顺序触发）。因此撤销本 change 的 `specs/predict-api/spec.md` delta，该处旧路径由 `delivery-model-allowlist` 归档时一并清零；本 change 只保留后端线另两份文件（`query-api` + `db-schema`，共 5 处死链）。**残留依赖**：若 `delivery-model-allowlist` 最终未归档，`predict-api` 那处旧路径需另立 change 补；tasks 2.3 保留对它的扫描判据，归档时一验就知道有没有漏。

**另核出 3 处同类死链，属模型线、不在本 change 范围**：`openspec/specs/feature-extraction/spec.md:4`、`:13` 与 `openspec/specs/model-delivery/spec.md:14` 仍指向 `docs/contracts/feature-columns.md`。蒋励的 `path-references-alignment`（随 #91 归档）改过 `feature-extraction`，但它的判据扫的是 `changes/<change-name>/` 形式旧引用，没扫 `docs/contracts/`，所以漏网。已开 **Issue #102** 交模型线，含逐处原文、`## Purpose` 段 delta 承载不到的提示、以及 `feature-columns.md` 文件头现为 v1.2 而该处仍写 v1.0 的版本漂移。

## What Changes

- 上述 5 处死链引用改指现行权威路径，版本标注按契约现状钉准，但**其中 1 处不由本 change 的 delta 落地**（见下条）：
  - `docs/contracts/api-format.md` 1.4 → `docs/backend/api-spec.md`（契约三 **v1.5**，已随 #62 进 main `7844f8e`）
  - `docs/contracts/data-fields.md` 1.4 → `docs/design/data-fields.md`（契约一 **v1.5**，2026-10-15 Camel 切换补齐，版本行 `docs/design/data-fields.md:3`）
  - `docs/contracts/feature-columns.md` → `docs/model/feature-columns.md`（契约二，文件头版本 **v1.2**）
- **`query-api` 的「提交详情查询」这一处撤出本 change，由 #97 的 delta 携带**：活规格 `openspec/specs/query-api/spec.md:72` 的 `docs/contracts/feature-columns.md` 死链在「提交详情查询」requirement 内，而 **#97（`on-demand-commit-prediction`，已合入 `4dc50aa`、change 尚未归档）对同一条 requirement 出了 MODIFIED delta，其文本已经写成 `docs/model/feature-columns.md`**，还新增了「在线模型与历史默认模型不同」的回退语义与 Scenario。OpenSpec 的 MODIFIED 是整条覆盖，本 change 若后归档会把 #97 的回退语义抹掉（活规格与 `backend/app/api/commits.py:136-141` 的实现不符）。故本 change 的 `query-api` delta 只保留「统一包络与错误码」（`:10`）与「Swagger 实现镜像」（`:119`）两条，`:72` 那处随 #97 归档清零；tasks 2.3 的判据按此拆分。
- **撤销 predict-api 那一处**（初版自查补入的「第 6 处」）：`openspec/specs/predict-api/spec.md` 的 `data_model/models/` → `data_model/pipelines/expert/models/` 已由 #96 的 MODIFIED delta 覆盖（同一条「模型加载」requirement，默认路径与清单语义一起改）。本 change 不再出这份 delta，避免归档顺序把 #96 的清单语义覆盖回旧措辞；判据仍留在 tasks 2.3，归档后扫活规格确认零命中。
- 另有 **2 处旧版本号在规格 `## Purpose` 段**（`openspec/specs/db-schema/spec.md:4`「契约一 1.4」、`openspec/specs/query-api/spec.md:4`「契约三 1.4」）：OpenSpec 的 delta 只承载 requirement，Purpose 行改不到，故排在归档时手工同步并在同一 PR 出证（tasks 3.3），不假装 delta 已覆盖。**两处分工已核实**：`query-api:4` 由前置归档 PR #84（`backend-time-range-semantics` 的 tasks 3.3）处理，本 change 按 D3 必在其后归档，故本 PR 只认领 `db-schema:4`，判据仍扫两处。
- **纯路径/版本字符串修订**：SHALL/MUST 措辞、阈值、判定、Scenario 期望一律逐字保留，不改任何行为语义。
- 不做：不动冻结件本体（`docs/backend/api-spec.md` 等不在本 change 范围）、不动 archive（默认按 #65「归档记录不改」，若 PO 另裁再立 change）、不动 `openspec/config.yaml` 与模型线 specs（蒋励 `path-references-alignment` 范围，其归档已在 PR #91 提出、**尚未合入**；剩下的模型线 3 处死链走 Issue #102）。**订正我先前的两句**：① 初版写过「`predict-api` 已核干净不涉及」—— 那句只核了 `docs/contracts/*`，漏了模型目录旧默认路径；② 第二版把它纳入本 change（第 6 处）—— 现又撤销，因为 #96 对同一条 requirement 出了 delta 且已带上正确路径，两份 delta 并存会因归档顺序互相覆盖。两句都记在这里，不悄悄改口。

## Capabilities

- New: （无）
- Modified: `query-api`（统一包络与错误码 / Swagger 实现镜像 **两条** requirement，仅引用路径与版本变化）、`db-schema`（建表字段逐字对齐契约 / 特征列名与顺序 两条 requirement，同上）—— 合计 **4 条 requirement**。范围两次收缩都留痕：初版为 6 条（另含 `predict-api` 的「模型加载」与 `query-api` 的「提交详情查询」），因分别与 **#96**、**#97** 的 MODIFIED delta 撞同一条 requirement 而撤出，理由见上条与 design D6

## Impact

- 规格：`openspec/specs/query-api/spec.md`、`openspec/specs/db-schema/spec.md`（delta 于归档时落地；`## Purpose` 段版本行 delta 承载不到，`db-schema:4` 由 tasks 3.3 在本 change 归档 PR 手工同步，`query-api:4` 已由前置归档 PR #84 处理）。`openspec/specs/predict-api/spec.md` **不在本 change 范围**，其旧路径随 `delivery-model-allowlist`（#96）归档落地；模型线 3 处死链见 Issue #102
- 代码：无；契约冻结件：无；数据库：无
- 看板行 18（吕建江 + 蒋励）：本 change 覆盖后端线份额；archive 12 份是否改待 PO 在 Issue #65 裁决
- 顺序约束：本 change 的归档必须排在 `backend-time-range-semantics` 归档**之后**（两者改同一规格文件的不同 requirement，排序只为避免同文件并发改动，无语义冲突）
