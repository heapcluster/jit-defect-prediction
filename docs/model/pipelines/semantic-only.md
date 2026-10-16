# 仅语义 · Pipeline 说明

> 版本 1.1 ｜ 更新 2026-10-14 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> **一句话**：用**冻结的 CodeBERT / GraphCodeBERT** 把每次提交的变更文本编码为 768 维语义向量，喂给与基线相同的 8 个分类器，检验「预训练语义特征优于专家度量」这一课程主线假设。
> 状态：**⬜ 计划态** —— 脚本（`10` / `11` / `13` / `14`）尚未落地，本文是开工口径，不是已完成工作。
> 本文自包含：照本文即可实现与复查，不需要再翻别的文档。

## 1. 用途

1. **验证课程主线假设**：课程《项目要求》指出现主流方法是「用预训练模型从源代码提取深层语义特征再建预测模型」。本线把 CodeBERT 768 维语义作为唯一输入，与仅专家基线在同一切分、同一模型池、同一指标下比出胜负。
2. **为融合线提供右表**：融合（782 维）= 本线 768 维 + 专家 14 维，本线的向量落盘是融合线的前置。
3. **沉淀语义特征的构造与落盘口径**：变更文本怎么构造、向量怎么聚合、截断怎么登记，一次性定死并复用到端到端线。

**「主线」指课程方向，不等于效果占优**：小样本下 768 维易过拟合、Kamei 14 强归纳偏置可能更稳 —— 这正是对比要验证的假设。语义不占优要**如实报告**，「不占优」不是失败。

## 2. 适用场景

| 场景 | 走本线？ |
|---|---|
| 检验语义特征单独使用是否优于专家基线 | ✅ 本线 |
| 为融合线准备 768 维向量 | ✅ 本线是融合线的上游 |
| 需要一条能上线交付的模型 | ❌ 语义向量 `feature_version=v2`，**不入库、不进交付链** |
| 算力不足以在 CPU 上跑全量 | ⚠️ 先跑 100 条基准定时限，再按时间序分层抽样并**如实登记**，不得谎报全量 |
| 端到端联合优化 | ❌ 走 `end-to-end.md`（那条不冻结 backbone） |

## 3. 核心处理步骤

| 步 | 动作 | 脚本（计划命令） | 输出 | 关键校验 |
|---|---|---|---|---|
| ⑩ | 构造变更文本：**一次提交内每个改动文件生成一条文本** | `10_semantic_text.py` | `pipelines/semantic/data/semantic_text_v2.csv` | 文本内容 = 文件路径 + 变更类型 + 增删行（去行首符号）+ 提交信息首行；超长**按行截断并记录被截断的文件数与行数** |
| ⑪ | 100 条基准计时（**Gate G1 放行条件**） | `11_semantic_codebert.py --limit 100` | 计时报告（写入 `pipelines/semantic/reports/`） | 未计时就跑全量 = 缺陷；CPU 单条约 50–150ms，据此决定全量 / 分层抽样 |
| ⑪' | 全量（或抽样）语义向量落盘 | `11_semantic_codebert.py` | `pipelines/semantic/data/semantic_codebert_v2.csv` | 一行一个 `commit_hash`，列 `sem_0 … sem_767`；`feature_version = v2` |
| ⑬ | 生成本线样本集（与专家线**同切分下标**） | `13_build_fused.py --line semantic` | `pipelines/semantic/data/dataset_semantic_v2.csv` | 切分下标与 `data_model/data/split_szz_*.csv` 逐条一致；缺失向量显式标注、**不填 0** |
| ⑭ | 训练 8 模型 + 两类指标 + 三线对比 | `14_compare_settings.py --line semantic` | 本线：`pipelines/semantic/reports/model_metrics_semantic.md`、`model_matrix_semantic.md`；跨线：`data_model/reports/three_way_comparison.md` | 8 模型齐全；与专家线同一切分、同一套指标 |

**环境**：`conda activate jit-defect-prediction`（torch 2.14.1 / transformers 5.19.0，CodeBERT 权重已预下载并离线验证，`hidden=768`）。语义线单测也跑在该环境，不给 `jit-defect` 加包。

**切分与指标全部复用基线口径**：切分沿用 `05_split_dataset.py` 的时间序切分（前 70% / 后 30%，禁随机）与 `validate_split` 断言；指标沿用 `06` / `08` 的两类指标（Effort-unaware：AUC / F1 / Precision / Recall / Accuracy；effort-aware：`P_norm`、Recall@20% / @50%、曲线下面积、随机基线与上界、LOC 与改动文件数两种工作量代理）。**不新造模型类**，8 模型框架直接复用 `model_registry` 插件化机制。

## 4. 输入

| 输入 | 来源 | 形态 |
|---|---|---|
| Apache Camel 仓库副本 | 仅专家线步骤①产出（`data_model/data/camel/`） | Git 仓库，固定 tag `camel-4.23.0` |
| 提交清单 | 仅专家线 `data_model/data/commits.csv` | 一行一次提交 |
| 缺陷标签 | 仅专家线 `data_model/data/commit_labels_szz.csv` | `is_bug_inducing` 标签 |
| 切分下标 | 仅专家线 `data_model/data/split_szz_{train,test}.csv` | **只读复用，本线不重新切分** |
| 预训练权重 | HuggingFace `codebert-base` / `graphcodebert-base` | 已离线预下载 |

## 5. 输出

**目录约定（2026-10-14 起，四线隔离）**：本线产物**全部落在 `data_model/pipelines/semantic/`** 下
（`data/` 中间结果、`models/` 模型文件、`reports/` 本线报告）；四线共享的上游产物仍在
`data_model/data/`；**跨线汇总报告**（三线对比、显著性）由共享脚本产出到 `data_model/reports/`。

| 产物 | 路径 | 入库？ | 去向 |
|---|---|---|---|
| 变更文本 | `pipelines/semantic/data/semantic_text_v2.csv` | ❌ | 端到端线复用同一份文本 |
| 语义向量 | `pipelines/semantic/data/semantic_codebert_v2.csv`（`sem_0…sem_767`） | ❌（v2 不入库） | **融合线的右表** |
| 样本集 | `pipelines/semantic/data/dataset_semantic_v2.csv` | ❌ | 本线训练用 |
| 模型文件 | `pipelines/semantic/models/{model}_semantic_v1.pkl` | ❌ | 仅评估，**不进交付链** |
| 指标报告 | `pipelines/semantic/reports/model_metrics_semantic.md` | ✅ | 证据 |
| 覆盖矩阵 | `pipelines/semantic/reports/model_matrix_semantic.md` | ✅ | 证据 |
| 消融 | `pipelines/semantic/reports/feature_ablation_semantic.md` | ✅ | 证据 |
| 三线对比汇总 | `data_model/reports/three_way_comparison.md`（历史沿用名，跨线共享） | ✅ | 与专家/融合共一份 |

**命名纪律**：本线一切报告名带 `_semantic` 后缀，**不许落到仅专家线的旧名上**（`reports/model_metrics.md` 等名字归专家线，四线同名即互相覆盖）。

## 6. 关键配置项及其作用

| 项 | 取值 / 计划参数 | 作用 |
|---|---|---|
| 编码模型 | `codebert-base`（主）；`graphcodebert-base`（可选对照） | 课程点名的代码专用预训练模型；`all-MiniLM-L6-v2` 域不匹配，仅作「非代码预训练」对照或直接砍掉 |
| 输入单元 | **按改动文件**一条文本（非整提交一条） | 缺陷引入常定位到文件；整提交拼一条会被模型截断，语义退化成噪声 |
| 文本字段 | 文件路径 + 变更类型（add/modify/delete）+ 增删行（去行首符号）+ 提交信息首行 | 路径与类型携带结构与意图信号；只留首行避免提交信息噪声淹没代码信号 |
| 跨文件聚合 | 同一提交多文件向量取**均值** | 得到提交级 768 维向量 |
| 截断 | 超模型上限按行截断，**记录被截断文件数与行数** | 不静默丢数据；截断统计必须进报告 |
| `feature_version` | `v2` | 与 v1（专家 14 项）区分；契约二既有 14 项列名与顺序**一字不动**，语义列只作附加列或独立文件 |
| 向量列名 | `sem_0 … sem_{d-1}` | 落盘格式（D4 决策） |
| 基准条数 | `--limit 100` | Gate G1：先计时再决定全量/抽样 |
| 设备与样本量 | CPU / GPU、全量 / 抽样比例 | 报告必须标注，**不声称全量 GPU 结果** |
| 缺失向量 | 显式标注，**不填 0** | 填 0 会被当成「语义全零」的真实信号，静默污染对比结论 |
| 模型池 / 指标 | 与仅专家线完全相同（8 模型 + 两类指标） | 三线可比的前提；任何一组换口径即不可比 |

## 7. 与其他 pipeline 的边界与协作关系

| 对象 | 关系 | 具体内容 |
|---|---|---|
| 仅专家 `expert-only.md` | **上游依赖** | 取仓库副本、提交清单、标签与切分下标；本线**不改**专家线任何产物，14 项列名与顺序不动 |
| 融合 `fused.md` | **上游 → 下游** | 本线 `data/semantic_codebert_v2.csv` 是融合线的右表；`13_build_fused.py` 一次连接、两线复用 |
| 端到端 `end-to-end.md` | **并列对照** | 两者都用 CodeBERT，但本线**冻结 backbone**（两段式：提特征 → 经典分类器），端到端**不冻结**（一段式联合优化）；本线的变更文本产物可被端到端复用 |
| 后端线 | **无直接交付** | v2 不入库、不进交付链；若对比显示语义更优，切换交付模型须另开提案走契约三变更流程 |

**边界要点**：本线与仅专家/融合三线共用「同一切分下标、同一 8 模型、同一套指标、同一显著性检验方法」；与端到端线**形态不同**，结论分开报，不并进同一张对比表。

## 8. 红线

1. **语义向量不入库、不进交付链**：只落 `data_model/data/semantic_*.csv`，不作为 `commit_feature` 表新列。
2. **契约二 14 项一字不动**；口径变更走契约变更流程并升 `feature_version`。
3. **不得伪造语义结果**；权重下载失败改 `HF_ENDPOINT=https://hf-mirror.com`，失败如实登记。
4. **不得谎报全量**：CPU 跑不动就按时间序分层抽样 + 如实登记样本量与设备。
5. **切分下标必须与专家线一致**；本线重新切分 = 打回重切。
6. `P_norm` 须标注「本组自造变体，非文献 `Popt`」；不得暗示复现 SOTA（本组为特征式混合形态）。

## 9. 变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-14 | 1.1 | 重写为独立自包含的 pipeline 说明：补用途/适用场景/五步流程（⑩→⑪→⑬→⑭）/输入输出/配置项（含 D3 文本构造、D4 落盘格式）/边界协作/红线；状态明确为 ⬜ 计划态 |
| 2026-10-14 | 1.0 | 从 `model-line-plan.md` §1/§3/§8 拆出仅语义线独有内容 |
