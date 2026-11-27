# Design: backend-spec-path-references

## Context

#55 契约重组后，后端线现行规格残留 5 处 `docs/contracts/*` 引用（清单见 proposal）；契约三已随 #62 升 v1.5 进 main（`7844f8e`），规格里的「1.4」版本标注也需按现状钉准。看板行 18 要求「先立 change 再改，不动冻结件」。

**第 6 处已撤销（2026-10-24）**：`openspec/specs/predict-api/spec.md` 的「模型加载」requirement 里 `MODEL_DIR` 默认值仍写旧路径 `data_model/models/`（成因是 #71 分包迁移后 PR #77 只改代码没同步规格）。本 change 初版把它收了，但 #96（`delivery-model-allowlist`，已合入 `39aa2b7`）对**同一条 requirement** 出了 MODIFIED delta，且其中默认路径已经是 `data_model/pipelines/expert/models/`。两份 delta 改同一条 requirement 时，后归档者整体覆盖先归档者 —— 本 change 的文本是 glob 时代措辞，若排在 #96 之后归档就会把清单语义写回旧版，活规格与 `backend/app/model_registry.py` 现状不符。故撤销，见 D6。

**另核出模型线 3 处同类死链**（`feature-extraction/spec.md:4`、`:13`、`model-delivery/spec.md:14`）：按「一人一线」不并入本 change，已开 Issue #102 交模型线，其中一处还在 `## Purpose` 段（delta 承载不到，与 D5 同类）且带过期版本号 v1.0（契约二文件头现为 v1.2）。

## Goals / Non-Goals

- Goals：后端线两份现行规格（`query-api`、`db-schema`）的旧路径清零；引用版本与契约现状一致；行为语义零变化。
- Non-Goals：不动契约冻结件本体；不动 archive 12 份（默认按 #65「归档记录不改」，PO 另裁再议）；不动 `openspec/config.yaml` 与模型线规格（蒋励 `path-references-alignment` 范围，已随 #91 归档，剩余 3 处死链走 Issue #102）；**不动 `predict-api`**（#96 的 delta 已覆盖同一条 requirement，见 D6）。**订正**：初版此处写「`predict-api` 已核无旧引用」，只核了 `docs/contracts/*`、漏了模型目录旧默认路径；第二版把它纳入本 change；现按 D6 撤销。三次口径都留痕，不悄悄改。

## Decisions

- **D1 只做后端线两份文件**：`query-api` + `db-schema`（初版含 `predict-api`，按 D6 撤销）。与蒋励同主题 change 按「一人一线」切分、文件集互斥；但**文件集互斥不足以保证互不阻塞** —— 两个 change 的 delta 可以指向同一条 requirement（本 change 与 #96 就撞在 `predict-api` 的「模型加载」上），所以归档顺序必须逐 requirement 核，不能只按文件名判，见 D6。
- **D2 路径映射按 #55 重组结论表**：`api-format.md → docs/backend/api-spec.md`、`data-fields.md → docs/design/data-fields.md`、`feature-columns.md → docs/model/feature-columns.md`；**模型目录映射** `data_model/models/ → data_model/pipelines/expert/models/`（权威 = `backend/app/config.py:16`，`.env` 可覆盖见 `backend/.env.example:3`）**不由本 change 落地**，改由 #96 的 delta 携带（D6）；版本标注写「契约三 v1.5 / 契约一 v1.5」现状值（两者文件头分别见 `docs/backend/api-spec.md:3`、`docs/design/data-fields.md:3`）；契约二在 main 现行规格里本就只按节引用（§2/§3）不带版本号，本次只换路径、不新增版本锚，避免扩大改动面。选「写死当前版本」而非「不写版本」：规格其余条目本就按版本引用契约（如「§3 逐字一致」），去掉版本反而丢判据；代价是契约再升版时要同步扫规格（tasks §3 已放扫描命令，这正是 #65 的根因修复）。
- **D3 归档排在 `backend-time-range-semantics` 之后**：两个 delta 改同一规格文件的不同 requirement（时间区间改「风险列表查询 / 趋势聚合查询」，本 change 改「统一包络与错误码 / 提交详情查询 / Swagger 实现镜像」），无语义冲突，排序只为避免同文件并发落地。
- **D4 验证用静态三件套**：旧路径全量扫描 + `openspec validate --all --strict` + 语义逐字比对（纯字符串修订不新增功能用例，与蒋励 change 同法；不适用项在「测试与验证」板块逐节注明，不省略板块）。
- **D5 版本标注的核对方式与工具边界**：每个写进规格的版本号都与契约文件头对读（`docs/backend/api-spec.md:3` = v1.5、`docs/design/data-fields.md:3` = v1.5、`docs/model/feature-columns.md:3` = v1.2），不凭记忆写版本。**本轮审阅（苏哲勋，`6edbe88`）指出 db-schema delta 曾把契约一写成 v1.4 —— 属实，已按文件头改正。** 另：`## Purpose` 段的两处旧版本号（`db-schema:4`、`query-api:4`）不在 requirement 里，OpenSpec 的 delta 结构承载不到，只能排进归档 PR 手工同步并单列判据（tasks 3.3），这是工具能力边界，记下来而不是假装 delta 已覆盖。两处的分工已核实，不重复声称：`query-api:4` 归前置归档 PR **#84**（该 change 自己的 tasks 3.3 声明），本 change 按 D3 必在其后归档，故只认领 `db-schema:4`；判据仍一次扫两处，正是为了避免「两个 PR 各认一半、结果都没认」这种漏口。

- **D6 两个 change 的 delta 撞同一条 requirement 时，由语义更完整的一方落地（本 change 让位给 #96）**：OpenSpec 的 MODIFIED delta 是**整条 requirement 覆盖**，不是逐行 patch。本 change 与 #96（`delivery-model-allowlist`，已合入 `39aa2b7`）都改 `predict-api` 的「模型加载」：本 change 只换一个路径字符串、保留 glob 时代的「加载 `.pkl` 并建立注册表」措辞；#96 既带了同一个正确路径，又把语义升级为 `feature_order.txt` 清单驱动。两者的归档时点各自跟随自己的 PR，顺序不可控；**若本 change 后归档，就会把 #96 的清单语义整体覆盖回旧措辞** —— 那比留着旧路径更糟：旧路径是死链、一打开就发现，语义回退却是「看起来对」的规格，与 `backend/app/model_registry.py` 现状悄悄不符。所以撤销本 change 的 `specs/predict-api/spec.md`，让 #96 单方落地。**判据不撤**：tasks 2.3 仍扫 `data_model/models/`，归档时命中即说明 #96 未归档或被覆盖，需另立 change 补。
  通用防线（写下来给下一个 change 用）：出 delta 前先 `grep -rn "### Requirement: <同名标题>" openspec/changes/*/specs/` 看有没有别的**未归档** change 改同一条 requirement；有就约定先后或合并到一方，别各写一份等着归档顺序决定谁对。本 change 与蒋励的 `path-references-alignment` 之所以没撞，是因为按文件切分刚好互斥，那是运气不是机制。
- **D6 补记：同一轮复查又抓到第二处撞车，本 change 再撤一条 requirement**（2026-10-24）。按上面的通用防线把 main `065c83a` 上所有**未归档** change 的 MODIFIED requirement 全列了一遍：

  | capability | requirement | 谁在改 |
  |---|---|---|
  | `db-schema` | 建表字段逐字对齐契约 / 特征列名与顺序 | 本 change（唯一） |
  | `db-schema` | MySQL SQL 建表入口与元数据等价 | #100，**ADDED**，不撞 |
  | `query-api` | 统一包络与错误码 / Swagger 实现镜像 | 本 change（唯一） |
  | `query-api` | **提交详情查询** | **#97 `on-demand-commit-prediction`（已合入 `4dc50aa`、未归档）** ← 与本 change 初版撞 |
  | `predict-api` | **模型加载** | **#96 `delivery-model-allowlist`（已合入 `39aa2b7`、未归档）** ← 与本 change 初版撞 |
  | `predict-api` | 在线预测入口 / 预测数据缺失错误 | #97（与 #96 的「模型加载」不同条，不撞） |
  | `predict-api` | 仓库模型模块可导入与加载失败汇总 | #99，**ADDED**，不撞 |
  | `model-coverage` 等 5 条 | — | 蒋励 `path-references-alignment`（PR #91 待合），与本 change 文件集互斥 |

  「提交详情查询」的处置与 predict-api 同理但更明确：#97 的 delta 文本**已经把 `docs/contracts/feature-columns.md` 写成 `docs/model/feature-columns.md`**，并新增了「在线模型与历史默认模型不同 → 回退到该提交已有模型中版本序最新一条」的语义与 Scenario（对应 `backend/app/api/commits.py:136-141`）。本 change 那条只是换路径字符串、且基于旧文本，后归档就会把回退语义抹掉。因此本 change 的 `query-api` delta 只留「统一包络与错误码」与「Swagger 实现镜像」，`query-api:72` 的死链随 #97 归档清零 —— 活规格最终结果一样，但不会出现语义回退。**本 change 的 requirement 数由初版 6 条收缩为 4 条。**
  顺带把这次复查的方法固化：归档任何 change 前，先跑一遍上面那张表的生成命令（`grep -rl "^## MODIFIED Requirements" openspec/changes/*/specs/` 后逐文件列 `### Requirement:`），确认没有第二个未归档 change 改同一条；CI 的 `openspec validate --specs --strict` 查不出这种撞车（两份 delta 各自都合法）。

## Risks / Trade-offs

- 若 PO 裁「archive 一起改」→ 本 change 范围扩大：archive 是历史快照，届时单独补 change 处理，不在本 change 里混（保持「规格现状修订」与「历史记录改写」两类审计清晰）。
- 版本标注漂移风险（契约升到 1.6 而规格还写 1.5）→ 契约升版流程里顺手跑一次对照：cwd=仓库根，`git grep -n -E "契约一 v|契约二 v|契约三 v" -- openspec/specs` 与三份契约文件头的「版本」行对读，不一致就在同一个升版 PR 里同步规格。tasks 2.3 的命令只清旧路径（`docs/contracts`），不含版本号，两者互补不重复。
- **同类缺陷的复发风险（已两次实证）**：① #77 改 `MODEL_DIR` 默认值时只改代码没同步规格，留下 `predict-api` 的旧路径；② 2026-10-24 在 main `065c83a` 上复查又核出模型线 3 处 `docs/contracts/` 死链（Issue #102），而蒋励的 `path-references-alignment` 刚随 #91 归档、其复扫判据扫的是 `changes/<name>/` 形式、没扫这个模式 —— 说明「改代码必须同步改规格」这条硬红线只靠人跑扫描确实会漏，而且**漏网会跨线复发**。本 change 的防线是 tasks 2.3 的两条扫描（人跑）。根治点在 CI：#72 已合入 main（`95f572b`），`.github/workflows/ci.yml` 现有 Checkout / Setup Node / Setup Python / Install frontend deps / Install Ruff / Install OpenSpec / Lint frontend / Lint Python / **Lint specifications（`openspec validate --specs --strict --no-interactive`）** / Test CI contract / Test backend / Test frontend / Test data model / Build frontend / Build Python 各步骤，其中 `openspec validate` 只校验 delta 结构、**不校验规格正文里引用的路径是否存在**。建议加一条死链检查（把 `openspec/specs/**` 与 `docs/**` 里的 `docs/...`、`data_model/...`、`backend/...` 相对路径抽出来逐个 `test -e`）；不在本 change 范围，我只把缺口点出来，同一建议也写在 Issue #102 末尾。

## Migration

无数据/代码迁移；delta 于 `openspec archive` 时落到现行规格；回滚 = revert 归档提交。
