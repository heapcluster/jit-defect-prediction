# backend-spec-path-references — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/query-api/spec.md`、`specs/db-schema/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-21 ｜ 状态：进行中
> 用户故事：无（工程化）—— 纯路径/版本字符串修订，不改任何行为语义（看板行 18 后端线份额）
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. delta 起草（提案即交付物）

- [x] 1.1 `specs/query-api/spec.md` delta：3 处 `docs/contracts/*` 改指 `docs/backend/api-spec.md`（契约三 v1.5）与 `docs/model/feature-columns.md`（契约二），三条 requirement 的 Scenario 逐字保留 —— 交付物：`openspec/changes/backend-spec-path-references/specs/query-api/spec.md`
      —— 完成判据：delta 内 `grep -c docs/contracts` = 0 且与 main 现行版逐段比对仅路径/版本差异。完成：见本 change 目录
- [x] 1.2 `specs/db-schema/spec.md` delta：2 处改指 `docs/design/data-fields.md`（契约一 v1.5，与 main 文件头 `docs/design/data-fields.md:3` 对读核实）与 `docs/model/feature-columns.md`（契约二）—— 交付物：`openspec/changes/backend-spec-path-references/specs/db-schema/spec.md`
      —— 完成判据：同上。完成：见本 change 目录
- [x] 1.3 **（审阅后自查补入）** `specs/predict-api/spec.md` delta：`MODEL_DIR` 默认值旧路径 `data_model/models/` → `data_model/pipelines/expert/models/`（权威 = `backend/app/config.py:16`），「模型加载」requirement 的 SHALL 与两条 Scenario 逐字保留 —— 交付物：`openspec/changes/backend-spec-path-references/specs/predict-api/spec.md`
      —— 完成判据：delta 内 `data_model/models/`（带斜杠的旧目录形式）零命中，且与 main 现行版逐段比对仅该一处路径差异。完成：见本 change 目录。**成因**：#71 分包迁移后 PR #77 只改代码未同步规格（`git show --stat 2d52db5` 仅 `backend/app/config.py`），初版提案那句「`predict-api` 已核干净」只核了 `docs/contracts/*`，属我的核查漏项，已在 proposal / design 订正

## 2. 静态校验（本 PR 内完成）

- [x] 2.1 `openspec validate backend-spec-path-references --strict` 通过 —— 交付物：命令输出记录于本文件「测试与验证」§3
- [x] 2.2 语义零变化比对：`git diff team/main...HEAD -- openspec/changes/backend-spec-path-references/specs/` 逐段人工过一遍，确认除路径/版本字符串外无任何措辞、阈值、判定、Scenario 期望变化 —— 交付物：§3 证据行
- [ ] 2.3 现行规格旧引用清零扫描（**归档时执行**，现在必失败属预期）：cwd=仓库根，两条都要无输出
      ① `git grep -n "docs/contracts" -- openspec/specs/query-api openspec/specs/db-schema openspec/specs/predict-api`
      ② `git grep -n "data_model/models/" -- openspec/specs/predict-api`

## 3. 归档与同步（排在依赖之后）

- [ ] 3.1 等 `backend-time-range-semantics` 归档 PR 合入（design D3 顺序约束）—— 交付给：自己；形式：关注该 PR 状态。当前状态：归档 PR 已于 2026-10-21 提出 = **PR #84**（head `cadafc6`，前置 #75 已合入 main `07f4309`），待 sober-hub 审阅合入
- [ ] 3.2 归档本 change：`openspec archive backend-spec-path-references -y`，delta 落 `openspec/specs/query-api/spec.md`、`openspec/specs/db-schema/spec.md` 与 `openspec/specs/predict-api/spec.md` —— 交付给：自己；形式：归档 PR；同时跑 2.3 两条扫描并回填证据
- [ ] 3.3 归档 PR 内手工同步 `openspec/specs/db-schema/spec.md:4` 的 `## Purpose` 旧版本号「契约一 1.4」→「契约一 1.5」（delta 承载不到 Purpose 段） —— 交付物：归档 PR 的该处 diff；判据：cwd=仓库根 `git grep -n -E "契约(一|三) 1\.4" -- openspec/specs` 无输出。**范围收缩说明**：原列两处，其中 `openspec/specs/query-api/spec.md:4`「契约三 1.4」已由 `backend-time-range-semantics` 的归档 PR #84 声明并处理（其 tasks 3.3）；按 design D3 本 change 的归档必然排在 #84 之后，故本条不再重复声称，只保留 `db-schema` 一处，判据仍扫两处以防漏改
- [ ] 3.4 看板行 18 与周报同步：后端线份额翻「已完成」，注明 archive 12 份仍待 PO 在 Issue #65 裁决 —— 交付给：吕建江（飞书为本人操作）；形式：看板备注

## 测试与验证（强制板块）

> 分层口径见 `docs/common/test-strategy.md`：**单元测试**由写代码的人自己做、**集成测试**在大版本合并后做、**验收测试**在交付时做，非功能验证并行。
> 铁律：**勾了 tasks ≠ 功能合格，必须有可复现的运行证据。**
> 本 change 是纯路径/版本字符串修订（不改 Python 代码、不改契约冻结件、不改规格行为语义），单元 / 集成 / 验收三层**均不新增功能用例**，验证手段为「旧引用扫描 + 严格规格校验 + 语义逐字比对」三类静态检查；不适用之处逐节注明，不省略板块（与蒋励 `path-references-alignment` 同法）。
> 统一复现口径 —— **cwd：仓库根**；解释器：无需 Python（纯文档校验）。

### 1. 单元测试（本 change 新增/改动代码的作者负责 · 吕建江）

| 项 | 内容 |
|---|---|
| 覆盖对象 | 无代码改动 —— 不适用（本 change 只新增/修订 markdown） |
| 测试文件 | 不适用 |
| 用例数与结果 | 0 条 ｜ 不适用（无行为变化；后端全套 **100 条**在 main 上保持全绿即可，见 §2 —— 本文件初版写 93 条，PR #79 合入后基线已是 100 条，按现状刷新） |
| 复现命令 | cwd=`backend`：`python -m pytest tests/`（期望 `100 passed`，证明本 change 未波及代码路径 —— 本 change 不动 `backend/`，此项为护栏） |
| 正向用例 | 不适用（无新逻辑） |
| 异常 / 边界用例 | 不适用（无新逻辑） |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 与 `backend-time-range-semantics` 归档的落地顺序（design D3：同一规格文件的不同 requirement，排序防并发改动）；与蒋励 `path-references-alignment` 的文件集互斥性 |
| 测试文件 | 不适用（无跨模块运行时交互） |
| 用例数与结果 | 0 条 ｜ 静态检查代替：`git diff --name-only team/main...HEAD` 确认两 change 文件集零交集 |
| 复现命令 | cwd=仓库根：`git diff --name-only team/main...HEAD`（期望仅 `openspec/changes/backend-spec-path-references/**`，共 7 个文件：`.openspec.yaml` + 三份 delta + proposal / design / tasks。用 `team/main` 而不是本地 `main` —— 本地引用落后时会得出几百个文件的假 diff） |
| 关键断言 | 归档后 `openspec/specs/query-api/spec.md` 同时含时间区间语义（#62 delta）与新路径引用（本 delta），互不覆盖 |

### 3. 验收测试（交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | 本 change 三份 delta 共 6 条 requirement 的全部 Scenario —— 语义逐字未变，验收点即「引用可点开」 |
| 用例数与结果 | 5 条静态验收 ｜ 2 过 3 待归档时执行（2.3 的 ①② 两条扫描 + 3.3 Purpose 版本号） |
| 复现命令 / 步骤 | ① cwd=仓库根：`openspec validate backend-spec-path-references --strict`；② `openspec validate --all --strict`；③ 归档后：`git grep -n "docs/contracts" -- openspec/specs/query-api openspec/specs/db-schema openspec/specs/predict-api`（期望无输出）；④ 归档后：`git grep -n "data_model/models/" -- openspec/specs/predict-api`（期望无输出 —— 规格里的 `MODEL_DIR` 默认值与 `backend/app/config.py:16` 对齐）；⑤ 归档后：`git grep -n -E "契约(一\|三) 1\.4" -- openspec/specs/query-api openspec/specs/db-schema`（期望无输出，覆盖 Purpose 段；其中 `query-api` 首段由前置归档 PR #84 先行同步，本 PR 归档后复扫两处皆净 —— 判据写成扫两处正是为了不因两个 PR 分工而漏一处） |
| 证据归档 | 本文件 §5 执行证据行 + 归档 PR 描述 |

### 4. 非功能验证（本 change 触及则必填）

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 否 | 纯文档修订 |
| 安全 | 否 | 错误码语义未变，仅引用路径变化（`docs/backend/api-spec.md` 为现行冻结件 v1.5 本体） |
| 可靠 | 否 | 无运行时行为 |
| 易用 | 是（规格可读性） | 照 `AGENTS.md` 找契约不再扑空 —— 这正是本 change 的目的；验收命令见 §3 步骤③ |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| archive 12 份旧引用未改 | 看板行 18 与 Issue #65 原文（「归档记录不改」按 #54 先例）口径冲突，已在 #65 请 PO 裁决；默认不改 | 苏哲勋（裁决）→ 吕建江/蒋励（按线执行） | 裁决后另立 change |
| `openspec/config.yaml:35` 仍写「以 docs/contracts/ 为准」 | 按 #65 分工归蒋励（其 change `path-references-alignment` 范围） | 蒋励 | 随其 change |
| 现行规格旧引用与旧版本号未清（2.3、3.3） | delta 未归档前现行规格本就不变，扫描必失败；且 Purpose 段的版本号 OpenSpec delta 结构上承载不到，只能在归档 PR 手工改 —— 均排在归档时 | 吕建江 | 3.2 归档 PR（含 3.3） |
| 归档依赖 | design D3：必须晚于 `backend-time-range-semantics` 归档。前置已推进：PR #75 已合入 main（`07f4309`），该归档 PR 已提出 = **PR #84**（head `cadafc6`），待合入后本 change 才走 3.2 | 吕建江 | 2026-10-22/23 |

> 执行证据（2026-10-21，Windows 11，仓库根）：`openspec validate backend-spec-path-references --strict` → 通过；`openspec validate --all --strict` → 全绿（项数见 PR 描述）；`git diff --name-only main...HEAD` → 仅本 change 目录 5 个文件。归档后在本表追加扫描输出，不倒填。
> 审阅后复核（2026-10-21，苏哲勋在 `6edbe88` 提出 db-schema delta 的契约一版本应为 v1.5）：改正后 cwd=仓库根重跑 `openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`；版本对读命令 `grep -n "版本" docs/design/data-fields.md | head -1` → `> 状态：**已冻结** ｜ 版本 1.5 ｜ …`（`docs/design/data-fields.md:3`）。
> 依赖推进与分工收缩（2026-10-22 00:01，Windows 11，仓库根）：前置归档 PR 已提出 = **#84**（head `cadafc6`，#75 已合入 main `07f4309`），3.1 记录其状态；`query-api` 首段版本行由 #84 认领，tasks 3.3 相应收缩为 `db-schema` 一处（判据仍扫两处）。收缩后重跑：`openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`（本分支基线尚未含 #84 的归档出队，故项数与 #84 上的 17 不同，非异常）。
