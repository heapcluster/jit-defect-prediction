# model 包（数据与模型）· 蒋励

> **你打开这个文件夹就能知道：你负责什么、最近要干什么、每次任务怎么干、改东西的红线在哪。**
> 包负责人：**蒋励**（数据与模型线，兼组长/SM）｜ 代码目录：`data_model/` ｜ 审核：苏哲勋
> 配套依据：飞书《产品需求文档》Epic **A 数据采集与缺陷标注 / B 特征工程与样本集 / C 模型训练与评估**；OpenSpec specs `labeled-dataset` `szz-labeling` `feature-extraction` `model-training` `model-delivery` `model-coverage`。

---

## 0. 👤 你的职责一句话

你是**数据与模型线负责人 + 项目组 SM**：从真实开源仓库挖数据、打缺陷标签、算 Kamei 14 维特征、训练 ≥8 种模型、出两类评估指标与 SHAP 解释，并把「模型文件 + `prediction_result.csv`」按方案 A+C 交给后端。同时统稿公共文档、每周五收各人供稿写周报。

## 0.5 谁依赖你 / 你依赖谁（阻塞关系）

| 方向 | 对象 | 依赖什么 | 卡住的后果 |
|---|---|---|---|
| **你依赖** | `repo/`（苏哲勋） | 分支模型 + OpenSpec SDD 流程 + 缺陷管理 | 改动不走 change = **SDD 缺陷（一票否决）** |
| **你依赖** | ActiveMQ 仓库（固定 `activemq-5.18.7`） | 可克隆的完整 Git 历史（SZZ 需要 fix 与引入方的对应关系） | 数据链路断在第一步 |
| **被你依赖** | `backend/`（吕建江） | **跨线交付方案 A+C**：`data_model/models/*.pkl` + `feature_order.txt`（14 项顺序 + `[models]` 段） | 在线预测无法加载，整条链路断 |
| **被你依赖** | `frontend/`（刘帅华） | `model/feature-columns.md` 14 项列名（详情页解释条与特征分组） | 解释条取不到值、静默空白 |
| **被你依赖** | `design/addons.md` G1-3 / G1-4 | 公开数据集加载与语义特征路线 | 附加功能无数据与特征来源 |

## 1. 📋 你的任务清单（来自进度台账，带验收与下一步）

| # | 任务 | 验收标准 | 状态 | 你下一步 |
|---|---|---|---|---|
| **J1** | 端到端演示准备（一条提交走完 风险列表→详情归因→趋势看板）+ 脚本+录屏 | 含正向+≥1 异常输入验证；录屏入库 | 🔄进行中 | 系统实跑后补录屏，脚本已建 `docs/repo/demo-script-sprint1.md` |
| J2 | 归档 change `model-expansion` | `openspec validate --all --strict` 通过 | ✅已完成 | 已 archive，`model-coverage` 入库 |
| J3 | 仓库卫生（删陈旧分支、origin 统一 heapcluster） | `git remote -v` 指向团队仓 | ✅已完成 | 达标 |
| **J4** | 周报常态化（1009/1016/1023 周五晚提交） | 三份周报链接，与看板/Git 对得上 | ⬜未开始 | 每周五 17:00 前收供稿统稿 |
| **J5** | 每周五收各人供稿并统稿，提交前对账（周报=看板=Git） | 每周留痕 | 🔄进行中 | 常态项 |
| J6 | 补勾已归档 `data-collection` change 5.4（回看板） | tasks 全勾；看板状态真实 | ✅已完成 | 已勾 |
| J7 | 四项附加功能（G1-1 缺陷可视化定位 / G1-2 高质量修复建议 / G1-3 公开数据集加载与治理 / G1-4 预训练语义特征建模）立项 | 看板新增 Sprint3 四行 / 立 change | ✅已完成 | 已立 `feature-addons-sprint3/`（含 `specs/public-dataset`、`specs/semantic-feature`）；看板 Sprint3 四行 G1-1~G1-4 |

> 实时状态以**飞书看板**为准。J1 是 Sprint 1（10/23）课上验收主证据，优先。

## 2. 🚀 后续工作开展方式（每次接到任务的标准动作 · 必须走 OpenSpec）

1. **认领**：飞板置「进行中」（你也是 SM，负责把任务分派并回收状态）。
2. **动规格先提 change**：改特征口径 / 切分方式 / 标签方法 → 提 change（`data-collection-and-szz-labeling`、`model-training-and-delivery`、`model-expansion` 等）。
3. **特征口径升级**：`feature_version` 升 `v2` 并全量重算，**不覆盖 v1**。
4. **实现 + 同步规格**：改了判据/口径/依赖版本 → 所有下游对照产物重跑（`data-pipeline.md` 踩坑清单）。
5. **自测**：评估报告覆盖两类指标（Effort-unaware + Effort-aware）；时间序切分（前 70%/后 30%），**禁随机**。
6. **提 PR**（文档类走 §3.7 强制合入）：描述写 change id；你的 PR 由苏哲勋审。
7. **归档 + 回写**：change 全勾且有运行证据 → `openspec archive`；看板置完成 + 周报记证据。

> ⚠️ 课程硬要求：**只勾 `tasks.md` ≠ 功能合格**；改需求只改码不改规格 = 缺陷；复现性：别人照命令跑出同一份统计（±0）。

## 3. 🚫 你的红线

- **不碰**：接口、页面、库表（跨线交付方案 A+C：模型文件 + `prediction_result.csv` 给后端）。
- **特征零漂移**：14 项特征字段名与 `feature-columns.md` 一致；下游（后端 `commit_feature` 表、前端解释区）共用同一套列名。
- **数据版本固定**：ActiveMQ 锁 `activemq-5.18.7`，报告出总数/正负样本/比例。
- **模型加载口径**：`*.pkl` 用 `joblib.load`（lr/rf 是 joblib、xgb 是标准 pickle，见交付清单）。

## 4. 本包交付物与课程对应

| 课程要求 | 本包落地 |
|---|---|
| 真实开源仓库挖掘历史数据 | ActiveMQ 固定 tag |
| SZZ 算法实现 | 自研标准行级 + 文件级简化版 |
| Kamei 14 维度量元 | `feature-columns.md` |
| ≥2 类不少于 8 种模型 | 经典 6（`lr` `rf` `xgb` `nb` `dt` `knn`）+ 神经网络 2（`mlp_v1` `mlp_deep_v1`），已实测达标 |
| 两类评估指标 | Effort-unaware + Effort-aware（实测见 `training-eval.md` §4） |
| 训练/测试集划分 | 按 `committed_at` 时间序，禁随机 |
| 缺陷概率 + 归因/解释 | SHAP 逐特征带 `direction` |
| 可选附加（G1-3/G1-4） | 公开数据集加载与治理 / 预训练语义特征建模（立项，详设 `design/addons.md`） |

## 5. 子文件导航

- `data-pipeline.md` — 数据链路九步、版本固定、复现、统计（合并自 `docs/model/data-pipeline.md`）
- `training-eval.md` — 训练/评估/8 模型/两类指标/校准阈值
- `methodology-references.md` — **方法依据与文献阅读记录**（6 篇文献 + 8 条方法决策↔文献↔实现↔偏离 + 阅读签注表；2026-10-13 课堂反馈「不能全依赖 AI」）
- `explanation.md` — SHAP 缺陷归因解释
- `feature-columns.md` — 14 项特征口径（与后端/前端共用列名）
- `a2-4-correction.md` — S6+1：A2-4 判据方向订正（仓库侧已对齐，待贴飞书）
- `openspec-compliance.md` — 数据/模型线改动如何走 change
- `acceptance.md` — 模型验收功能板块

## 6. 先读 common 里的哪几份

打开 `common/`：`course-requirements.md`（课程要求全文+映射）、`openspec-rules.md`（每次改动必须走规范）、`dev-handbook.md` §2（跑通数据线）、`team-charter.md`（分工）。**common + 本文件 = 你开展工作的全部依据。**
