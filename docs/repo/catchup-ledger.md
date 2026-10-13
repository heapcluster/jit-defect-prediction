# 进度追平台账

> 版本 1.19 ｜ 创建 2026-10-05 ｜ 更新 2026-10-13 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> 周期口径：Sprint 0 = 9/11 – 10/2（已收官）；Sprint 1 = 10/2 – 10/23，10/23 课上验收。

## 0. 这份台账管什么

周报口径与仓库实证之间目前存在差距，差距只记在这一处：每项写清验收标准与证据位置，**完成一项就回填一行「✅ 日期 + 证据链接」**。台账清零，周报口径与仓库即重新一致。

任务的日常状态仍以飞书看板为准（`repo/collaboration.md` §5.2「状态判定」）。本台账不另造第三套任务清单：能对应看板行的尽量对应看板行，看板暂无对应行的事项以 GitHub Issue / PR 或 Git 提交为据（如部分跨线协办项、仓库侧已完成但看板未同步的项）；看板管「现在谁在做什么」，本台账管「补齐实证还差什么」。

## 1. 口径说明

1. 0911 / 0918 / 0925 三份周报的「下周计划」按"下一周的本周计划"统一改写：计划写在开工之前，进度一律从 0 起记；各周实际完成情况以看板与 Git 证据为准。
2. 0918 周报总结中"p95、p99"两个分位数是补记，**数值尚未核实**，以压测日志为准（见 L2）。
3. 周报重写前的原表明细未再保留备份，历史结论以 Git 提交与看板记录为准。
4. 0911 / 0918 / 0925 三份「本周总结」里挂的待改进项已逐条核对，仍未闭合的登记进 §2（J6、J7、S5–S7、L4）；openspec 实测：`model-expansion` 剩 tasks 4.4、`nfr-evidence-scripts` 剩 4.1 / 4.3 / 4.4、已归档的 `2026-09-19-data-collection-and-szz-labeling` 剩 5.4 未勾 —— 未勾即不算完成（课程原文：change 中的任务完成不等于功能合格）。

## 2. 按人分工的追平任务

### 蒋励（组长 / SM · 数据与模型线，兼公共文档统稿）

| # | 任务 | 验收标准与证据 | 状态 | 完成记录 |
|---|---|---|---|---|
| J1 | 端到端链路演示准备：一条提交走完「风险列表 → 详情归因 → 趋势看板」，做演示脚本 + 录屏，作为 Sprint 1（10/23）课上验收主证据 | 含正向验收 + 至少一项异常输入验证；录屏与脚本入库 `docs/` 或 Issue 附链 | 进行中 | ✅ 2026-10-09 演示脚本文档已建 `repo/demo-script-sprint1.md`；录屏待系统实跑后补 |
| J2 | 归档 change model-expansion：先补勾 tasks 4.4（PR 链接 + 非作者审阅记录；代码已由 PR #42 合入），再跑 `openspec archive` | `openspec validate --all --strict` 通过；`openspec/specs/` 收入对应需求 | 已完成 | ✅ 2026-10-10 ｜ 已补勾 tasks 4.4 并 `openspec archive`，`model-coverage` 规格入库（`openspec/specs/`）；依据 commit `8c1e919` |
| J3 | 仓库卫生：删除陈旧分支 `fix/model/delivery-list-wording`；本地 origin 从 `jolly326` 统一到 `heapcluster` | `git fetch` 走团队仓库正常；`git branch -a` 无陈旧分支 | 已完成 | ✅ 2026-10-10 ｜ 远程分支 `fix/model/delivery-list-wording` 经查已不存在（当前 fix/ 仅 `fix/backend/explain-real-models`）；`git remote -v` 显示 origin 已指向 `heapcluster`，仓库卫生达标 |
| J4 | 周报常态化：1009 / 1016 / 1023 三份按周五晚提交，写实到每人并附佐证材料 | 三份周报链接；内容与看板、Git 记录对得上 | 未开始 | — |
| J5 | 每周五 17:00 前收各人供稿并统稿，提交前对账：周报 = 看板 = Git 三处同口径 | 每周周报留痕 | 进行中 | 常态项 |
| J6 | 补勾已归档 change `2026-09-19-data-collection-and-szz-labeling` 的 5.4「回飞书看板更新任务状态」 | 该 change 的 tasks 全勾；看板对应任务状态已是真实状态 | 已完成 | ✅ 2026-10-09 已归档 change 5.4 已勾选（tasks 全勾）；飞书看板对应行状态已更新 |
| J7 | 四项附加功能（G1-1 缺陷可视化定位、G1-2 高质量修复建议、G1-3 公开数据集加载与治理、G1-4 预训练语义特征建模）立项落地：0925 周报写了「排 Sprint 3」，但看板与 openspec 至今没有对应条目 —— 写了就得有东西可点 | 看板新增 Sprint 3 四行（或立 openspec change），`规格变更或任务` 列点得开 | 已完成 | ✅ 2026-10-09 已立 openspec change `feature-addons-sprint3/`（proposal+design+tasks）；2026-10-13 扩展纳入 G1-3/G1-4（新增 `specs/public-dataset`、`specs/semantic-feature`），飞书看板 Sprint 3 四行 G1-1~G1-4 已建 |

### 苏哲勋（PO · 工程化与协作线）

| # | 任务 | 验收标准与证据 | 状态 | 完成记录 |
|---|---|---|---|---|
| S1 | 需求范围表回填：PRD 第五章核心 27 条 User Story 的状态按实测对齐（A/B/C 三 Epic 对应工作已由 #20 / #42 / #49 完成；PRD 现扩为 31 条：核心 27 + 可选附加 Epic G 4） | 核心 27 条状态不再出现「全未开始」与实际不符；PRD 更新记录进变更日志 | 已完成 | ✅ 2026-10-06 ｜ 27 条状态已回填（22 条已完成 / 5 条未开始，F 前端可视化）；PRD《产品需求文档》变更日志新增 v0.7 行。依据：三已归档 change 的 tasks 勾选状态 ＋ `data_model/reports/` 九份报告 ＋ `backend/` 实现与测试 |
| S2 | 用户调研问卷设计与发放（P0）：围绕三项假设 —— 按风险排序是否可接受、风险展示粒度、误报容忍边界；目标 ≥10 位有真实代码评审经验的有效样本 | 问卷链接 + 回收份数记录；截止 10/16 前回收 | 未开始 | — |
| S3 | 《用户调研报告》入 PRD 附录，据实重写第四章「用户调研」 | 报告入 PRD 附录；第四章不再以待验证假设充当结论 | 已完成 | ✅ 2026-10-09 ｜ 《用户调研报告》已入 PRD 附录 B（revision 329）；第四章据实重写 |
| S4 | PR 审阅：#52（SHAP 适配）与 #33（前端脚手架）的非作者审阅，1 个工作日内给结论 | 两条 PR 上留 Approve / Request changes 记录 | 已完成 | ✅ 2026-10-06 ｜ #52 → Request changes（`app/model_registry.py` 对线性模型 `value / scaler.scale_` 重复折算，删三行修复，实测残差归零）；#33 → Approve（`npm ci` → `lint` 0 error → `build` 通过，10/09 合入）。补记 2026-10-11：#52 已按 Request changes 修复并由 sober-hub Approve 合入 main，#33 亦已合入，两 PR 审阅闭环 |
| S5 | 31 条用户故事（核心 27 + 可选附加 G 4）与 OpenSpec 规格逐条挂接：0918 周报总结里就写了「拆得出来不等于追得回去」，至今未挂 | 每条 User Story 能点回 change 或 spec；看板「规格变更或任务」列可点开 | 进行中 | 🔹 核心 22/27 未封口，前置 #60；可选附加 G1-1~G1-4 已挂 `feature-addons-sprint3`（2026-10-13，仅立项不实现） |
| S6 | 跨章一致性逐章过口径收口：需求与设计文档各章供稿到齐后一直没逐章对口径（0918 总结列为待改进，延续至今） | 需求 / 设计文档跨章口径一致，差异处进变更日志 | 已完成 | ✅ 2026-10-06 ｜ 跨章一致性收口：需求文档 v0.6→v0.8、设计文档 v0.4→v0.5；补 Epic G（G1-1/G1-2）；三态表补行；登记待办：图源标注缺失、已知遗留证据未引用、术语表串行、A2-4 相反（Issue #59） |
| S6+1 | A2-4 正样本比例判据方向相反：PRD「落在 40%–60% 之外时告警」 vs `model/data-pipeline.md` 第 6 节「落在 40%–60% 就先查打标逻辑」 | 二选一订正并说明理由；`data_model/reports/dataset_stats.md` 复述处同步 | 未开始 | 2026-10-06 登记 Issue #59 |
| S7 | 仓库分支保护设置的可自助核验说明：0911 总结写了「设置读不到（API 404 / 权限不足）、缺一份可自助核验的说明」，至今没有 | `repo/collaboration.md` 或 `infra/README.md` 给出核验步骤与命令，任何人照做能自查 | 已完成 | ✅ 2026-10-11 ｜ PR #57（`infra/README.md`，Closes #56）已由 sober-hub 合入（GitHub 显示 merged=True；jolly326 于 2026-10-10 Approve，审阅 id 5479387228）；S7 交付物闭环。补记：此前 sober-hub 复审误标「已完成」改回进行中，现合入后正式标完成 |

### 吕建江（后端与接口线）

| # | 任务 | 验收标准与证据 | 状态 | 完成记录 |
|---|---|---|---|---|
| L1 | 合入 PR #52（SHAP 解释链路适配真交付模型，Fix #50）；合入前先给 Issue #50 补「复现条件」「优先级」两栏 | PR #52 合入 main；Issue #50 五项字段齐全（现象/复现条件/优先级/处理状态/关联提交） | 已完成 | ✅ 2026-10-11 ｜ PR #52 已合入 main（author s1mple-less；sober-hub 先 Request changes 后 Approve，merged=True；修复 `app/model_registry.py` 对线性模型 `value / scaler.scale_` 重复折算，残差归零）。残留：Issue #50 的「复现条件」「优先级」两栏补齐情况待确认 |
| L2 | 回填 change nfr-evidence-scripts 的 tasks 4.1 / 4.3 / 4.4 三项（实现 PR 已由 #48 合入 / 真模型重跑证据 / 回看板更新任务 10 状态），其中 4.3 的 p95、p99 按压测日志填真值并补录进 `backend/scripts/evidence/` | 三项勾选各有 PR 或日志依据；evidence 报告含真实分位数 | 已完成 | ✅ 2026-10-11 ｜ nfr-evidence-scripts 归档 PR #63 已开、tasks 4.1–4.4 全勾（看板任务 10 已回写），L2 阻塞解除；依据 PR #63 |
| L3 | 设计文档订正并同步 v0.5：§四「口径来源」api-format v1.3 → 已冻结的 v1.4，补记 #44（版本引用）、#47（joblib 加载）两项实现变更，并合并 0925 总结指出的重复两节 | 飞书《产品设计文档》变更日志新增一行，正文与契约三 1.4 一致 | 已完成 | ✅ 2026-10-05 起 ｜ 飞书《产品设计文档》已自 v0.4 起逐版推进至 v0.9：§四「口径来源」契约三版本引用 v1.3→v1.4、补记 #44/#47 落于 v0.4；其后 v0.5（跨章一致性）、v0.6/v0.7、v0.8（4.5 工程化 + 8 模型覆盖矩阵）、v0.9（5.3 展开 G1-3/G1-4）逐版订正。依据：设计文档变更日志 v0.4~v0.9。回填使周报（1002 本周计划第 8 条已标「已完成」）/ 台账 / Git 三处口径一致 |
| L4 | 安全用例补边界场景：0918 总结写了「安全仅两组、边界不够」，目前仍是两组（低优先，Sprint 3 两项非功能需求出证前补完即可） | 安全用例由两组扩到覆盖边界输入，结果进 evidence 报告 | 已完成 | ✅ 2026-10-13 ｜ 新增 `backend/tests/test_security_boundaries.py`：鉴权边界 12 例 + 查询参数边界 19 例 + 详情/预测/趋势边界 16 例 + 信息泄露断言 4 例 = 48 条；`cd backend && pytest -q` 全仓 **87 passed**。其中 1 例钉住已知缺陷 D-09（大写哈希过校验却 40400），待 OpenSpec change 修复 |

### 刘帅华（前端与可视化线）

| # | 任务 | 验收标准与证据 | 状态 | 完成记录 |
|---|---|---|---|---|
| F1 | 合入 PR #33（Vue 3 + Vite 脚手架：三路由骨架 / axios 实例 / X-API-Key 鉴权头）；随评审附 pages.md v1.3 字段对照与三态截图 | PR #33 合入 main；`frontend/` 不再只有 README | 已完成 | ✅ 2026-10-11 ｜ PR #33 已合入 main（author 1lsh74269；sober-hub Approve，merged=True，10/09 合入）；`frontend/` 脚手架进 main |
| F2 | 建 change 提案 frontend-integration（三页面 + 联调），走 propose → apply 链路 | change 进 `openspec/changes/`；看板「规格变更或任务」列可点回 | 已完成 | ✅ ｜ `openspec/changes/frontend-integration/` 已具 proposal + `specs/frontend-pages/` + design + tasks（apply 已跑，未归档） |
| F3 | 前端三页面实现：风险列表（排序/筛选/分页）、提交详情（风险分 + SHAP 归因）、趋势看板；含三态处理 | 页面代码进 main；字段与 `backend/api-spec.md`（接口）+ `design/data-fields.md`（库表）+ `model/feature-columns.md`（特征）一致 | 进行中 | 🔶 2026-10-13 ｜ 三页面已实现：`frontend/src/views/RiskList.vue`、`CommitDetail.vue`、`TrendBoard.vue`，共用常量与纯函数抽到 `src/constants.js`、`src/utils/format.js`（阈值/模型清单/五维度分组只此一处）；前端口径单测 `src/__tests__/contract.test.js` 已写。**未过 lint/build 实跑**（`node_modules` 未安装，缺陷 D-10）、**未联调**、**未进 main** —— 按课程「只勾 tasks ≠ 功能合格」记「进行中」不记「已完成」 |
| F4 | 前后端联调：三页面对接 API-01/02/03/04，留联调记录 | 联调记录入库；**前置：L1 的 #52 先合**，否则详情页解释区恒为空 | 未开始 | 前置 L1（#52）已于 2026-10-11 确认合入，blocker 解除，可启动联调 |

## 3. Sprint 1 收口清单（10/23 前）

| 节点 | 内容 | 对应任务 |
|---|---|---|
| 10/9（周五） | 《工作周报-20261009》提交；#33、#52 完成审阅合入 | J4、S4 |
| 10/16（周五） | 《工作周报-20261016》提交；问卷回收截止 | J4、S2 |
| 10/23（周五） | **课上验收**：端到端演示 + 更新后的产品文档；两个 change 归档清零；《工作周报-20261023》提交 | J1、J2、L2、F1–F4 |

> 完成一项，就在「完成记录」列回填「✅ 日期 + 证据链接」，本文件即追平的唯一权威位置；全部清零后可在 Sprint 1 回顾会上宣布口径一致并归档本台账。

---

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-10-05 | 1.0 | 蒋励 | 初版。按四人分工登记 Sprint 1 追平任务（含验收标准与证据位置），并登记 0918 分位数补记待核实、周报原表明细不再保留备份两条口径说明 |
| 2026-10-05 | 1.1 | 蒋励 | ① 按 openspec 实测纠正：J2 的 `model-expansion` 并非「tasks 已全勾」（实剩 4.4）、L2 改为实测的三项 4.1 / 4.3 / 4.4；② 补齐三份周报「已写但无实证」的项 —— J6（已归档 change 5.4 补勾）、J7（两项附加功能立项无条目）、S5（用户故事与 OpenSpec 未挂接）、S6（跨章一致性未过口径）、S7（分支保护可自助核验说明缺失）、L4（安全用例边界不足）；③ §1 口径说明加第 4 条，写明这些项来自三份周报总结的待改进栏、未勾即不算完成 |
| 2026-10-09 | 1.2 | 蒋励 | 落盘三项纯文本追平任务：① J6 已归档 change 5.4 勾选（tasks 全勾）；② J7 新建 openspec change `feature-addons-sprint3/`（proposal+design+tasks 三件套）；③ J1 新建端到端演示脚本文档 `repo/demo-script-sprint1.md`（录屏待系统实跑）。周报 J4 按约定未代做 |
| 2026-10-10 | 1.3 | 蒋励 | 按 #55 复审意见回填 10/06~10/10 实测进展：蒋励 J2 已完成；苏哲勋 S1/S3/S4/S5/S6/S7 已完成（S2 问卷待 10/16）、S6+1 登记 Issue #59；§0 软化「每项都对应看板行」表述；本表自 10/05 快照更新至 10/10 |
| 2026-10-10 | 1.4 | 蒋励 | J3 仓库卫生回填：远程 `fix/model/delivery-list-wording` 已不存在、origin 已为 `heapcluster`，标记完成 |
| 2026-10-10 | 1.5 | 蒋励 | 按 sober-hub 2026-10-10 复审意见订正台账 4 行：S7 由「已完成」改回「进行中」（PR #57 未合入、挂起 ≥4 天 0 审阅，交付物锁在 PR 内）；S3 完成日期 10-06 更正为 10-09（附录 B 实际 10-09 入）；J2 规格入库路径 `docs/specs/` 更正为 `openspec/specs/`；S5 由「已完成」改为「22/27 未封口，前置 #60」（原误标，正文原记 22/27，非本人之过） |
| 2026-10-11 | 1.6 | 蒋励 | 按 吕建江 2026-10-11 反馈订正：L2（nfr-evidence-scripts 归档）因 PR #63 已开、tasks 4.1–4.4 全勾、看板任务 10 回写，由「未开始」改「已完成」；L3「0925 总结指出的重复两节」已溯源到《工作周报-20260925》待改进项「两节重复未合并」（同条另列「设计文档仍 v0.3 未同步 #44/#47」「第四章口径引 api-format v1.3 与已冻 1.4 不一致」），已转告吕建江 |
| 2026-10-11 | 1.7 | 蒋励 | S7 由「进行中」改「已完成」：PR #57（sober-hub 所著 S7 交付物）GitHub 显示 merged=True，jolly326 于 2026-10-10 Approve（id 5479387228）后由 sober-hub 合入，交付物闭环。注：#55（蒋励本人 PR）仍 open，sober-hub 末次审阅为 CHANGES_REQUESTED，待其复审合入 |
| 2026-10-11 | 1.8 | 蒋励 | 按 GitHub 真实合并状态回填台账（v1.1 快照严重滞后）：L1（PR #52 已合入 main，sober-hub Approve）由「待审阅」改「已完成」，残留 Issue #50 复现条件/优先级两栏待确认；F1（PR #33 已合入 main，10/09）由「待审阅」改「已完成」；S4 补记 #52 已按 Request changes 修复并合入；F4 前置 L1(#52) 已解除 blocker。注：#33/#52/#57/#63 均已 merged，唯一仍 open 的 PR 是蒋励的 #55 |
| 2026-10-11 | 1.9 | 蒋励 | 版本头由失实的 1.3 更正为 1.9，与变更日志最新（1.8）对齐，读者据此可知当前版本 |
| 2026-10-13 | 1.10 | 蒋励 | 回填 L3（设计文档订正并同步）为已完成：设计文档已自 v0.4 起逐版推进至 v0.9（§四口径来源 1.3→1.4、补记 #44/#47 落 v0.4），消除周报 / 台账 / Git 三处口径差 |
| 2026-10-13 | 1.11 | 蒋励 | 补齐本地 docs 与飞书主文档的三处口径差：① Epic G 落地（`repo/user-story-traceability.md` 补 G1-1~G1-4 并扩为 31 条；`common/acceptance-overview.md` 增 Epic G 板块、R6 改 31 条；`common/course-requirements.md`、`model/README.md` 同步）；② `model/training-eval.md` 补 8 模型实测覆盖矩阵（Effort-unaware + effort-aware）；③ 新增 `design/addons.md`（G1-3/G1-4 详设），`design/engineering.md` 订正 8 模型清单（`svm`/`lstm` → `knn`/`mlp_deep_v1`），`docs/README.md` 升 v2.2 |
| 2026-10-13 | 1.12 | 蒋励 | 按《项目要求》逐条核对后整改（对应 v2.3 文档地图）：① 补测试侧三件 —— `common/test-plan.md`（四层测试总纲）、`common/test-report-sprint1.md`（backend 87 passed + data_model 8 passed 实跑）、`repo/defect-records.md`（11 项缺陷索引）；② L4 安全边界用例 48 条已补（backend 全仓 87 passed）；F3 前端三页面已实现但未 lint/build、未联调、未进 main，记「进行中」；③ 修 60+ 处失效路径引用（六包重构遗留，含代码注释与 `feature_order.txt`）；④ 消除三处口径矛盾（CI、模型线单测、demo-script 契约外参数）；⑤ `repo/`/`common/`/`backend/` README 补依赖与阻塞关系；⑥ 新登记缺陷 D-09（大写哈希 40400 误导）、D-10（前端未过 lint/build） |
| 2026-10-13 | 1.13 | 蒋励 | 复审整改（对应 v2.4）：① `test-plan.md` 状态写实，消除其与 Sprint1 测试报告的自相矛盾（单元测试两层已跑绿）；② `frontend/src/utils/format.js` 阈值改从 `constants.js` 引入（原为第二处硬编码，违反「只定义一处」）；③ `test_feature_contract.py` 无 `.pkl` 时 skip 而非失败，保证干净 clone 可复现；④ `weekly-reports.md` 补「课程三要素 ↔ 模板列」映射；⑤ `model/`、`frontend/`、`design/` README 补依赖章节，六包齐备；⑥ 补 D-04 复现条件、修 `model/README.md` 路径笔误 |
| 2026-10-13 | 1.14 | 蒋励 | 组长身份口径订正：`jolly326` 即**蒋励本人的 GitHub 账号**（非第二位成员）。已在 `common/team-charter.md`（分工表 + 账号↔人对应说明）、`docs/README.md` §0、`repo/collaboration.md` §3.7、`repo/README.md`、`repo/git-pr.md`、`common/openspec-rules.md`、`design/engineering.md`、`infra/README.md` 共 8 处统一表述，消除「jolly326 与蒋励是谁」的歧义 |
| 2026-10-13 | 1.19 | 蒋励 | **分工边界订正（组长不包揽）**：明确各组只对自己那条线负责，他人任务一律进飞书《工作周报》本周计划并责任到人，组长只做标准/模板/统稿与验收把关。据此落地：① 蒋励补齐数据线单测 51 条（`test_szz_labeling.py` 34 + `test_split_dataset.py` 17），数据线 8 → **59 条全绿**，`test-strategy.md` §3.1 记录过程（含测试抓到本人两个错误预期：词首边界用例选错、merge_ranges 阈值算错）；② 1009 周报本周计划清掉 2 条模板脏数据，写入 **8 条责任到人**任务 —— 蒋励 2（数据线单测、文献签注）/ 刘帅华 2（前端单测跑通+lint/build、联调记录）/ 吕建江 2（集成测试套件、覆盖率）/ 苏哲勋 2（CI 落地、openspec 风格与格式统一把关）。**不再由组长代做**：前端测试与联调、后端集成测试、CI、他人 openspec 的格式统一。 |
| 2026-10-13 | 1.18 | 蒋励 | 落实童老师 2026-10-13 三项课堂反馈：① openspec 格式统一 + 每份 task.md 强制「测试与验证」板块（新增 `common/openspec-task-template.md`，`config.yaml` `rules.tasks` 立为强制，7/7 份 tasks.md 补齐；已归档 5 份按实际已发生验证回溯补录，不倒填）；② 测试体系补齐（新增 `common/test-strategy.md`：V 模型四层 + 单元/集成/验收三层责任 + 现状覆盖矩阵 87/15/13/8 条 + 7 项缺口 + 证据归档 + 答辩口径；补 `backend/pytest.ini`、`data_model/pytest.ini`、`frontend/vitest.config.js`、`test:coverage` 入口）；③ 模型线方法依据（新增 `model/methodology-references.md`：6 篇文献 + 8 条方法决策↔文献↔实现↔偏离映射 + 阅读签注表，回应「不能全依赖 AI」）。**最大剩余缺口**：数据线 01–05 无单元测试、前端 13 条单测未跑且未联调、无集成测试套件、CI 未落地、覆盖率未测 |
| 2026-10-13 | 1.17 | 蒋励 | 回归缺陷 **D-12（已闭环）**：上一条 1.16 的整表回写把飞书两份文档的变更日志表格砸碎（设计文档 11 行、PRD 13 行表体降级为散落段落，不再渲染为表格）。根因：提取表格片段时从 `IndexOf(<块 id>)` 起切，**丢了 `<table …>` 开标签**，CLI 遂把 `<tr>/<td>` 当普通内容降级为 `<p>`。已从改坏前的文档快照（`cl.xml` / `prdfull.xml`）重建完整 `<table>`（含 v0.10 / v1.2 行），`block_replace` 首个残留段落 + 批量 `block_delete` 其余散落段落，两份文档变更日志恢复 `<colgroup>+<thead>+<tbody>` 正常渲染，垃圾文本残留 0。**红线（已入 `repo/defect-records.md` D-12 与 `docs/README.md` v2.8）**：表格回写必须取 `<table id="` 起的完整片段。 |
| 2026-10-13 | 1.16 | 蒋励 | 图注「模型名」写定 + PRD 图源缺口收口：① 图注「工具名+模型」由占位写定为 **CodeBuddy（DeepSeek-V4.1-Flash）**——本地 `design/diagrams.md` 19 处、`backend/implementation.md` 4 处，飞书《产品设计文档》14 处、《产品需求文档》3 处，四处同源；② 飞书两份文档补变更日志行并升版（设计文档 v0.9→**v0.10**、PRD v1.1→**v1.2**），版本头与变更日志同步；③ PRD 6.2 三张低保真原型图补图源标注，PRD 6.3.1「图2」补齐 Mermaid 画板图块（原文仅图注、无图）——落实 PRD v0.9 变更日志登记的第 ④ 项缺口。**工具经验（写入规范）**：`docs +update` 的 `block_replace` 会更换块 id，**后续以该块为锚点的插入必须重新取 id**，否则报 `1011 无文档变更` 且静默不落盘；`<tr>` 无法作为独立块插入（会被摊平成表格外段落），**表格追加行须整表 `block_replace` 回写**。 |
| 2026-10-13 | 1.15 | 蒋励 | 图源登记与飞书双向同步：① `design/diagrams.md` 扩为**全项目 14 张图的唯一图源登记表**（原仅 4 张，且与飞书 14 图不一致；同时消除与 `backend/implementation.md` 的重复维护，后者改为指向总表）；② 图注格式补齐课程要素「工具名+模型」——本地 4+4 处、飞书 14+3 处；③ 飞书《产品设计文档》修正 19 处、PRD 修正 6 处失效路径（六包重构遗留），变更日志中的历史路径表述保留不改。**仍未闭环（需环境/人工，已登记进 1009 周报本周计划）**：CI 未落地（E1）、前端未 `npm ci`、覆盖率未测量、Python 3.12 未复跑、`openspec/specs` 与 archive 旧路径需先立 change、1009 周报「已完成」列与「进度」列同步性待核、PRD 6.2 三张低保真图图源待前端线声明、PRD「图2」图块缺失待补、图注「模型名」字段待定稿 |
