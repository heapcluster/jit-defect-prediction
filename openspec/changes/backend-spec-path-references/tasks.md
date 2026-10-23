# backend-spec-path-references — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/query-api/spec.md`、`specs/db-schema/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-21 ｜ 更新：2026-10-24 ｜ 状态：delta 起草与静态校验完成；范围两次收缩（6 → 4 条 requirement，撤出与 #96/#97 撞车的两条）；PR #82 已 rebase 到 main `065c83a` 待复审，归档（3.2 / 3.3）待执行
> 用户故事：无（工程化）—— 纯路径/版本字符串修订，不改任何行为语义（看板行 18 后端线份额）
> 统一格式见 `docs/common/openspec-task-template.md`；**本文件末的「测试与验证」为强制板块，缺失视为提案不完整。**

## 1. delta 起草（提案即交付物）

- [x] 1.1 `specs/query-api/spec.md` delta：**2 处** `docs/contracts/*` 改指 `docs/backend/api-spec.md`（契约三 v1.5），两条 requirement（统一包络与错误码 / Swagger 实现镜像）的 Scenario 逐字保留 —— 交付物：`openspec/changes/backend-spec-path-references/specs/query-api/spec.md`
      —— 完成判据：delta 内 `grep -c docs/contracts` = 0 且与 main 现行版逐段比对仅路径/版本差异。完成：见本 change 目录。**2026-10-24 收缩**：初版还含第 3 处（活规格 `:72`「提交详情查询」里的 `docs/contracts/feature-columns.md`），因与 #97 的 MODIFIED delta 撞同一条 requirement 而撤出（design D6 补记）；#97 的文本已写成 `docs/model/feature-columns.md`，该处随它归档清零
- [x] 1.2 `specs/db-schema/spec.md` delta：2 处改指 `docs/design/data-fields.md`（契约一 v1.5，与 main 文件头 `docs/design/data-fields.md:3` 对读核实）与 `docs/model/feature-columns.md`（契约二）—— 交付物：`openspec/changes/backend-spec-path-references/specs/db-schema/spec.md`
      —— 完成判据：同上。完成：见本 change 目录
- [x] 1.3 **（2026-10-24 撤销）** ~~`specs/predict-api/spec.md` delta：`MODEL_DIR` 默认值旧路径 `data_model/models/` → `data_model/pipelines/expert/models/`~~ — 撤销理由：#96（`delivery-model-allowlist`，已合入 main `39aa2b7`）对**同一条「模型加载」requirement** 出了 MODIFIED delta，其中默认路径已是新值，且语义整体升级为 `feature_order.txt` 清单驱动。OpenSpec 的 MODIFIED 是整条覆盖，本 change 若后归档会把清单语义写回 glob 时代措辞（design D6）。交付物：`git rm` 掉本 change 的 `specs/predict-api/spec.md`；该处旧路径改由 #96 归档时落地，判据保留在 2.3 ②。**原自查结论仍成立**：#77 只改代码未同步规格是我的漏项（`git show --stat 2d52db5` 仅 `backend/app/config.py`），只是修复的落点换到了 #96

## 2. 静态校验（本 PR 内完成）

- [x] 2.1 `openspec validate backend-spec-path-references --strict` 通过 —— 交付物：命令输出记录于本文件「测试与验证」§3
- [x] 2.2 语义零变化比对：`git diff 11993e2 HEAD -- openspec/changes/backend-spec-path-references/specs/` 逐段人工过一遍，确认除路径/版本字符串外无任何措辞、阈值、判定、Scenario 期望变化 —— 交付物：§3 证据行
- [ ] 2.3 现行规格旧引用清零扫描（**归档时执行**，现在必失败属预期）：cwd=仓库根。判据按「谁负责哪一处」拆开，不写成一句笼统的「全部清零」，免得把别人 delta 的落地时机算到本 change 头上
      ① `git grep -n "docs/contracts" -- openspec/specs/db-schema` → 期望**无输出**（2 处全由本 change 落地）
      ② `git grep -n "docs/contracts" -- openspec/specs/query-api` → 本 change 归档后应由 3 命中降为 **1 命中**（只剩 `:72`「提交详情查询」那处，由 #97 的 delta 负责）；若 `on-demand-commit-prediction` 已先归档，则直接为 **0**。两种结果都记进证据，不按 0 硬凑
      ③ `git grep -n "data_model/models/" -- openspec/specs/predict-api` → 期望无输出，但**不由本 change 落地**：验的是 #96 `delivery-model-allowlist` 归档了没有；仍命中就另立 change 补（design D6）
      ④ `git grep -n "docs/contracts" -- openspec/specs/feature-extraction openspec/specs/model-delivery` → **属模型线，不计入本 change 判据**；2026-10-24 在 main `065c83a` 上实测 3 命中，已开 Issue #102 交蒋励
      ⑤ 归档前撞车复查：`grep -rl "^## MODIFIED Requirements" openspec/changes/*/specs/ | grep -v archive` 后逐文件列 `### Requirement:`，确认没有第二个未归档 change 改本 change 的那 4 条（design D6 补记的表就是这道检查的产物）

## 3. 归档与同步（排在依赖之后）

- [x] 3.1 等 `backend-time-range-semantics` 归档 PR 合入（design D3 顺序约束）—— **已满足**：PR #84 已合入，main `065c83a` 上存在 `openspec/changes/archive/2026-10-21-backend-time-range-semantics/`，且它认领的 `openspec/specs/query-api/spec.md:4` 已由「契约三 1.4」同步为「契约三 1.5」（2026-10-24 用 `git ls-tree` + `git show` 核实）。本 change 的归档不再被前置阻塞
- [ ] 3.2 归档本 change：`openspec archive backend-spec-path-references -y`，delta 落 `openspec/specs/query-api/spec.md` 与 `openspec/specs/db-schema/spec.md`（**不含 predict-api**，见 1.3 与 design D6）—— 交付给：自己；形式：归档 PR；同时跑 2.3 的 ①②③ 三条扫描并回填证据；归档前按 D6 再复查一次有无别的未归档 change 改这 5 条 requirement（「统一包络与错误码 / 提交详情查询 / Swagger 实现镜像 / 建表字段逐字对齐契约 / 特征列名与顺序」）
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
| 用例数与结果 | 0 条 ｜ 不适用（无行为变化；后端全套在 main 上保持全绿即可，见 §2 —— 护栏值随基线刷新：`11993e2` 93 条 → `e46624b` 100 条 → **`065c83a` 143 条**，三组数字各挂各自基线，不倒填历史） |
| 复现命令 | cwd=`backend`：`python -m pytest tests/` —— **本分支已 rebase 到 `065c83a`，2026-10-24 在本工作树实测 143 条全绿**（`--junitxml` 计数 `tests=143 failures=0 errors=0 skipped=0 time=3.898`；`git diff --name-only team/main HEAD -- backend/` 为空，即 `backend/` 与 main 逐字一致）。逐模块覆盖率见 `backend/scripts/evidence/coverage-2026-10-24.md`（PR #85）。本 change 不动 `backend/`，此项为护栏 |
| 正向用例 | 不适用（无新逻辑） |
| 异常 / 边界用例 | 不适用（无新逻辑） |

### 2. 集成测试（大版本合并后，由负责合入的一条线组织）

| 项 | 内容 |
|---|---|
| 集成范围 | 与 `backend-time-range-semantics` 归档的落地顺序（design D3：同一规格文件的不同 requirement，排序防并发改动 —— 该前置已随 PR #84 合入，见 3.1）；与蒋励 `path-references-alignment` 的文件集互斥性；**与 #96 `delivery-model-allowlist` 的 requirement 级撞车**（design D6，已按撤销 predict-api delta 消解） |
| 测试文件 | 不适用（无跨模块运行时交互） |
| 用例数与结果 | 0 条 ｜ 静态检查代替：① 文件集零交集；② 同名 requirement 撞车复查 |
| 复现命令 | cwd=仓库根：`git diff --name-only 065c83a HEAD`（`065c83a` = 本分支 rebase 后的基线，**不依赖任何 remote 名**；期望仅 `openspec/changes/backend-spec-path-references/**` 共 **6 个文件** —— 撤销 predict-api delta 后由 7 降为 6）。撞车复查：`grep -rln "### Requirement: 统一包络与错误码\|### Requirement: 提交详情查询\|### Requirement: Swagger 实现镜像\|### Requirement: 建表字段逐字对齐契约\|### Requirement: 特征列名与顺序" openspec/changes/*/specs/`，期望只命中本 change 自己。若要对着团队仓最新 main 比，先自备 remote：`git remote add team https://github.com/heapcluster/jit-defect-prediction.git && git fetch team main`，然后用 `team/main` 替换基线 sha |
| 关键断言 | 归档后 `openspec/specs/query-api/spec.md` 同时含时间区间语义（#62 delta，已随 #84 落地）与新路径引用（本 delta），互不覆盖；`openspec/specs/predict-api/spec.md` 的「模型加载」**只由 #96 的 delta 落地一次**，本 change 不参与，因此不存在把清单语义覆盖回 glob 措辞的路径 |

### 3. 验收测试（交付时，按 `specs/<cap>/spec.md` 的 Scenario 逐条走）

| 项 | 内容 |
|---|---|
| 验收依据 | 本 change 两份 delta 共 **4 条 requirement** 的全部 Scenario —— 语义逐字未变，验收点即「引用可点开」（初版为三份 delta / 6 条，`predict-api`「模型加载」与 `query-api`「提交详情查询」已按 1.3 与 design D6 撤出） |
| 用例数与结果 | 5 条静态验收 ｜ 2 过 3 待归档时执行（2.3 的扫描 + 3.3 Purpose 版本号） |
| 复现命令 / 步骤 | ① cwd=仓库根：`openspec validate backend-spec-path-references --strict`；② `openspec validate --all --strict`；③ 归档后跑 2.3 的 ①–⑤ 五条扫描，逐条回填**实际命中数**（`query-api` 那处的期望值取决于 #97 是否已归档，1 命中与 0 命中都如实记，不按 0 硬凑）；④ 归档后两条纯字符串扫描，期望均无输出：`git grep -n "契约一 1.4" -- openspec/specs` 与 `git grep -n "契约三 1.4" -- openspec/specs`（覆盖 Purpose 段；`query-api` 首段已由前置归档 PR #84 同步 —— 2026-10-24 在 main 上核实为「契约三 1.5」，判据写成两条正是为了不因两个 PR 分工而漏一处） |
| ④ 为什么不用扩展正则 | 本轮审阅（苏哲勋 `2d89a67`）指出原写法在表格单元格里必须写 `契约(一\|三)`，**从源文件复制执行时竖线被当字面量 → 零命中 = 假通过**。我实测三种备选：`-E "契约(一\|三) 1\.4"` 0 命中（坏）；`-E "契约[一三] 1[.]4"` 0 命中（也坏 —— git grep 的字符类按**字节**匹配多字节中文，同样漏）；`-E "契约. 1[.]4"` 0 命中（`.` 同理）。可用的是不带正则的两条纯字符串（上表④），实测命中 `db-schema:4` + `query-api:4` 两处旧标注 = 反例成立；列表项里那条无反斜杠的 `-E "契约(一|三) 1\.4"`（见 3.3）实测 2 命中、可用，但为免复制时被 Markdown 转义坑，统一改用纯字符串形式 |
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
| 归档依赖 | design D3：必须晚于 `backend-time-range-semantics` 归档。**已解除**：PR #84 已合入，main `065c83a` 上 `archive/2026-10-21-backend-time-range-semantics/` 存在、`query-api:4` 已是「契约三 1.5」 | 吕建江 | 3.2 归档 PR（不再被前置阻塞） |
| `predict-api` 的 `data_model/models/` 旧路径未清 | 本 change 撤销了该 delta（design D6：与 #96 撞同一条 requirement，后归档者会整体覆盖前者） | 苏哲勋/蒋励（`delivery-model-allowlist` 归档）+ 吕建江（判据） | 随 #96 归档清零；2.3 ② 保留扫描，命中即另立 change 补 |
| 模型线 3 处 `docs/contracts/` 死链（`feature-extraction:4`、`:13`、`model-delivery:14`） | 属模型线规格，本 change 按「一人一线」不动；蒋励 `path-references-alignment` 已随 #91 归档但判据没扫这个模式 | 蒋励 | **Issue #102**（2026-10-24 开），含逐处原文、`## Purpose` 段 delta 承载不到的提示、契约二版本 v1.0→v1.2 漂移 |
| `docs/repo/defect-records.md` N-03 仍写「CI 未落地（`.github/workflows` 为空）」 | #72 已合入（`95f572b`），main 上有 `.github/workflows/ci.yml`（含 Lint specifications / Test backend / Build frontend 等步骤） | 蒋励（该文件维护人） | 建议随下次缺陷记录更新订正；不属本 change，只在此留痕 |

> 执行证据（2026-10-21，Windows 11，仓库根）：`openspec validate backend-spec-path-references --strict` → 通过；`openspec validate --all --strict` → 全绿（项数见 PR 描述）；`git diff --name-only main...HEAD` → 仅本 change 目录 5 个文件。归档后在本表追加扫描输出，不倒填。
> 审阅后复核（2026-10-21，苏哲勋在 `6edbe88` 提出 db-schema delta 的契约一版本应为 v1.5）：改正后 cwd=仓库根重跑 `openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`；版本对读命令 `grep -n "版本" docs/design/data-fields.md | head -1` → `> 状态：**已冻结** ｜ 版本 1.5 ｜ …`（`docs/design/data-fields.md:3`）。
> 依赖推进与分工收缩（2026-10-22 00:01，Windows 11，仓库根）：前置归档 PR 已提出 = **#84**（head `cadafc6`，#75 已合入 main `07f4309`），3.1 记录其状态；`query-api` 首段版本行由 #84 认领，tasks 3.3 相应收缩为 `db-schema` 一处（判据仍扫两处）。收缩后重跑：`openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`（本分支基线尚未含 #84 的归档出队，故项数与 #84 上的 17 不同，非异常）。
> 自查扩面（2026-10-22 00:35，Windows 11，仓库根）：按苏哲勋对版本标注的意见把「同类缺陷」重扫一遍，补入第 6 处 —— `openspec/specs/predict-api/spec.md:10` 的 `MODEL_DIR` 旧默认路径（成因 = PR #77 只改代码未同步规格，`git show --stat 2d52db5` 只动了 `backend/app/config.py`）。重跑 `openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`。**更正本文件初版一处计数**：`git diff --name-only team/main...HEAD` 实为 6 个文件（初版证据行写「5 个」漏算 `.openspec.yaml`），加本次 predict-api delta 后现 = **7 个文件**，以命令输出为准。归档前扫描现状（按 2.3 预期仍失败）：`git grep -c docs/contracts -- openspec/specs/query-api openspec/specs/db-schema openspec/specs/predict-api` → query-api 3、db-schema 2、predict-api 0；`git grep -n "data_model/models/" -- openspec/specs/predict-api` → 1 命中（`spec.md:10`，本次要改的就是它）。
> 复现口径修订（2026-10-22 22:52，Windows 11，仓库根 · 应苏哲勋第二轮 `2d89a67` 的两项）：① 表格里的 `-E "契约(一\|三) 1\.4"` 换掉 —— 实测该串 0 命中（复制即字面量），备选 `-E "契约[一三] 1[.]4"` 与 `-E "契约. 1[.]4"` **同样 0 命中**（git grep 字符类/通配按字节匹配多字节中文），故改为两条无正则的纯字符串扫描，实测命中 `openspec/specs/db-schema/spec.md:4` 与 `openspec/specs/query-api/spec.md:4`（反例成立，归档后应零命中）。② 去掉对未声明 remote 的依赖：`git diff --name-only 11993e2 HEAD` → 7 个文件（`.openspec.yaml` + 三份 delta + proposal/design/tasks）；`git merge-base HEAD main` → `11993e2`，与本分支切出基线一致。③ §1 护栏命令标注基线 `e46624b`（100 passed），初版 93 条留在原句说明来自 `11993e2`，不覆盖。重跑：`openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 19 passed, 0 failed (19 items)`。
> rebase 与两次范围收缩（2026-10-24 02:45 前后，Windows 11，仓库根）：分支 rebase 到 main `065c83a`（含 #94/#95/#96/#97/#100/#99），`backend/` 与 main 逐字一致（`git diff --name-only team/main HEAD -- backend/` 无输出）；护栏 cwd=`backend` `python -m pytest tests/ -q --junitxml=…` → `tests=143 failures=0 errors=0 skipped=0 time=3.898`（计数取自 junitxml，本机 shell 会吞掉 pytest 末行汇总）。按 design D6 撤出两条与**已合入但未归档**的 change 撞车的 requirement：`git rm specs/predict-api/spec.md`（#96 改同一条「模型加载」）、从 `specs/query-api/spec.md` 删掉「提交详情查询」整段（#97 改同一条，其文本已写成 `docs/model/feature-columns.md` 且带回退语义）。change 目录由 7 个文件降为 **6 个**，requirement 由初版 6 条降为 **4 条**。
> 收缩后重跑：`openspec validate backend-spec-path-references --strict` → `Change 'backend-spec-path-references' is valid`；`openspec validate --all --strict` → `Totals: 25 passed, 0 failed (25 items)`；delta 内 `grep -rc "docs/contracts" openspec/changes/backend-spec-path-references/specs/` → db-schema 0、query-api 0。
> 归档前扫描现状（按 2.3 预期仍失败，逐条如实记，不按 0 硬凑）：① `git grep -c "docs/contracts" -- openspec/specs/db-schema` → **2**；② `-- openspec/specs/query-api` → **3**（本 change 只清其中 2 处，第 3 处 `:72` 待 #97 归档）；③ `git grep -c "data_model/models/" -- openspec/specs/predict-api` → **1**（待 #96 归档，不由本 change 落地）；④ `-- openspec/specs/feature-extraction openspec/specs/model-delivery` → **2 + 1 = 3**（模型线，Issue #102）；⑤ 撞车复查 `grep -rl "^## MODIFIED Requirements" openspec/changes/*/specs/ | grep -v archive` 后逐文件列 `### Requirement:`，全量结果见 design D6 补记的表 —— 本 change 剩下的 4 条（统一包络与错误码 / Swagger 实现镜像 / 建表字段逐字对齐契约 / 特征列名与顺序）确认无第二个未归档 change 触碰；#100 与 #99 对 `db-schema`/`predict-api` 都是 **ADDED**，不构成本条问题。
> 前置解除：3.1 已勾 —— PR #84 已合入，main 上存在 `openspec/changes/archive/2026-10-21-backend-time-range-semantics/`，且 `openspec/specs/query-api/spec.md:4` 已是「契约三 1.5」（`git ls-tree` + `git show` 核实）。
