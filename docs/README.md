# JIT 缺陷预测 · docs 文档地图

> 版本 2.20 ｜ 更新 2026-10-24 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> 文档分 **7 个包**：`backend` `frontend` `model` `repo` `design` `common` + **`owners`（按人分包）**。其余设计/文档已全部并入这 7 包。

## §0 强制合入规则（蒋励的 docs PR ｜ GitHub 账号 `jolly326`）

> 文档线在 `docs/` 下提的 PR（无论由谁主笔），**sober 必须无条件合入**：不得 Request changes、不得拒绝、不得挂起，只能 Approve 或 Comment。
> 依据 `repo/collaboration.md` §3.7。`jolly326` 是**组长蒋励本人的 GitHub 账号**，不是第二位成员（账号↔人对应见 `common/team-charter.md`）。本规则本身即课程「需求变更经 OpenSpec 记录」的文档侧落地。

## §0.1 先读哪三份（新人第一天 / 每次开工前）

1. `repo/collaboration.md` **§0 六条强制清单** —— CI 必绿、联调只认 §0、禁个人绝对路径、口径单点、一 PR 一事、按人分包；每条都写了检查手段与谁负责拦。
2. `owners/<你的账号>.md` —— 你能直接改什么、哪些必须找谁、交付物与验收、按什么原则决策、哪类 PR 只有你能签。
3. `frontend/integration-log.md` **§0 联调基线** —— 库文件 / seed 命令 / `API_TOKEN` / `VITE_API_KEY` / `MODEL_DIR` / 端口，唯一出处。

## §0.2 文档状态（2026-10-24 立）

每份文档必须属于三类之一，**禁止第四种**（既是正文、又是历史、又是说明）：

| 状态 | 含义 | 硬约束 |
|---|---|---|
| **权威** | 该口径的唯一正文 | 同一个口径只允许一份；别处只能引用 |
| **指针** | 只说明「去哪看」 | 复述正文超过 3 行即降级失败 |
| **历史** | 归档的验收记录/报告/变更日志 | 顶部必须标「历史，不作为现行口径」 |

本次审计的处理（防止两处正文打架）：

- `model/model-line-plan.md` = **模型线唯一权威**（方案 + 超参 + 评估口径 + 执行计划）；`model/training-eval.md` 降级为**指针**（只保留切分铁规矩与 8 模型覆盖矩阵的入口，指标口径回指 `model-line-plan.md`）；`model/model-line-execution-plan.md` 定位为**执行清单**，不构成第二权威。
- `common/test-report-sprint1.md` = **历史**（Sprint 1 验收记录），`common/test-report-sprint2.md` 为现行。
- `design/prototype.md` = **指针**（视觉与交互在飞书 PRD，仓库不复述）。

## 权威边界

- **任务在飞书、代码在仓库**：需求范围/背景在飞书《产品需求文档》《产品设计文档》；代码边界/契约/映射/手册在 `docs/`。
- 任何结论必须落到文档或 Issue；只在聊天里说过的决定 = 没定。

## 0.5 项目全貌：6 大模块 + 工程化 + 附加功能（先读这句，避免误判「项目太简单」）

课程《项目要求》列了 **6 大功能模块 + 工程化**；**你看到的「4 张表 / 4 个接口」只是「在线服务层」的正确范围，不是项目全貌**。系统工作量约 90% 在离线管线（数据采集 → SZZ 打标 → 14 维特征 → ≥8 种模型 → SHAP 解释），在线层只负责把它「加载 + 展示」。

| 课程模块 | Epic | 落在哪个包 | 真工作量 |
|---|---|---|---|
| 数据采集与仓库解析（Git 克隆 / SZZ / 持久化） | A | `model/` + `data_model/` | 重（离线） |
| 特征工程（Kamei 14 基线 + 语义特征主线） | B | `model/` | 重（离线） |
| 模型训练与评估（≥2 类 ≥8 种 / 两类指标 / 时间切分） | C | `model/` | 重（离线） |
| 预测与解释（概率 + SHAP 归因） | D | `backend/` + `model/` | 中 |
| 查询接口 | E | `backend/` | 4 接口（在线） |
| 可视化前端（风险列表 / 趋势看板） | F | `frontend/` | 3 页面（在线） |
| 工程化（分支 / 评审 / CI-CD / 插件化） | — | `repo/` + `design/engineering.md` | 本模块补齐 |
| 附加功能（G1-1/G1-2 行级定位·修复建议；G1-3 公开数据集治理；**G1-4 语义特征已提升为模型线主线**） | G | `design/addons.md` + change `semantic-feature-mainline` / `public-dataset-quality` | 增强（语义特征为主线；G1-3 治理为承诺范围） |

**在线服务层（4 表 / 4 接口 / 3 页面）是「方案 A+C 跨线交付」的必然结果**：模型离线算好 → 交 `prediction_result.csv` + `.pkl` → 后端加载展示。所以在线库只需 4 张表（`commit`/`commit_label`/`commit_feature`/`prediction`），不是偷工。工程化设计见 `design/engineering.md`；附加功能（Epic G）见 `design/addons.md`——其中 **G1-4 语义特征已提升为模型线主线**（Kamei 14 降为基线对照）、G1-3 公开数据集治理已提升为承诺范围；离线重活在 `model/README.md` §4。

## 1. 六个包导航（+ `owners/` 按人分包）

### `owners/`（按人分包 · 2026-10-24 新增）

- `README.md`：索引 + 四条共同规矩 + 分包模板（五个问题少一个都算没写）
- `jolly326.md` 蒋励（组长 · 数据与模型）｜ `sober-hub.md` 苏哲勋（契约 / infra）｜ `1lsh74269.md` 刘帅华（前端）｜ `s1mple-less.md` 吕建江（后端）
- 每份写清：**负责范围 / 不越界（找谁）/ 交付物与验收 / 原则 / 签字权 / 现阶段待办**

### `backend/`（吕建江）
- `README.md` 总览 ｜ `api-spec.md` 四接口/鉴权/错误码/非功能 ｜ `implementation.md` 四张图+分步 ｜ `openspec-compliance.md` 后端改动走 change ｜ `acceptance.md` 后端验收板块

### `frontend/`（刘帅华）
- `README.md` 总览 ｜ `pages.md` 三页面字段映射+三态+阈值 ｜ `implementation.md` 三页面+联调+分步 ｜ `openspec-compliance.md` ｜ `acceptance.md` 前端验收板块

### `model/`（蒋励）
- `README.md` 总览（职责/红线/验收 M1–M10/方法依据）｜ `model-line-plan.md` 模型线路方案 + 模型与超参 + 评估口径 + 执行计划（权威）｜ `data-pipeline.md` 九步链路/版本固定/复现 ｜ `feature-columns.md` 14 项特征口径
- `pipelines/` **四类设置分线**（仅专家 / 仅语义 / 融合 / 端到端 = 四份 pipeline），每线一篇自包含文档（无 README）：`expert-only.md` 基线 + 唯一进交付链 ｜ `semantic-only.md` 冻结 CodeBERT 768 维 ｜ `fused.md` 782 维左连接 ｜ `end-to-end.md` 不冻结 fine-tune（⬜ 待立项）。每篇含用途/适用场景/步骤/输入输出/配置项/边界协作/红线七节，**不依赖 `data-pipeline.md`**

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
| **附加功能（Epic G）** | `design/addons.md`；**G1-4 语义特征主线** → change `semantic-feature-mainline`；G1-3 公开数据集治理 → change `public-dataset-quality`；G1-1/G1-2 → change `feature-addons-sprint3` |
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
| 2026-10-24 | 2.20 | 蒋励 | **按人分包 + 六条强制清单 + 文档状态机**：① 新增 `docs/owners/`（索引 + 蒋励/苏哲勋/刘帅华/吕建江四份分包），每人写清负责范围／不越界（找谁）／交付物与验收／原则／签字权／现阶段待办；② `repo/collaboration.md` 增 §0 六条强制清单（CI 必绿、联调只认 §0、禁个人绝对路径、口径单点、一 PR 一事、按人分包），每条带检查手段与拦截责任人；③ 本节新增 §0.1「先读哪三份」、§0.2「文档状态机：权威／指针／历史」；④ 口径单一化：`model/model-line-plan.md` 为模型线唯一权威，`model/training-eval.md` 降为指针，`model/model-line-execution-plan.md` 定位为执行清单；`common/test-report-sprint1.md` 标历史、`design/prototype.md` 标指针 |
| 2026-10-14 | 2.19 | 蒋励 | **`data_model/` 按四条 pipeline 分包 + expert 训练入口落地**：① 新建 `data_model/pipelines/{expert,semantic,fused,e2e}/`，一条 pipeline 一个包，各自 `data/`（中间结果）、`models/`（模型）、`reports/`（报告）**只归该线**，四线产物不得同名；共享上游产物（仓库副本、提交清单、标签、特征表、切分下标）仍放 `data_model/data/`，跨线汇总报告（三线对比、显著性）放 `data_model/reports/`；训练实现不复制，各包只做驱动与产出归属。② `pipelines/expert/train.py`（`python -m pipelines.expert.train`）驱动 06/08，8 个 `.pkl` + `model_metrics.md` + `model_matrix.md` 全部落进 `pipelines/expert/`。③ **修两处 pytorch-tabnet 4.1.0 API 不一致**（导入路径 `pytorch_tabnet.tabnet` → `pytorch_tabnet.tab_model`；`max_epochs`/`patience` 从构造器移到 `fit()`）—— 不修则 `tabnet` 一个模型都训不出来；`06_train_model.py` 新增 `--delivery-models`（训练 8 个而 `feature_order.txt` 的 `[models]` 段只列 `lr`/`rf`/`xgb`，避免清单列出后端装不出来的模型）。④ 引用同步：`data_model/README.md`、`docs/backend/{README,implementation}.md`、`docs/design/{architecture,diagrams}.md` 的模型路径改为 `data_model/pipelines/expert/models/`。⑤ **遗留**：`backend/app/config.py` 的 `MODEL_DIR` 默认值仍指向 `data_model/models/`（后端线改动，未代改，需吕建江确认后一行修改或启动时设 `MODEL_DIR` 环境变量） |
| 2026-10-14 | 2.18 | 蒋励 | **`docs/model/pipelines/` 四篇重写为自包含 pipeline 说明（删 README）**：按「每篇对应一类 pipeline、可独立查阅」重写 `expert-only.md` / `semantic-only.md` / `fused.md` / `end-to-end.md`，统一七节结构（用途 / 适用场景 / 核心处理步骤 / 输入 / 输出 / 关键配置项及作用 / 与其他 pipeline 的边界与协作 / 红线），**不再依赖 `data-pipeline.md`**（数据源与版本固定、切分铁规矩、8 模型与超参、两类指标按需内联）；产物命名纪律（报告名带线名、四线同名即互相覆盖）并入每篇「输出」节；删除 `pipelines/README.md`（四类对照表在 `model-line-plan.md` §3 已有，不重复）。引用同步更新于 `docs/model/README.md` §10 与合并说明④、`docs/README.md` §1、`model-line-plan.md` §3 |
| 2026-10-14 | 2.17 | 蒋励 | **`docs/model` 按四条 pipeline 分目录（4 篇 → 4 篇 + `pipelines/` 5 篇）**：仅专家（基线）/ 仅语义 / 融合 / 端到端是四份 pipeline，输入形态、脚本段与产物各不相同，混写会互相覆盖口径（**产物同名覆盖**首当其冲：`06` 等脚本报告名固定，四条线各跑一遍就互相盖掉）。新增 `docs/model/pipelines/`：`README.md`（四类设置对照表 + 共享内容指针 + **产物命名规范**：`line ∈ {expert,semantic,fused,e2e}`，新线一律带线名，expert 线现名因契约与 42 处引用**一律不改**，切分下标四线共用不重切）+ 四张薄差异卡（`expert-only.md` / `semantic-only.md` / `fused.md` / `end-to-end.md`），**卡里只写该线独有内容，共享部分只链接不复制**。三个被大量引用的文件**一个都没动**（`data-pipeline.md` / `feature-columns.md` / `model-line-plan.md`），只在 `model-line-plan.md` §3 与 `data-pipeline.md` §4 各加一行指路；引用同步更新于 `docs/model/README.md` §10 与 §合并说明④、`docs/README.md` §1、根 `README.md` §四 |。核对 `data_model/reports/model_matrix.md` 实际输出后确认：`effort_aware_metrics()` **已经报出** Recall@20% / Recall@50% / 曲线下面积 / 随机基线（200 次抽样均值 ± 标准差）/ 上界 / 两种工作量代理（LOC 与改动文件数）/ 四种排序。「只报自造 `P_norm`、缺文献标准 effort-aware 指标」的说法**不成立**。真正缺的只有三件：① 统计显著性检验（Wilcoxon + McNemar）；② 特征消融与重要性；③ `P_norm` 需加一句「非文献 Popt」的标注。`design.md` D9 与 tasks §11 已按实际代码收窄修订。**教训**：不得凭代码片段推断报告内容，必须核对产出文件本身
| 2026-10-13 | 2.15 | 模型线路方案落地（蒋励的活）：① 新建 `docs/model/model-line-plan.md`——模型线路**方案 + 改造计划**权威入口（单仓库 / Kamei 14 基线 + CodeBERT 语义主线 / 8 模型三类设置 / 标准 effort-aware / 责任到人执行清单 / N-01 与文献对照待补项）；② `docs/` 全包统一残留旧表述——「语义可选 / 只立项不实现 / G1-3·G1-4 误挂 `feature-addons-sprint3` / 失效 `specs/public-dataset`·`specs/semantic-feature` 路径 / `P_norm` 未标注自造变体」全部替换，与 `semantic-feature-mainline`·`public-dataset-quality` 新口径一致；③ `training-eval.md`·`methodology-references.md` 为 `P_norm` 加「自造归一化变体、非文献 Popt」标注 | |
| 2026-10-13 | 2.13 | **一步到位落实课程附加功能 (3)(4)**（蒋励的活）：① 新增 change `public-dataset-quality`（6 Requirement / 21 tasks，`validate` 通过）逐条回应 (3) 三缺陷——标签粒度过粗、主要针对 Java、数据质量；**第 0 号任务为「可下载性验证」，不过则整体降级并如实写明原因，不虚构数据**；② `semantic-feature-mainline` 补 **D9 评测协议对齐文献标准**（查证确认未在测试集上调参；但 `P_norm` 是自造变体而非文献标准，须补 CE@20% / Recall@20% / Popt / ALPA，并补 Wilcoxon 显著性检验与显式基线）、**D10 形态说明**（我们是「预训练提特征→经典分类器」混合形态，非端到端，不得暗示复现 SOTA）、D11 三组设置口径统一；tasks 增至 39 条；③ `feature-addons-sprint3` 的 G1-3 移出并留痕，删除旧 `specs/public-dataset`；④ 全量校验：3/4 change valid（`frontend-integration` 仍失败，属刘帅华线，已派活未代修） |
| 2026-10-13 | 2.12 | 模型线路范围调整：语义特征提升为主线（蒋励的活）：① 新增 change `semantic-feature-mainline`（proposal/design/specs/tasks 四件，`openspec validate --strict` **通过**，7 Requirement / 10 Scenario / 29 tasks），Sprint 2 启动，Kamei 14 降为基线对照组；② `feature-addons-sprint3` 的 G1-4 移出（proposal/design/tasks 同步改为「已顶替」留痕，删除旧 `specs/semantic-feature`），避免双入口；③ `design/addons.md` §4 改写为「已提升为模型线主线」并更新排期（Sprint 3 → Sprint 2–3）；④ **修复 `openspec/config.yaml` 的 YAML 解析错误**（我此前编辑引入，导致 `rules.tasks` 被 CLI 忽略 —— 多行 list 项改单行后 `openspec list` 不再告警）；⑤ 论文方法论补两项：专家特征留一法消融 + 置换重要性、跨项目不可迁移显式登记；⑥ 顺带发现 `frontend-integration` 校验失败（spec 缺 delta 头与 Scenario），**未代修**，已派活刘帅华 |
| 2026-10-14 | 2.16 | 蒋励 | **`docs/model` 去冗余合并（5 篇 → 4 篇）**：`training-eval.md` 并入 `model-line-plan.md`（8 模型与选型→§2.1、超参与口径登记→§2.3、切分铁规矩与两类指标→§4.1/§4.2、覆盖矩阵→§4.3、校准与阈值→§4.4、验收双轨→§4.5、交付边界→§6、SHAP→§7），**消除「8 模型清单 / 两类指标 / 交付边界」三处重复**；合并后按「数据线（`data-pipeline.md`）/ 模型线（`model-line-plan.md`）/ 契约（`feature-columns.md`）/ 导航（`README.md`）」切分，职责互斥。**`data-pipeline.md` 与 `feature-columns.md` 刻意不并** —— 前者被 42 处引用（含 24 处代码 docstring），后者是跨线冻结契约。同时清掉 `model-line-plan.md` 里**残留的旧仓库实测 AUC 数字**（与"换库后不引用旧数字"口径冲突）与「`lgbm`/`et`/`svm`/`tabnet` 暂无实现」的过期状态。引用同步更新于 `docs/README.md`、`docs/model/README.md`、`docs/design/{engineering,addons}.md`、`docs/common/test-plan.md`、`docs/repo/defect-records.md`、`openspec/changes/semantic-feature-mainline/tasks.md`、`data_model/{README.md,06_train_model.py}`。**历史留痕不改**：各文档变更日志与 `repo/catchup-ledger.md` 中的旧文件名属合法快照 |
| 2026-10-14 | 2.13 | 蒋励 | **训练口径自审与三处订正（"标准做法不可折损"）**：按「口径统一 + 标准做法 + 不因算力折损」逐模型自审，查出并修正三处折损 —— ① `lgbm` 的 `subsample=0.9` 因 `subsample_freq` 默认 0 而**空转**（静默不生效），补 `subsample_freq=1`；② `tabnet` 的 `patience=15` 因未向 pytorch-tabnet 传 `eval_set` 而**静默失效**（实际跑满 `max_epochs`），改用 `TabNetWithEarlyStop` 包装器，从**训练集内部**切验证子集传 `eval_set`，与 `mlp_deep` 同语义；③ `svm` 的 `probability=True` 实为 libsvm 内部 5 折 Platt 校准概率，**保留但如实登记**（改了会破坏 8 模型 `predict_proba` 口径一致）。新增 `model/training-eval.md` §2.1「超参与口径登记表」（8 模型超参 / 停止方式 / 可逐字节复现性 / 三条口径 + 两条主动选择理由），`data_model/README.md` §模型覆盖补「选型前提（不可折损）」|
| 2026-10-14 | 2.12 | 蒋励 | **数据源换库（ActiveMQ → Apache Camel）+ 模型线性能优先选型全局同步**：① 主对象确定为 **Apache Camel**（tag `camel-4.23.0` / commit `b2329103…`），`docs/design`（架构 / 边界 / 数据字段 / 数据库 / 工程 / 非功能 / 图注）、`docs/common`（开发手册校验命令 / 验收 M1）、`docs/model`（方案 / 数据链路 / 训练评估 / 包 README）、根 `README.md`、`AGENTS.md`、`openspec/config.yaml` 与三份活跃 change 全部同步；② 数据字段 `repo_name` 固定值 `activemq` → `camel`；③ 判据与统计的旧仓库专属数字（提交数 / 正样本比例 / 外沿条数 / 实测指标矩阵）**一律删除或改为「待 Camel 实测回填」**，不保留旧值；④ 模型线由「`lr`/`rf`/`xgb`/`nb`/`dt`/`knn` + `mlp`/`mlp_deep`」改为**性能优先 8 个**（经典 6：`lr`/`rf`/`xgb`/`lgbm`/`et`/`svm`；神经 2：`mlp_deep`/`tabnet`），代码（`06`/`08`/`16`）、前端 `constants.js` 与契约测试、`training-eval.md` §2 与 `design/engineering.md` 模型清单同步；⑤ 删除旧仓库的训练文件与全部旧评估报告。**历史留痕不改**：`openspec/changes/archive/**`、各文档变更日志与 `repo/catchup-ledger.md` 的过往条目属合法快照，保持原样 |
| 2026-10-13 | 2.11 | openspec 格式把关人落规（组长指派苏哲勋）：① `common/openspec-task-template.md` 新增 §6「PR 审阅时的 openspec 检查清单」——十项逐份检查 + 一致性抽查 + 结论三写法，**把关不代改、只管增量**；② `repo/collaboration.md` PR 审阅清单由六项改**七项**（新增「openspec 格式合规」）并写明把关人与增量口径；③ `repo/README.md` 苏哲勋职责新增第 6 条；④ 1009 周报本周计划对应任务同步指向 §6 |
| 2026-10-13 | 2.10 | 分工边界订正 + 蒋励的活落地：① **组长不包揽** —— 明确各组只对自已那条线负责，他人任务一律进飞书《工作周报》本周计划并责任到人，组长只做标准/模板/统稿与验收把关；② 蒋励补齐数据线单测 51 条（`test_szz_labeling.py` 34 + `test_split_dataset.py` 17），数据线 8 → **59 条全绿**，`test-strategy.md` §3.1 记录过程（含测试抓到本人两个错误预期）；③ 1009 周报本周计划清掉 2 条模板脏数据，写入 **8 条责任到人**任务（蒋励 2 / 刘帅华 2 / 吕建江 2 / 苏哲勋 2，含 openspec 风格统一把关归苏哲勋） |
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
