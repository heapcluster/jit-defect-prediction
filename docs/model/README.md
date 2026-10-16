# model 包（数据与模型）· 蒋励

> **打开这个文件夹就能知道：你负责什么、最近要干什么、每次任务怎么干、改东西的红线在哪。**
> 包负责人：**蒋励**（数据与模型线，兼组长/SM）｜ 代码目录：`data_model/` ｜ 审核：苏哲勋
> 配套依据：飞书 Epic **A 数据采集与缺陷标注 / B 特征工程与样本集 / C 模型训练与评估**；OpenSpec specs `labeled-dataset` `szz-labeling` `feature-extraction` `model-training` `model-delivery` `model-coverage`。

---

## 1. 你的职责

数据与模型线负责人 + 项目组 SM：从真实开源仓库挖数据 → 打缺陷标签 → 算 Kamei 14 维特征 → 训练 ≥8 种模型 → 出两类评估指标与 SHAP 解释，并把「模型文件 + `prediction_result.csv`」按方案 A+C 交给后端。

**Sprint 2 起主线升级**：CodeBERT / GraphCodeBERT 语义特征升为技术主线，Kamei 14 降为基线对照组；三类设置（仅专家 / 仅语义 / 融合）同一时间序切分、同一 8 模型、同一套指标对比，并探索端到端第四类（详细方案见 `model-line-plan.md`）；评估对齐文献标准 effort-aware。同时统稿公共文档、每周五收各人供稿写周报。

**2026-10-14 换库**：主对象确定为 **Apache Camel**（tag `camel-4.23.0`、JIRA `CAMEL-`），原 ActiveMQ 方案及其数据、模型与报告已一并废弃清理。详细见 `model-line-plan.md` §5。

## 2. 谁依赖你 / 你依赖谁（阻塞关系）

| 方向 | 对象 | 依赖什么 | 卡住的后果 |
|---|---|---|---|
| **你依赖** | `repo/`（苏哲勋） | 分支模型 + OpenSpec SDD 流程 + 缺陷管理 | 改动不走 change = **SDD 缺陷（一票否决）** |
| **你依赖** | Apache Camel 仓库（tag `camel-4.23.0`） | 可克隆的完整 Git 历史 | 数据链路断在第一步 |
| **被你依赖** | `backend/`（吕建江） | 跨线交付方案 A+C：`data_model/models/*.pkl` + `feature_order.txt` | 在线预测无法加载 |
| **被你依赖** | `frontend/`（刘帅华） | `feature-columns.md` 14 项列名 | 解释条取不到值、静默空白 |
| **被你依赖** | `design/addons.md` G1-3 / G1-4 | 公开数据集加载与语义特征路线 | 附加功能无来源 |

## 3. 任务清单

| # | 任务 | 验收 | 状态 |
|---|---|---|---|
| J1 | 端到端演示准备（风险列表→详情归因→趋势看板）+ 脚本 + 录屏 | 正向 + ≥1 异常输入；录屏入库 | 🔄 |
| J2 | 归档 change `model-expansion` | `openspec validate --all --strict` 通过 | ✅ |
| J3 | 仓库卫生（删陈旧分支、origin 统一） | `git remote -v` 指向团队仓 | ✅ |
| J4 | 周报常态化（1009/1016/1023 周五） | 三份周报与看板/Git 对得上 | 🔄 |
| J5 | 每周五收供稿统稿、提交前对账 | 每周留痕 | 🔄 |
| J6 | 补勾已归档 `data-collection` change 5.4 | tasks 全勾 | ✅ |
| J7 | 四项附加功能立项（G1-1/G1-2 → `feature-addons-sprint3`；G1-3 → `public-dataset-quality`；G1-4 → `semantic-feature-mainline`） | 看板新增行 | ✅ |

> 实时状态以飞书看板为准；J1 是 Sprint 1（10/23）课上验收主证据。

## 4. 每次接任务的标准动作（必须走 OpenSpec）

1. 认领：飞板置「进行中」。2. 动规格先提 change。3. 特征口径升级 → `feature_version` 升 `v2` 全量重算，不覆盖 v1。4. 实现 + 同步规格（下游对照产物重跑）。5. 自测：两类指标齐全；时间序切分禁随机。6. 提 PR（描述写 change id）。7. 归档 + 回写。

> ⚠️ 只勾 `tasks.md` ≠ 功能合格；改需求只改码不改规格 = 缺陷；复现性 ±0（别人照命令跑出同一份统计）。

## 5. 本包交付物与课程对应

| 课程要求 | 本包落地 |
|---|---|
| 真实开源仓库挖掘 | Apache Camel 固定 tag |
| SZZ 算法实现 | 自研标准行级 + 文件级简化版 |
| Kamei 14 度量元（现降基线） | `feature-columns.md` |
| ≥2 类不少于 8 种模型 | 性能优先 8 个：`rf`/`xgb`/`lgbm`/`et`/`svm`/`lr` + `mlp_deep`/`tabnet`，选型与超参见 `model-line-plan.md` §2.1 / §2.3 |
| 两类评估指标 | Effort-unaware + 标准 effort-aware（`model-line-plan.md` §4.2） |
| 训练/测试划分 | 按 `committed_at` 时间序，禁随机 |
| 缺陷概率 + 归因 | SHAP 逐特征带 `direction`（`model-line-plan.md` §7） |
| 附加功能 G1-1/G1-2/G1-3/G1-4 | 见 `design/addons.md` |

## 6. 红线

- **不碰**接口 / 页面 / 库表（跨线交付 A+C：模型文件 + `prediction_result.csv`）。
- **特征零漂移**：14 项键名与 `feature-columns.md` 一致，前后端共用同一套。
- **数据版本固定**：主对象锁 **Apache Camel**（`camel-4.23.0`）。报告出总数 / 正负样本 / 比例。
- **模型加载**：`*.pkl` 用 `joblib.load`（lr/rf 是 joblib、xgb 是标准 pickle）。
- **语义线**：向量落 `v2`、**不入库、不进交付链**；契约二 14 项一字不动；**不静默切换交付模型**；`P_norm` 是自造变体，不得当 `Popt` 宣称。

## 7. 相关 change 与口径升级

| change | 覆盖 | 状态 |
|---|---|---|
| `data-collection-and-szz-labeling` | 数据/特征 ①–⑤ | 已归档 |
| `model-training-and-delivery` | 训练/全量预测 ⑥⑦ | 已实现 |
| `model-expansion` | 覆盖矩阵/校准 ⑧⑨ | 已实现 |
| `semantic-feature-mainline` | 语义特征主线 ⑩–⑯ | 🔄 Sprint 2 |
| `public-dataset-quality` | G1-3 公开数据集治理 | ⬜ Sprint 2–3 |

- 口径改动 → 升 `feature_version` 全量重算，不覆盖旧版；改了判据 / 口径 / 依赖版本 → 下游对照产物全部重跑。

## 8. 验收标准（M1–M10）

| # | 板块 | 效果 | 证据 / 一票否决 |
|---|---|---|---|
| M1 | 数据可复现 | 主对象 Apache Camel 固定 tag `camel-4.23.0`，跑出同一份统计（±0） | 版本浮动 `main` = 否决 |
| M2 | SZZ 打标 | 两套均跑、差异量化；D4 词首边界 | `szz_labeling_stats.md` |
| M3 | Kamei 14 特征 | 口径一致、键名同源 | 三处键名不一致 = 否决 |
| M4 | 8 模型 / 2 类 | 经典 + 深度学习齐全，两类指标 | `model_matrix.md`；只报一类 = 否决 |
| M5 | 时间序切分 | 前 70% / 后 30%，禁随机 | `--selfcheck` 通过 |
| M6 | 全量预测交付 | `prediction_result.csv` 字段 = 契约一表三 | 夹带契约外字段 = 否决 |
| M7 | 解释 SHAP | `explanation[]` 逐特征带 direction | 与查询/实时接口结构不一致 = 否决 |
| M8 | 校准与阈值 | 时间序折校准 + 阈值/配额对照 | `calibration_threshold.md` |
| M9 | 语义特征主线 | v2 落盘、三类对比同切分同 8 模型 | 语义入库/进交付链、切分不一致 = 否决 |
| M10 | 评测协议与显著性 | 两类指标齐全 + Bootstrap/Wilcoxon/McNemar + 多切分稳健 | `P_norm` 当 `Popt` 宣称 = 否决 |

## 9. 方法依据与文献（答辩抽查）

> 起因：2026-10-13 课堂反馈「模型训练不能全依赖 AI，需自己读论文搞清楚」。本节把「为什么这么做」落到可核验出处 + 本组判断。

**文献清单（出处 + 我们用了哪一条）**：

| 编号 | 文献 | 我们用到的 |
|---|---|---|
| A-1 | Śliwerski, Zimmermann, Zeller, *When Do Changes Induce Fixes?*, MSR '05 | 缺陷引入 = 对修复提交中被删/改的行，在父提交 `git blame` |
| A-3 | da Costa 等, *A Framework for Evaluating the Results of the SZZ Approach*, IEEE TSE | SZZ 结果需评估而非默认正确 → 本组做两套 SZZ 对照 |
| B-1 | Nagappan, Ball, Zeller, *Mining Metrics to Predict Component Failures*, ICSE '06 | 14 项变更度量（Kamei 14）原始出处 |
| B-2 | Hassan, *Predicting Faults Using the Complexity of Code Changes*, ICSE '09 | Entropy = 两周滚动窗口内改动文件的信息熵 |
| B-3 | Kamei, Shihab, *Defect Prediction: Accomplishments and Future Directions*, PROMISE '16 | 问题 framing + effort-aware 必要性 |
| C-1 | Mende & Koschke, *Effort-aware Defect Prediction Models*, ICSM '10 | 只报 AUC/F1 会被工作量代理带偏 → 两类指标同报 |

**关键决策 ↔ 文献 ↔ 实现 ↔ 偏离**（详证见 `data-pipeline.md` 与各脚本 docstring）：

| 决策 | 依据 | 本组实现与偏离 |
|---|---|---|
| 修复提交判据 = `CAMEL-\d+` **且**修复语义词首边界 | A-1 未定义「什么是修复提交」 | D4：只用编号会收 54.7% 噪声，子串匹配误收 122 条 → 取词首边界 |
| 两套 SZZ 并行（行级 + 文件级） | A-3 | `szz_lite` 本组自研，差异量化出示 |
| PySZZ 不可用 → 自研标准行级 | A-1（不依赖具体工具） | PyPI 404 → 自研实现 |
| `rexp` 衰减 = `Σ count(n)/(n+1)` | B-1 原文口径 | 以原文补契约 |
| 时间序切分（禁随机） | B-3 / C-1 | EXP/NUC 与时间强相关 |
| 两类指标同报 + `P_norm` 标注自造 | C-1 | LOC 代理下 `P_norm` 负值如实报告（Issue #37） |
| 阈值 `p ≥ 0.50` | **无论文依据** | 本组口径选择，Issue #38 登记，不得当论文结论 |

**答辩 30 秒讲法**：① 指标是文献定义的 14 项（Nagappan 2006，通称 Kamei 14）；② SZZ 读 Śliwerski 2005，PySZZ 在 PyPI 404 故自研，并加文件级对照、差异量化；③ 打标判据文献没给，是实测外沿数字后自定（词首边界）；④ 切分必须时间序（EXP/NUC 与时间相关，随机=看未来）；⑤ effort-aware 负值没藏（Issue #37），阈值是口径选择非论文结论。

## 10. 子文件导航（4 篇 + `pipelines/` 5 篇）

- `model-line-plan.md` — **模型线唯一权威入口**：方案（特征层 / 模型层 / 四类对比）+ 模型与超参（§2）+ 评估与验收口径（§4）+ SHAP（§7）+ 执行计划 P0–P7 / DoD / Gate（§8）
- `data-pipeline.md` — 数据链路九步 + 版本固定 + 复现命令 + 必须报出的统计 + SZZ 局限
- `feature-columns.md` — 契约二 14 项特征列名（已冻结，与后端/前端共用）
- `pipelines/` — **四类设置分线目录**（仅专家 / 仅语义 / 融合 / 端到端 = 四份 pipeline），每线一篇**自包含**文档（无 README）：`expert-only.md` / `semantic-only.md` / `fused.md` / `end-to-end.md`。每篇写全「用途 / 适用场景 / 核心步骤 / 输入输出 / 配置项及作用 / 与其他线的边界协作 / 红线」七节，**不依赖 `data-pipeline.md`**，照单篇即可开工与复查；各自的产物命名纪律写在该篇「输出」节（报告名带线名，四线同名即互相覆盖）
- `README.md` — 本文件（包导航 + 职责 + 红线 + 验收 + 方法依据）

> **合并说明（2026-10-14 两轮精简：9 篇 → 4 篇）**：
> ① 第一轮：`model-line-execution-plan.md` → `model-line-plan.md` §8；`acceptance.md` → 本文件 §8；`explanation.md` → SHAP 一节；`methodology-references.md` → 本文件 §9。
> ② 第二轮（去冗余）：**`training-eval.md` → `model-line-plan.md`**（8 模型与选型 → §2.1、超参与口径登记 → §2.3、切分规矩与两类指标 → §4.1/§4.2、覆盖矩阵 → §4.3、校准 → §4.4、验收双轨 → §4.5、交付 → §6、SHAP → §7）。合并理由：原三篇同属"模型线"，存在「8 模型清单」「两类指标」「交付边界」三处重复；合并后按「**数据线 / 模型线 / 契约 / 导航**」切分，职责互斥。
> ③ **`data-pipeline.md` 刻意不并**：它被 42 处引用（含 24 处代码 docstring），改名成本远大于收益；`feature-columns.md` 是跨线契约，必须独立。
> ④ **第三轮（2026-10-14）：按四条 pipeline 分目录，新增 `pipelines/`**。四类设置（仅专家 / 仅语义 / 融合 / 端到端）的用途、步骤、输入输出与配置各不相同，混写会互相覆盖口径（产物同名首当其冲），故每线一篇**自包含**文档（七节统一结构，**不依赖 `data-pipeline.md`**）。**三个被大量引用的文件一个都没动**，只在 `model-line-plan.md` §3 与 `data-pipeline.md` §4 各加一行指路。产物同名覆盖问题由每篇「输出」节的命名纪律收敛（expert 线现名不改，新线报告名一律带 `_semantic` / `_fused` / `e2e` 线名）。

## 11. 先读 common 里的哪几份

打开 `common/`：`course-requirements.md`、`openspec-rules.md`、`dev-handbook.md` §2、`team-charter.md`。**common + 本文件 = 你开展工作的全部依据。**
