# Design: backend-spec-path-references

## Context

#55 契约重组后，后端线现行规格残留 5 处 `docs/contracts/*` 引用（清单见 proposal）；契约三已随 #62 升 v1.5 进 main（`7844f8e`），规格里的「1.4」版本标注也需按现状钉准。看板行 18 要求「先立 change 再改，不动冻结件」。

**审阅后自查补入第 6 处**：`openspec/specs/predict-api/spec.md:10` 的 `MODEL_DIR` 默认值仍写 `data_model/models/`，代码现状是 `backend/app/config.py:16` 的 `data_model/pipelines/expert/models/`（#71 分包迁移后，PR #77 只改代码没同步规格）。同属「现行规格里的旧路径」，纳入本 change 一起收。

## Goals / Non-Goals

- Goals：后端线三份现行规格的旧路径清零；引用版本与契约现状一致；行为语义零变化。
- Non-Goals：不动契约冻结件本体；不动 archive 12 份（默认按 #65「归档记录不改」，PO 另裁再议）；不动 `openspec/config.yaml` 与模型线 5 份规格（蒋励 `path-references-alignment` 范围）。**订正**：初版此处写了「`predict-api` 已核无旧引用」，只核了 `docs/contracts/*`、漏了模型目录旧默认路径 —— 该处现已纳入本 change（第 6 处），不再声称它干净。

## Decisions

- **D1 只做后端线三份文件**：`query-api` + `db-schema` + `predict-api`（后者仅 `MODEL_DIR` 默认路径一处）。与蒋励同主题 change 按「一人一线」切分，文件集互斥，两 change 可并行推进、归档顺序互不阻塞（除 D3 的一条）。
- **D2 路径映射按 #55 重组结论表**：`api-format.md → docs/backend/api-spec.md`、`data-fields.md → docs/design/data-fields.md`、`feature-columns.md → docs/model/feature-columns.md`；**外加第 6 处的模型目录映射** `data_model/models/ → data_model/pipelines/expert/models/`（权威 = `backend/app/config.py:16`，`.env` 可覆盖见 `backend/.env.example:3`，`backend/README.md:76` 与 `docs/backend/README.md:17/:60` 已是新路径，规格是唯一漏网处）；版本标注写「契约三 v1.5 / 契约一 v1.5」现状值（两者文件头分别见 `docs/backend/api-spec.md:3`、`docs/design/data-fields.md:3`）；契约二在 main 现行规格里本就只按节引用（§2/§3）不带版本号，本次只换路径、不新增版本锚，避免扩大改动面。选「写死当前版本」而非「不写版本」：规格其余条目本就按版本引用契约（如「§3 逐字一致」），去掉版本反而丢判据；代价是契约再升版时要同步扫规格（tasks §3 已放扫描命令，这正是 #65 的根因修复）。
- **D3 归档排在 `backend-time-range-semantics` 之后**：两个 delta 改同一规格文件的不同 requirement（时间区间改「风险列表查询 / 趋势聚合查询」，本 change 改「统一包络与错误码 / 提交详情查询 / Swagger 实现镜像」），无语义冲突，排序只为避免同文件并发落地。
- **D4 验证用静态三件套**：旧路径全量扫描 + `openspec validate --all --strict` + 语义逐字比对（纯字符串修订不新增功能用例，与蒋励 change 同法；不适用项在「测试与验证」板块逐节注明，不省略板块）。
- **D5 版本标注的核对方式与工具边界**：每个写进规格的版本号都与契约文件头对读（`docs/backend/api-spec.md:3` = v1.5、`docs/design/data-fields.md:3` = v1.5、`docs/model/feature-columns.md:3` = v1.2），不凭记忆写版本。**本轮审阅（苏哲勋，`6edbe88`）指出 db-schema delta 曾把契约一写成 v1.4 —— 属实，已按文件头改正。** 另：`## Purpose` 段的两处旧版本号（`db-schema:4`、`query-api:4`）不在 requirement 里，OpenSpec 的 delta 结构承载不到，只能排进归档 PR 手工同步并单列判据（tasks 3.3），这是工具能力边界，记下来而不是假装 delta 已覆盖。两处的分工已核实，不重复声称：`query-api:4` 归前置归档 PR **#84**（该 change 自己的 tasks 3.3 声明），本 change 按 D3 必在其后归档，故只认领 `db-schema:4`；判据仍一次扫两处，正是为了避免「两个 PR 各认一半、结果都没认」这种漏口。

## Risks / Trade-offs

- 若 PO 裁「archive 一起改」→ 本 change 范围扩大：archive 是历史快照，届时单独补 change 处理，不在本 change 里混（保持「规格现状修订」与「历史记录改写」两类审计清晰）。
- 版本标注漂移风险（契约升到 1.6 而规格还写 1.5）→ 契约升版流程里顺手跑一次对照：cwd=仓库根，`git grep -n -E "契约一 v|契约二 v|契约三 v" -- openspec/specs` 与三份契约文件头的「版本」行对读，不一致就在同一个升版 PR 里同步规格。tasks 2.3 的命令只清旧路径（`docs/contracts`），不含版本号，两者互补不重复。

## Migration

无数据/代码迁移；delta 于 `openspec archive` 时落到现行规格；回滚 = revert 归档提交。
