# 模型线方法依据与文献阅读记录（2026-10-13 建立）

> 起因：**2026-10-13 课堂反馈** —— 「模型训练不能全依赖 AI，需要自己阅读论文搞清楚怎么弄的」。
> 本文的目的**不是让 AI 代写综述**，而是把「我们为什么这么做」落到**可核验的文献出处 + 本组自己的判断**上，使结项答辩（占 50%）能逐条讲明白。
> 关联：`data_model/01~09_*.py` 各脚本 docstring 的「决策/判据」节、`docs/model/data-pipeline.md`、`openspec/specs/{feature-extraction,model-training,szz-labeling}/spec.md`、`data_model/reports/`。

## 0. 阅读责任（先立规矩）

| 方法域 | 必读文献 | 阅读责任人 | 状态 |
|---|---|---|---|
| SZZ 缺陷引入提交识别 | 本表 §2 的 A-1 / A-3 | 蒋励 | ⬜ 待读并签注 |
| 14 项变更度量（Kamei 14） | §2 的 B-1 | 蒋励 | ⬜ 待读并签注 |
| 信息熵（Entropy） | §2 的 B-2 | 蒋励 | ⬜ 待读并签注 |
| 时间序切分与 effort-aware 评估 | §2 的 B-3 / C-1 | 蒋励 | ⬜ 待读并签注 |

**签注要求**（答辩抽查用）：读完在 §4 表格填「篇目 / 阅读日期 / 原文页码 / 一句话结论 / 与本组实现的差异」。**只填「已读」不填页码，视为未读。**

## 1. 一句话结论（答辩可直接念）

> 本项目的模型线不是「调包」，而是**三条自研判断 + 两组对照实验**：
> ① 打标判据（缺陷编号 + 修复语义词首边界）是在固定版本上**实测外沿数字**后定下的，不是照抄论文；
> ② SZZ 实现了两套（标准行级 / 文件级简化）并**量化差异**，因为 PySZZ 工具在 PyPI 不可得；
> ③ 时间序切分是硬约束（禁随机），因为 EXP / NUC 等特征与时间强相关，随机切分等于让模型看到未来；
> ④ effort-aware 指标出现负值是**如实报告的问题**，并提出了重排方案。

## 2. 文献清单（出处 + 我们用了哪一条）

| 编号 | 文献 | 我们用到它的哪一条 | 置信度 |
|---|---|---|---|
| A-1 | Śliwerski, Zimmermann, Zeller, *When Do Changes Induce Fixes?*, MSR '05（SZZ 原始论文） | 缺陷引入提交 = 对修复提交中被删/改的行，在父提交上 `git blame`，blame 到谁就是谁。本组 `szz` 模式即按此实现 | ✅ 可引用 |
| A-3 | da Costa 等, *A Framework for Evaluating the Results of the SZZ Approach for Identifying Bug-Introducing Changes*, IEEE TSE（约 2017） | 「SZZ 结果需要用框架评估，而非默认正确」→ 本组因此**做了两套 SZZ 对照**，而不是只信一套 | ⚠️ 题目/年份待核对原文 |
| B-1 | Nagappan, Ball, Zeller, *Mining Metrics to Predict Component Failures*, ICSE '06 | 14 项变更度量（NS / ND / NF / Entropy / LA / LD / LT / FIX / NDEV / AGE / NUC / EXP / REXP / SEXP）的**原始出处**。仓库里通称「Kamei 14」，实际定义以本篇为准 | ✅ 可引用 |
| B-2 | Hassan, *Predicting Faults Using the Complexity of Code Changes*, ICSE '09 | Entropy = 两周滚动窗口内改动文件的信息熵（代码注释中记为「Kamei 引用 Hassan 的定义」） | ✅ 可引用 |
| B-3 | Kamei, Shihab, *Defect Prediction: Accomplishments and Future Directions*, PROMISE '16 | JIT 缺陷预测的问题 framing、effort-aware 评估的必要性、常见陷阱清单 | ✅ 可引用 |
| C-1 | Mende & Koschke, *Effort-aware Defect Prediction Models*, ICSM '10 | 「只看 AUC/F1 会被工作量代理带偏」→ 本组因此同时报 Effort-unaware 与 Effort-aware 两类指标，并发现 `P_norm` 为负 | ⚠️ 题目/年份待核对原文 |

> **待核对说明**：标 ⚠️ 的两条，其题目或年份需按原文 PDF / DOI 核对后再写入答辩材料；**不许凭印象引**。已核对的在 §4 签注。

## 3. 方法决策 ↔ 文献 ↔ 实现 ↔ 偏离（全部可在代码中核验）

| 决策 | 文献依据 | 我们的实现 | 与原文的偏离及理由（本组判断） |
|---|---|---|---|
| 修复提交判据 = 缺陷编号 `AMQ-<数字>` **且** 修复语义词出现在词首边界 | A-1 只定义「如何回溯」，**不定义「什么是修复提交」** | `data_model/02_szz_labeling.py` 的判据（D4）：两类同时命中；词首边界 `\b` | **原文未给判据，本组自定**。只用编号会把 54.7% 提交拉进候选池（含新功能与文档）；子串匹配会误收 `dispatch`/`debug`/`prefix` 词族 122 条（**实测无一条是真修复**）；严格词表又会漏 `fixe`/`fixinng` 这类拼写错误的真修复。取中间档并实测外沿数字 |
| 两套 SZZ 并行（`szz` 行级 + `szz_lite` 文件级） | A-3：SZZ 结果需被评估而非默认正确 | 同一固定版本各打一次标，`label_method` 区分，互不覆盖；差异量化出示 | **原文无「文件级简化版」**，`szz_lite` 是本组自研的取舍：粒度粗但快一个量级。**两套差异必须量化并出示**，不静默取其一 |
| `PySZZ` 工具不可用 → 自研标准行级 SZZ | A-1 的算法描述（不依赖具体工具） | `02_szz_labeling.py` 自研实现；契约一 1.2 版同步该口径 | 实测 `https://pypi.org/pypi/pyszz/json` 返回 **404**，其官方仓库依赖 gitlog 数据格式，属研究专用工具，Sprint 0 内跑通不现实 → 按 `docs/model/data-pipeline.md` 第 7 节兜底策略自研 |
| `rexp` 衰减口径 = `Σ count(n)/(n+1)`，`n` = 距本次提交的整年数 | B-1 原文口径（仓库契约第四节原只写「按时间衰减加权」） | `03_extract_features.py` 按上式实现，并在脚本内注明「契约未给公式，按 Kamei 原文口径」 | 原文给了公式、契约只给了中文描述 → **以原文补契约**，并在 `data-pipeline.md` 第 7 节登记该订正 |
| Entropy = 两周（14 天）滚动窗口 | B-2（Hassan 定义） | `03_extract_features.py` 窗口 14 天 | 与原文一致 |
| subsystem = 路径根目录名 | B-1 | `03_extract_features.py`：根目录下的文件单列一组 | 与原文一致 |
| 训练/检验**必须按 `committed_at` 时间序**切分（前 70% / 后 30%），禁随机 | B-3 / C-1：时间相关特征下随机切分会高估性能 | `05_split_dataset.py` 时间序切分；`openspec/config.yaml` 立为硬约束 | 与文献结论一致，且本项目特征集里 EXP / NUC 与时间强相关，风险更高 |
| 同时报 Effort-unaware 与 Effort-aware 两类指标 | C-1：effort-aware 才能反映评审员真实收益 | `06_train_model.py` / `08_model_matrix.py` 输出 AUC/F1/P/R/Acc + `P_norm`（按 `risk_score/工作量` 重排） | 与文献一致。**如实报告**：LOC 工作量代理下三个模型 `P_norm` 为负（-0.67 / -0.25 / -0.42，Issue #37），并给出同预算召回 +31.72 pp 的重排证据 |
| 高风险阈值 `p ≥ 0.50` | **无论文直接依据**，是本组按校准结果定的 | `09_calibration_threshold.py`；Issue #38 登记「`p≥0.50` 的提交真实缺陷率仅 29.6%」 | **这是本组的口径选择，不是文献结论**，答辩必须说明它已被登记为待契约变更提案，不得包装成论文结论 |

## 3.1 SZZ 打标的定位与已知局限（2026-10-13 补）

**定位**：SZZ 出自 2005 年（Śliwerski/Zimmermann/Zeller, MSR '05），**不是最新方法**，但：
- 课程把「SZZ 算法实现」列为**数据采集与仓库解析模块的必做项**，实现它符合要求；
- 打标层 20 年来**没有出现取代 SZZ 的主流方案**——DeepJIT / CC2Vec / LApredict / SimCom 等现代工作的数据集仍用 SZZ 类回溯标注；
- 课程所称「现在主流方法」（附加功能 (4)）指**特征与模型层**（预训练语义特征），**不是打标层**。

**已知局限（文献已讨论，须如实登记，详见 `docs/model/data-pipeline.md` §7.1）**：① 代理标注非 ground truth；② blame 追溯过远（假阳性主因）；③ 对代码移动/重构敏感；④ 「缺陷引入提交」定义不稳定（两套方法正样本比例差 11.16 pp）；⑤ D4 判据为自定启发式，数字不可横向比较。

**答辩口径**：SZZ 是课程必做模块，本组实现强于多数论文（两套并行且差异量化、判据实测外沿、回溯未命中不记 0）；同时按 da Costa et al.（IEEE TSE）的评估框架观点，**SZZ 结果需被评估而非默认正确**，故局限如实写入报告，不包装成高精度标注。

## 4. 阅读签注记录（责任人填写，答辩抽查）

| 篇目 | 阅读人 | 阅读日期 | 原文页码 | 一句话结论 | 与本组实现的差异 |
|---|---|---|---|---|---|
| A-1 | 蒋励 | 待填 | 待填 | 待填 | 待填 |
| A-3 | 蒋励 | 待填 | 待填 | 待填 | 待填 |
| B-1 | 蒋励 | 待填 | 待填 | 待填 | 待填 |
| B-2 | 蒋励 | 待填 | 待填 | 待填 | 待填 |
| B-3 | 蒋励 | 待填 | 待填 | 待填 | 待填 |
| C-1 | 蒋励 | 待填 | 待填 | 待填 | 待填 |

> 签注完成前，本表**任何一行都不得在答辩中声称「已读」**。

## 5. 方法依据的代码证据位置（不需读论文也能核验）

| 主题 | 位置 |
|---|---|
| 打标判据与外沿数字 | `data_model/02_szz_labeling.py` 模块 docstring「判据（D4）」「排除口径（D5）」；`docs/model/data-pipeline.md` 第 7 节 |
| 两套 SZZ 与 PySZZ 不可用 | `02_szz_labeling.py` 模块 docstring「两套方法（D3）」；第 512–513 行的报告输出 |
| `rexp` 与 Entropy 口径订正 | `03_extract_features.py` 第 28 / 45 / 91 / 294 / 304 行注释；同文件写出的订正表 |
| 时间序切分硬约束 | `05_split_dataset.py`；`openspec/config.yaml` 「必须遵守的约定」 |
| effort-aware 与负值报告 | `06_train_model.py` 第 28 / 36 / 199 / 582 行；`data_model/reports/calibration_threshold.md` |
| 阈值语义与 29.6% 真实缺陷率 | `09_calibration_threshold.py`；`repo/defect-records.md` D-06 |

## 6. 答辩讲法建议（30 秒版）

1. 「指标不是我选的，是文献里定义的 14 项，出处 Nagappan 2006，仓库通称 Kamei 14。」
2. 「SZZ 我读的是 Śliwerski 2005；工具 PySZZ 在 PyPI 404，所以我自己写了标准行级版本，并额外做了一个文件级简化版做对照，差异量化在报告里。」
3. 「打标判据文献没给，是我在固定版本上实测外沿数字后定的：只用编号会收进 54.7% 噪声，子串匹配会误收 122 条 dispatch/debug/prefix，我取词首边界。」
4. 「切分必须时间序，因为 EXP/NUC 与时间相关，随机切分会高估性能 —— 这是文献明确警告的。」
5. 「effort-aware 出现负值我没藏，Issue #37 登记了，并给了同预算召回 +31.72pp 的重排方案；`p≥0.50` 这个阈值是我的口径选择，已登记为待契约变更，不是论文结论。」
