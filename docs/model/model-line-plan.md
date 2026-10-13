# 模型线路方案与改造计划（蒋励 · 数据与模型线）

> 版本 1.0 ｜ 起草 2026-10-13 ｜ 负责人 **蒋励**（数据与模型线 + 组长/SM）｜ 审核 苏哲勋
> 关联 OpenSpec change：`semantic-feature-mainline`（语义特征主线）、`public-dataset-quality`（G1-3 公开数据集治理）、`feature-addons-sprint3`（G1-1/G1-2 前端展示侧）
> 本文是模型线「**当前方案 + 改造执行清单**」的唯一权威入口；答辩陈述、周报本周计划、飞书文档均以本文为基准。
> 本文不重复 proposal/design 的技术细节，只给「方案结论 + 为什么 + 谁来做 + 做到哪」。

---

## 0. 一句话方案（先读这句，避免误判）

> **聚焦单一仓库 ActiveMQ（`activemq-5.18.7`，11,050 次提交）；Kamei 14 专家特征降为基线对照组，CodeBERT/GraphCodeBERT 语义特征提升为模型线主线；8 个模型跑「仅专家 / 仅语义 / 融合」三类设置对比；评估对齐文献标准（Effort-unaware + 标准 effort-aware），`P_norm` 明确标注为本组自造变体；不静默切换交付模型、不跨项目预测、不端到端复现 SOTA。**

---

## 1. 当前模型线路方案（已确定，经童老师 2026-10-13 指导）

### 1.1 聚焦单一仓库（不跨项目）

- **主对象**：Apache ActiveMQ `activemq-5.18.7`，约 **11,050 次提交**，SZZ 两种口径标注：`szz` 正例 38.98% / `szz_lite` 正例 27.74%。
- **为什么只做一个仓库（答辩必问）**：Kamei et al. 2013（IEEE TSE 39(6):757–773）核心结论——JIT 预测**项目内可用、跨项目不可迁移**。一个模型换仓库即失效，「一个模型测任何仓库」在 JIT 领域是伪命题。
- **管线可扩展、模型逐个训**：数据管线通过 `RepoSource` 插件化（`design/engineering.md` §4.3）做到仓库无关；但每个仓库的模型要重训。系统正确形态 = 管线能测别的仓库、模型要重训。详见 `design/sprint0-scope.md`。
- **SZZ 局限已登记**：代理标注非 ground truth、blame 追溯过远、对重构敏感、定义不稳定（两套正样本差 11.16pp）、D4 判据为自定启发式——五条局限写入 `docs/model/data-pipeline.md` §7.1，如实报告不包装。

### 1.2 特征与模型分层

| 层 | 内容 | 定位 |
|---|---|---|
| 基线（原主线，现对照） | **Kamei 14 项专家特征**（变更度量元） | 课程必做；保留为基线对照组，契约二 14 项列名与顺序不动 |
| **主线（核心）** | **CodeBERT / GraphCodeBERT** 语义特征（代码专用预训练） | 课程附加功能 (4) 点名的「现在主流方法」；Sprint 2 启动 |
| 弱基线（可选/可砍） | `all-MiniLM-L6-v2`（通用句向量，非代码专用） | 域不匹配，仅作「非代码预训练」对照，进度紧可直接砍 |
| 交付模型 | **8 个模型**（经典 6 + 神经网络 2），三类设置各跑同一套 | 见 `training-eval.md` §2；交付边界由 `model-coverage` R6 规定 |

- **三类设置对比**（同一时间序切分、同一测试集、同一 8 模型、同一套指标）：仅 Kamei 14 / 仅语义 / 融合。产出 `data_model/reports/three_way_comparison.md`。
- **订正记录**：初版曾把 MiniLM 设为「打底全量」、CodeBERT 设为「抽样增强」，与文献主流方向相反，已订正（见 `semantic-feature-mainline/design.md` D1）。

### 1.3 训练「不依赖 AI」（童老师反馈 1）

- 必须读论文并手写核心逻辑：Kamei 2013、Śliwerski 2005（SZZ）、DeepJIT/CC2Vec 等；方法依据与文献阅读签注见 `docs/model/methodology-references.md`（6 篇文献 + 8 条方法决策↔文献↔实现↔偏离 + 阅读签注表）。
- 蒋励自身已完成**数据线单元测试 59 条**（`test_szz_labeling.py` 34 + `test_split_dataset.py` 17，与 `jit-defect` 环境既有 8 条合并全绿），过程见 `common/test-strategy.md` §3.1。

### 1.4 评估标准化（修正自造指标）

- **Effort-unaware（全套）**：AUC / F1 / Precision / Recall / Accuracy。
- **Effort-aware（文献标准，替换自造 `P_norm` 的单一口径）**：CE@20% / Recall@20% / Popt / ALPA；`P_norm` **保留但标注为本组自造归一化变体（锚点取实测随机均值与上界），与文献 `Popt` 非同一指标**，仅作内部对照，不得对外宣称「标准 effort-aware 指标」。
- **统计检验**：Wilcoxon signed-rank（+ McNemar）显著性检验，8 模型在同一测试集上配对比较。
- **显式基线**：随机排序（200 次抽样均值 ± 标准差）、上界（真实缺陷密度降序）、两种工作量代理（LOC 与改动文件数）。
- **形态说明（答辩口径）**：本组是「预训练提特征 → 经典分类器」混合形态，**不是** DeepJIT/CC2Vec 式端到端，不得暗示复现 SOTA（见 `semantic-feature-mainline/design.md` D10）。

### 1.5 范围与协作控制

- **组长不包揽**：蒋励只做数据线/评估/方法依据自己的任务；他人任务进飞书《工作周报》本周计划并责任到人。
- **openspec 风格把关**：苏哲勋负责（增量审查、把关不代改），规则见 `common/openspec-task-template.md` §6。
- **不切换交付模型**：单一技术栈；切换须另开「模型切换」提案（`model-coverage` R6），走契约三变更流程。

---

## 2. 为什么这样定（教师指导 + 文献依据 = 答辩口径）

| 维度 | 旧方案 / 易被质疑的表述 | 当前方案（已确定） | 依据 |
|---|---|---|---|
| 仓库范围 | 「测任何仓库」「多仓库」 | **单仓库 ActiveMQ**，管线插件化可扩展 | Kamei 2013：跨项目不可迁移 |
| 特征 | Kamei 14 是唯一主线；语义特征「可选附加、Sprint 3 才做」 | **CodeBERT 语义特征为主线**；Kamei 14 降基线 | 课程附加功能 (4)：现在主流是预训练语义特征；童老师「不能采用老旧方案」 |
| 语义模型 | MiniLM 打底全量 | **CodeBERT/GraphCodeBERT 主路线**；MiniLM 仅弱基线/可砍 | 代码专用预训练 vs 通用句向量域不匹配 |
| 评估 | 只报自造 `P_norm` | **标准 effort-aware（CE@20%/Recall@20%/Popt/ALPA）+ Wilcoxon**；`P_norm` 标注自造 | 文献 effort-aware 标准口径 |
| 交付 | 语义更优就静默替换 | **不静默切换**，须另开模型切换提案 | `model-coverage` R6 硬约束 |
| 形态 | 暗示端到端 SOTA | **特征式混合**，如实说明非端到端 | D10 答辩纪律 |

---

## 3. 改造计划（执行清单，责任到人）

> 状态口径：🔄 进行中 / ✅ 已完成 / ⬜ 未开始 / 🔶 阻塞前置（torch 可装性、数据集可下载性）。
> **端到端执行计划（启动 → 完成）**：见 `docs/model/model-line-execution-plan.md`（阶段编排 P0–P7 / 依赖关系 / 里程碑 Gate / 完成定义 DoD / 复现命令）；本节为按 SF·PD·EV 编号的任务主清单。

### 3.1 语义特征主线 — change `semantic-feature-mainline`（39 tasks，Sprint 2 启动）

| # | 任务 | 负责人 | 交付物 / 验收 | 状态 |
|---|---|---|---|---|
| SF-1 | 独立环境 `jit-defect-prediction` 装 `torch`+`transformers`，统一并入单环境 `jit-defect-prediction`（原 `jit-defect` 改名） | 蒋励 | 环境就绪，87+59 测试仍绿 | ✅ 已完成 |
| SF-2 | 100 条基准测试定时限（CodeBERT CPU 单条约 50–150ms） | 蒋励 | 实测耗时报告，决定全量/抽样 | ⬜ |
| SF-3 | 按文件构造变更文本（路径+类型+增删行+提交首行），超长截断并记统计 | 蒋励 | `10_*` 脚本 + 截断统计 | ⬜ |
| SF-4 | 语义向量落盘 `semantic_<model>_v2.csv`（新 `feature_version=v2`，不入库） | 蒋励 | 落盘文件 + 契约二 14 项不动 | ⬜ |
| SF-5 | 三类设置对比（仅专家/仅语义/融合）同一切分同 8 模型 | 蒋励 | `reports/three_way_comparison.md` | ⬜ |
| SF-6 | 专家特征留一法消融 + 置换重要性（Kamei 14 效力排序） | 蒋励 | 消融报告 | ⬜ |
| SF-7 | 多切分点稳健性（60/40 与 80/20 各跑一遍，禁随机） | 蒋励 | 稳健性表（低于 D9） | ⬜ |

### 3.2 公开数据集治理 — change `public-dataset-quality`（21 tasks，Sprint 2–3）

| # | 任务 | 负责人 | 交付物 / 验收 | 状态 |
|---|---|---|---|---|
| PD-0 | **可下载性验证**（阻塞前置） | 蒋励 | 验证通过 / 不通过则降级并如实说明 | 🔶 阻塞前置（代理网络） |
| PD-1 | 公开 JIT 数据集加载器（对齐 `commit`/`commit_label`/`commit_feature`） | 蒋励 | 加载器脚本，缺字段报错终止不产半成品 | ⬜ |
| PD-2 | 三维度质量治理：标签粒度 / 语种分布 / 数据质量（缺失率·重复率·时间序一致性） | 蒋励 | 质量报告 | ⬜ |
| PD-3 | 多语言证据（非 Java 样本单列统计） | 蒋励 | 语种分布报告 | ⬜ |
| PD-4 | 与文献数字对照（若取到 OpenStack/Qt 等标准 benchmark） | 蒋励 | 量级对照表（**可选目标**，见 §4.2） | ⬜ |

### 3.3 评测协议对齐 — `semantic-feature-mainline` D9 / `training-eval.md`

| # | 任务 | 负责人 | 交付物 / 验收 | 状态 |
|---|---|---|---|---|
| EV-1 | 补 CE@20% / Recall@20% / Popt / ALPA 标准 effort-aware 指标 | 蒋励 | 指标进 `model_matrix.md` | ⬜ |
| EV-2 | Wilcoxon signed-rank + McNemar 显著性检验 | 蒋励 | 检验表 | ⬜ |
| EV-3 | `P_norm` 标注「自造变体非 Popt」（已落 `training-eval.md` §3、`methodology-references.md` §3） | 蒋励 | 文档标注已就位 | ✅ 已完成 |

### 3.4 文档口径统一（本文档所属的改动，2026-10-13）

- ✅ 已完成：`docs/README.md`、`design/addons.md`、`design/README.md`、`model/README.md`、`training-eval.md`、`methodology-references.md`、`user-story-traceability.md`、`repo/README.md`、`acceptance-overview.md`、`team-charter.md`、`defect-records.md` 中「语义可选 / 只立项不实现 / G1-3·G1-4 误挂 feature-addons-sprint3 / 失效 spec 路径 / P_norm 未标注」等旧表述已全部替换。
- 历史进度台账 `catchup-ledger.md` 保留其当时快照（其变更日志 1.21/1.22/1.23 已记录 G1-3/G1-4 移出更正）。

### 3.5 飞书同步（见第 4 节执行）

- 产品设计文档：模型线路方案章节更新为本文 §1。
- 产品需求文档：附加功能 Epic G 拆分为 G1-1/G1-2（可选附加）、G1-3（承诺范围）、G1-4（主线）的表述。
- 1009 周报「本周计划」：写入责任到人的模型线任务（SF/PD/EV 系列）。

### 3.6 阻塞前置与风险

| 阻塞/风险 | 应对 |
|---|---|
| `torch` 安装体量大、可能冲突 `jit-defect` | 独立环境 `jit-defect-prediction`；主线 87+59 测试不受影响 |
| CodeBERT CPU 全量耗时超预期 | 先 100 条基准定时限；超则抽样并**如实标注**，不谎报全量 |
| 公开数据集下载不到（代理不通） | PD-0 专门验证；不通过则降级为「加载器框架 + ActiveMQ 自验」，如实写明原因，**不虚构数据** |
| 语义指标不如专家特征（完全可能） | 如实报告；三类对比表本身就是交付物，「语义不占优」不是失败 |

---

## 4. 待补项（延续「补」指令）

### 4.1 N-01：8 模型交付清单口径

- **现状**：`model-coverage` spec 要求 8 模型，但 `data_model/models/` 当前仅 `lr_v1` / `rf_v1` / `xgb_v1` 三个 `.pkl` 进入交付段（`[models]` 段），其余 5 个（nb/dt/knn/mlp/mlp_deep）仅作评估用、不进交付链（`defect-records.md` N-01 已登记为「非缺陷」，由 R6 规定）。
- **补做**：在 `training-eval.md` §2 与 `model/README.md` §4 明确写「**本期交付模型 = lr/rf/xgb 三个；其余 5 个为评估对照，不进 `[models]` 段**」，消除「8 个都交付」的歧义。切换更优模型须另开「模型切换」提案。

### 4.2 公开数据集 vs 文献数字对照（可选目标）

- 若 PD-0 取到标准 benchmark（DeepJIT/CC2Vec 用过的 OpenStack、Qt），在其上训练并与**已发表结果**（AUC/F1）作量级对照，作为「本组管线在公开 benchmark 上可复现文献量级」的证据。
- **纪律**：获取不到标准 benchmark 则不强求；**不得为凑对照而选用非标准数据集**。属 `public-dataset-quality` 第 4 号任务的可选目标。

---

## 5. 如实标注纪律（一票否决红线）

1. 不声称全量 GPU 结果（无 GPU 则标 CPU/抽样）。
2. 不把自造 `P_norm` 包装成文献 `Popt`。
3. 不暗示复现 SOTA（本组是特征式混合形态）。
4. 不静默切换交付模型（切换走提案）。
5. 不虚构公开数据集（下载不到则降级并说明）。
6. 改需求只改码不改规格 = 缺陷；只勾 tasks ≠ 功能合格；复现性 ±0。

> 本文与 `openspec/changes/semantic-feature-mainline/`、`public-dataset-quality/` 互为补充：change 管「怎么改」，本文管「现在是什么 + 谁来做」。
