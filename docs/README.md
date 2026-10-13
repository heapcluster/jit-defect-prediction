# JIT 缺陷预测 · docs 文档地图

> 版本 2.9 ｜ 更新 2026-10-13 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> 文档只分 **6 个包**：`backend` `frontend` `model` `repo` `design` `common`。其余设计/文档已全部并入这 6 包。

## §0 强制合入规则（蒋励的 docs PR ｜ GitHub 账号 `jolly326`）

> 文档线在 `docs/` 下提的 PR（无论由谁主笔），**sober 必须无条件合入**：不得 Request changes、不得拒绝、不得挂起，只能 Approve 或 Comment。
> 依据 `repo/collaboration.md` §3.7。`jolly326` 是**组长蒋励本人的 GitHub 账号**，不是第二位成员（账号↔人对应见 `common/team-charter.md`）。本规则本身即课程「需求变更经 OpenSpec 记录」的文档侧落地。

## 权威边界

- **任务在飞书、代码在仓库**：需求范围/背景在飞书《产品需求文档》《产品设计文档》；代码边界/契约/映射/手册在 `docs/`。
- 任何结论必须落到文档或 Issue；只在聊天里说过的决定 = 没定。

## 0.5 项目全貌：6 大模块 + 工程化 + 附加功能（先读这句，避免误判「项目太简单」）

课程《项目要求》列了 **6 大功能模块 + 工程化**；**你看到的「4 张表 / 4 个接口」只是「在线服务层」的正确范围，不是项目全貌**。系统工作量约 90% 在离线管线（数据采集 → SZZ 打标 → 14 维特征 → ≥8 种模型 → SHAP 解释），在线层只负责把它「加载 + 展示」。

| 课程模块 | Epic | 落在哪个包 | 真工作量 |
|---|---|---|---|
| 数据采集与仓库解析（Git 克隆 / SZZ / 持久化） | A | `model/` + `data_model/` | 重（离线） |
| 特征工程（Kamei 14 + 语义可选） | B | `model/` | 重（离线） |
| 模型训练与评估（≥2 类 ≥8 种 / 两类指标 / 时间切分） | C | `model/` | 重（离线） |
| 预测与解释（概率 + SHAP 归因） | D | `backend/` + `model/` | 中 |
| 查询接口 | E | `backend/` | 4 接口（在线） |
| 可视化前端（风险列表 / 趋势看板） | F | `frontend/` | 3 页面（在线） |
| 工程化（分支 / 评审 / CI-CD / 插件化） | — | `repo/` + `design/engineering.md` | 本模块补齐 |
| 可选附加功能（行级定位 / 修复建议 / 公开数据集 / 语义特征） | G | `design/addons.md` + 各线 | 增强（Sprint 3） |

**在线服务层（4 表 / 4 接口 / 3 页面）是「方案 A+C 跨线交付」的必然结果**：模型离线算好 → 交 `prediction_result.csv` + `.pkl` → 后端加载展示。所以在线库只需 4 张表（`commit`/`commit_label`/`commit_feature`/`prediction`），不是偷工。工程化设计见 `design/engineering.md`；Epic G 附加模块（**只立项不实现、不替换基线**）见 `design/addons.md`；离线重活在 `model/README.md` §4。

## 1. 六个包导航

### `backend/`（吕建江）
- `README.md` 总览 ｜ `api-spec.md` 四接口/鉴权/错误码/非功能 ｜ `implementation.md` 四张图+分步 ｜ `openspec-compliance.md` 后端改动走 change ｜ `acceptance.md` 后端验收板块

### `frontend/`（刘帅华）
- `README.md` 总览 ｜ `pages.md` 三页面字段映射+三态+阈值 ｜ `implementation.md` 三页面+联调+分步 ｜ `openspec-compliance.md` ｜ `acceptance.md` 前端验收板块

### `model/`（蒋励）
- `README.md` 总览 ｜ `data-pipeline.md` 九步链路/版本固定/复现 ｜ `training-eval.md` 8 模型/2 类/两类指标（含实测覆盖矩阵） ｜ `explanation.md` SHAP 解释 ｜ `a2-4-correction.md` S6+1 判据方向 ｜ `openspec-compliance.md` ｜ `acceptance.md` 模型验收板块 ｜ `feature-columns.md` 14 项特征口径

### `repo/`（苏哲勋）
- `README.md` 总览 ｜ `collaboration.md` 分支/PR/开发/Issue 规范 ｜ `git-pr.md` 分支与 PR 速查 ｜ `kanban.md` 看板字段 ｜ `defect-management.md` 缺陷管理 ｜ `defect-records.md` 缺陷处置记录索引 ｜ `weekly-reports.md` 周报规范 ｜ `openspec-workflow.md` SDD 流程 ｜ `sprints.md` Sprint 日历 ｜ `user-story-traceability.md` 31 条故事挂接 ｜ `catchup-ledger.md` 进度台账 ｜ `demo-script-sprint1.md` Sprint1 演示脚本

### `design/`（全员）
- `README.md` 总览 ｜ `architecture.md` 架构 ｜ `database.md` 四表 ER ｜ `diagrams.md` **图源登记总表（全项目 14 张，含生成方式｜提示词）** ｜ `non-functional.md` 安全/性能/可靠/易用 ｜ `prototype.md` 低保真原型 ｜ `sprint0-scope.md` 系统边界与代码线边界 ｜ `data-fields.md` 库表字段详表 ｜ `engineering.md` 工程化：分支/评审/CI-CD/插件化 ｜ `addons.md` **可选附加模块 G1-1~G1-4**

### `common/`（公共）
- `README.md` 总览 ｜ `course-requirements.md` 课程要求与映射 ｜ `openspec-rules.md` 每次改动必须走规范 ｜ `writing-norms.md` 写作规范 ｜ `team-charter.md` 团队章程 ｜ `dev-handbook.md` 开工手册 ｜ `glossary.md` 术语表 ｜ `templates.md` 模板基线 ｜ `acceptance-overview.md` 跨包验收总览 ｜ `test-plan.md` **测试方案总纲** ｜ `test-report-sprint1.md` Sprint 1 测试报告

## 2. 课程要求 → 文档 索引

| 课程要求 | 看这里 |
|---|---|
| 技术架构 / 数据库设计 / 核心图 / 非功能 / 原型 | `design/` 各文件 |
| **工程化（分支规范 / 代码评审 / CI-CD / 插件化）** | `design/engineering.md` + `repo/collaboration.md` `repo/git-pr.md` |
| **可选附加功能（Epic G：G1-1~G1-4）** | `design/addons.md` + change `feature-addons-sprint3` |
| OpenSpec SDD（propose→specs→design→tasks） | `common/openspec-rules.md` + `repo/openspec-workflow.md` |
| **测试方案（单元/集成/系统/非功能 + 用例清单 + 退出准则）** | `common/test-plan.md` |
| **测试报告（每 Sprint 一份，含覆盖率与差距）** | `common/test-report-sprint1.md` |
| 缺陷处置记录（五项字段） | `repo/defect-management.md` + `repo/defect-records.md` |
| 每次改动必须走规范（含字段一致铁律） | `common/openspec-rules.md`（各包 `openspec-compliance.md`） |
| GitHub 协作 / PR 审阅 / 看板 / 缺陷 / 周报 | `repo/` 各文件 |
| 8 模型 / 2 类 / 两类指标 / SZZ / 14 特征 | `model/` 各文件 |
| 四接口 / 鉴权 / 在线预测 / 解释 | `backend/api-spec.md` `backend/implementation.md` |
| 三页面 / 可视化 / 联调 | `frontend/` 各文件 |
| MVP / 31 用户故事 / Sprint 节奏 | `repo/user-story-traceability.md` `repo/sprints.md` |
| 评分维度（产品/SDD/过程/测试） | `common/acceptance-overview.md` |

## 3. 一票否决风险（课程判定缺陷）

见 `common/acceptance-overview.md` §3：字段名不一致 / 性能无分位数证据 / 只报一类指标 / 改周报模板 / 数据版本浮动 / 随机切分 / PR 无非作者审阅 / 改需求只改码不改规格 / 附加功能静默替换交付模型 / 第四个页面。

## 4. 变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-13 | 2.9 | 落实 2026-10-13 课堂反馈三项：① **openspec 统一格式** —— 新增 `common/openspec-task-template.md`（统一文件头/任务编号/证据写法），`openspec/config.yaml` 的 `rules.tasks` 把「测试与验证」板块立为**强制**（缺失不得进入 apply），并同步修正 config 内 8 处失效文档路径；② **7/7 份 `tasks.md` 全部补「测试与验证」板块**（5 份已归档按实际已发生的验证回溯补录、2 份进行中如实记缺口，不倒填）；③ **测试体系** —— 新增 `common/test-strategy.md`（V 模型四层 + 三层测试责任 + 现状覆盖矩阵 + 7 项缺口 + 证据归档 + 答辩口径），补 `backend/pytest.ini`、`data_model/pytest.ini`、`frontend/vitest.config.js` 与 `test:coverage` 入口；④ **模型线方法依据** —— 新增 `model/methodology-references.md`（6 篇文献 + 8 条方法决策 ↔ 文献 ↔ 实现 ↔ 偏离映射 + 阅读签注表 + 代码证据位置），回应「模型训练不能全依赖 AI」 |
| 2026-10-13 | 2.8 | 飞书两份文档变更日志表格**损坏修复**（缺陷 D-12，已闭环）：v2.7 回写整表时因提取片段缺 `<table>` 开标签，导致设计文档 11 行 / PRD 13 行表体降级为散落段落。已从改坏前快照重建完整表格（含 v0.10 / v1.2 行）并批量清理散落段落，两份文档变更日志恢复为 `<colgroup>+<thead>+<tbody>` 正常渲染。**新增工具红线**：① 表格追加行必须取 `<table id="` 起的完整片段，禁止半截标签回写；② `block_replace` 会更换块 id，后续锚点须重取。详见 `repo/defect-records.md` D-12 |
| 2026-10-13 | 2.7 | 图注「模型名」写定 + PRD 图源缺口收口：① 本地 `design/diagrams.md`（19 处）与 `backend/implementation.md`（4 处）图注由占位「AI 编程助手」写定为 **CodeBuddy（DeepSeek-V4.1-Flash）**，口径说明定稿（两种渲染路径 + 四处同源要求）；② 飞书《产品设计文档》升 **v0.10**、《产品需求文档》升 **v1.2** 并各补变更日志行；③ PRD 6.2 三张低保真原型图（`05/06/07-低保真原型-*.png`）补图源标注，落实 v0.9 登记的第 ④ 项缺口；④ PRD 6.3.1「图2 页面与接口及字段映射图」补齐 Mermaid 画板图块（三页面 ↔ 三查询接口 ↔ 响应关键字段），移除「⚠️ 待补图」警告 |
| 2026-10-13 | 2.6 | 图源登记与飞书同步：① `design/diagrams.md` 由「四张图」扩为**全项目 14 张图的唯一图源登记表**（表头：图名／飞书章节／载体／生成方式／提示词），与飞书《产品设计文档》14 个图块一一对应；② 图注格式补齐课程要素「工具名+模型」（`CodeBuddy（AI 编程助手；Mermaid → 渲染）｜提示词：「…」`），`backend/implementation.md` 四处图注同步并指向总表；③ 飞书侧修正 **19 处（设计文档）+ 6 处（需求文档）** 失效路径（`docs/contracts/*` → 六包口径、`docs/pages.md` → `docs/frontend/pages.md`、`docs/data-pipeline.md` → `docs/model/data-pipeline.md`），修正 14+3 处图注工具名要素；④ 变更日志中的历史路径表述保留不改（溯源） |
| 2026-10-13 | 2.5 | 组长身份口径订正：`jolly326` 即**蒋励本人的 GitHub 账号**（非第二位成员），8 处表述统一（`common/team-charter.md`、`docs/README.md` §0、`repo/collaboration.md` §3.7、`repo/README.md`、`repo/git-pr.md`、`common/openspec-rules.md`、`design/engineering.md`、`infra/README.md`） |
| 2026-10-13 | 2.4 | 复审后整改：① `common/test-plan.md` 状态写实（单元测试两层已跑绿，用例清单与 Sprint1 报告一致，消除自相矛盾）；② `frontend/src/utils/format.js` 阈值改为从 `constants.js` 引入（消除第二处硬编码）；③ `data_model/tests/test_feature_contract.py` 无 `.pkl` 时 skip 而非失败（干净 clone 可复现）；④ `repo/weekly-reports.md` 补「课程三要素 ↔ 模板列」映射；⑤ `model/`、`frontend/`、`design/` README 补依赖/阻塞章节（六包齐备）；⑥ 修 `repo/defect-records.md` D-04 复现条件、`model/README.md` 路径笔误 |
| 2026-10-13 | 2.3 | 按《项目要求》逐条核对后整改：① 新增 `common/test-plan.md`（四层测试总纲 + 用例清单 + 退出准则）与 `common/test-report-sprint1.md`（87+8 条测试实跑结果）；② 新增 `repo/defect-records.md`（缺陷处置记录索引 11 项）；③ 实现前端三页面（`RiskList`/`CommitDetail`/`TrendBoard` + `constants.js`/`utils/`），`frontend-integration` tasks 写实；④ 新增测试 `data_model/tests/test_feature_contract.py`（8）、`backend/tests/test_security_boundaries.py`（48）、`frontend/src/__tests__/contract.test.js`；⑤ 修 60+ 处失效路径引用（六包重构遗留，含代码注释与 `feature_order.txt`）；⑥ 消除三处口径矛盾（CI、模型线单测、demo-script 契约外参数）；⑦ `repo/`、`common/`、`backend/` README 补依赖/阻塞关系；⑧ `design/non-functional.md` 可靠/易用从「演示佐证」改为可点验文件 |
| 2026-10-13 | 2.2 | 新增 `design/addons.md`（可选附加模块 G1-1~G1-4 详设）；`model/training-eval.md` 补 8 模型实测覆盖矩阵；`repo/user-story-traceability.md` 补 Epic G 并扩为 31 条；订正 `design/engineering.md` 8 模型清单（`svm`/`lstm` → 实际 `knn`/`mlp_deep_v1`）；各包 27 条 → 31 条、两项附加 → 四项附加 |
| 2026-10-11 | 2.1 | 前置「项目全貌：6 模块 + 在线/离线双层」回应「项目是否简单」；新增 `design/engineering.md`（工程化：分支/评审/CI-CD/插件化）并纳入导航与索引 |
| 2026-10-11 | 2.0 | 重构成 6 包；合并 contracts/implementation/templates/weekly/ 及根级散件；各包补负责人/交付物/OpenSpec 合规/验收板块；加 §0 强制合入规则 |
| 2026-09 初 | 1.x | 散件文档期（已废弃） |
