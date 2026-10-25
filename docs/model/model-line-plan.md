# 模型线路方案（蒋励 · 数据与模型线）

> 版本 1.4（2026-10-14：主对象定为 **Apache Camel**；原 `training-eval.md` 并入本文）｜ 负责人 **蒋励** ｜ 审核 苏哲勋
> 关联 change：`semantic-feature-mainline`、`public-dataset-quality`、`feature-addons-sprint3`
> **本文 = 模型线唯一权威入口**（方案 + 模型与超参 + 评估口径 + 执行计划）。
> 数据从哪来、固定在哪个版本、怎么复现 → `data-pipeline.md`；14 项特征列名 → `feature-columns.md`（契约二）。

---

## 0. 一句话方案

> 聚焦单仓库 **Apache Camel**（`github.com/apache/camel.git`，tag `camel-4.23.0`；**2026-10-14 换库变更**，原 ActiveMQ 方案及其数据已废弃清理）；**Kamei 14 专家特征降为基线，CodeBERT / GraphCodeBERT 语义特征升为主线**；用**四类对比**（仅专家 / 仅语义 / 融合 / 端到端 fine-tune）在同一套模型、同一切分、同一指标下比出胜负；**不预设谁赢、不静默切换交付模型、不跨项目预测、不暗示复现 SOTA**。

---

## 1. 特征层（基线 + 主线）

| 层 | 内容 | 说明 |
|---|---|---|
| 基线 | **Kamei 14** 专家特征（14 维） | 课程必做；保留为对照组，契约二 14 项列名列序不动 |
| **主线** | **CodeBERT / GraphCodeBERT** 语义（768 维） | 课程点名的「现在主流方法」；**「主线」指课程方向，不等于效果占优**，由四类对比实验决定 |

---

## 2. 模型架构层（8 个输入模型 + 1 个端到端模型）

### 2.1 输入模型 8 个 —— 性能优先选型

课程硬要求「**至少 2 类（经典 ML + 神经网络）、不少于 8 种**」（`model-coverage` R1）。本组按**性能优先**选型（2026-10-14 决定），每个都是所在范式的强代表，且保留 `lr/rf/xgb` 与交付段（§6）一致：

| 类别 | 模型 | 范式 | 选型理由 |
|---|---|---|---|
| 经典机器学习（6） | `rf` 随机森林 | 袋装集成 | 同族稳健、抗过拟合 |
| | `xgb` XGBoost | 提升集成 | JIT 文献主流 |
| | `lgbm` LightGBM | 提升集成 | 现代提升，快 + 准 |
| | `et` Extra Trees | 极端随机树 | 分裂阈值随机、方差低 |
| | `svm` RBF-SVM | 核方法 | 非线性强基线（须特征标准化） |
| | `lr` 逻辑回归 | 线性 | 可解释基线 + **交付模型** |
| 神经网络（2） | `mlp_deep` 深层 MLP | 深度前馈 | 3 隐藏层 + 早停 |
| | `tabnet` TabNet | 深度表格 | 现代深度表格模型 |

- **被换下**：`nb` / `knn` / `dt` / `mlp`（单隐藏层）—— 范式覆盖有余而强度不足，让位给上表强模型。
- ⚠️ **换库前的实测排名数字已随 2026-10-14 换库一并清理，不得再引用**；新的实测排名在 Camel 重跑后登记于 `reports/model_matrix.md`。
- **`1D-CNN` 不在此列**：它吃 diff token 序列、属**端到端**架构，归到 §2.2 作对标。
- **保留 `lr/rf/xgb`**：与交付段（§6）一致，避免评估池与交付池冲突。
- 8 个共用同一时间序切分、同一特征口径（`model-coverage` R2）。
- **实现状态**：8 个均已在 `pipelines/expert/train.py`（原 `06_train_model.py`）落地；`lgbm` / `tabnet` 需 `lightgbm` / `pytorch-tabnet` 依赖。

### 2.2 端到端模型 1 个（第四类）

- **端到端 fine-tune CodeBERT / GraphCodeBERT**：**不冻结 backbone**，直接在 commit diff 文本上微调，特征提取与分类**联合优化**；输入只有变更文本，输出缺陷概率。
- 比「冻结语义 768 维 + 经典分类器」更强、最贴合课程说明；但约 2.3 万提交训 ~1.1 亿参数仍**偏紧**，需早停 / 小学习率防过拟合。
- 备选对标：DeepJIT / CC2Vec 式端到端（**`1D-CNN` 归此类**——它吃 diff token 序列，不吃特征向量）。
- 状态：⬜ 待立项（须走 openspec change + 更新 D10 如实标注形态）。

### 2.3 超参与口径登记表（2026-10-14）

> **纪律：口径统一 + 标准做法 + 不因算力折损。** 8 个模型共用同一份特征、同一切分、同一种子；每个模型用自己的**标准超参**（不为统一而简化）；任何偏离必须写明理由。本表是答辩被问「你到底怎么训的」时的标准答案。

| 模型 | 关键超参 | 停止方式 | 可逐字节复现 |
|---|---|---|---|
| `lr` | `max_iter=1000` | 凸优化，唯一解 | ✅ |
| `rf` | `n_estimators=300, min_samples_leaf=2` | 树建完即止 | ✅ |
| `xgb` | `n_estimators=300, lr=0.1, max_depth=6, subsample=0.9, colsample_bytree=0.9` | **固定 300 棵**（见口径 2） | ✅ |
| `lgbm` | `n_estimators=300, lr=0.1, num_leaves=31, subsample=0.9, subsample_freq=1, colsample_bytree=0.9` | **固定 300 棵** | ✅ |
| `et` | `n_estimators=300, min_samples_leaf=2` | 树建完即止 | ✅ |
| `svm` | RBF，`C=1.0, gamma="scale"`, `probability=True` | 凸二次规划，唯一解 | ✅ |
| `mlp_deep` | 3 层 (64/32/16)，`alpha=1e-4, max_iter=500, n_iter_no_change=15, validation_fraction=0.1` | **早停**（训练集内部验证子集） | ❌ |
| `tabnet` | `n_d=n_a=8, n_steps=3, gamma=1.3, max_epochs=100, patience=15, validation_fraction=0.1` | **早停**（训练集内部验证子集） | ❌ |

**三条必须能解释的口径**（「没做」与「为什么不做」都要答得出）：

1. **早停只用训练集内部验证子集**：`mlp_deep`（`MLPClassifier.early_stopping=True`）与 `tabnet`（`TabNetWithEarlyStop` 内部切 `validation_fraction` → 作为 `eval_set`）都从**训练集**里切验证子集；检验集按 `committed_at` 时间序切、始终更晚，**不参与早停决策**（红线第 1 条）。
   - ⚠️ **2026-10-14 订正**：pytorch-tabnet 的 `patience` **只在 `fit()` 收到 `eval_set` 时才生效**；此前直接放进 `Pipeline` 会导致早停**静默失效、实际跑满 `max_epochs`**。现改用包装器传入 `eval_set`，与 `mlp_deep` 同语义。
2. **`xgb` / `lgbm` 用固定 300 棵而非早停轮数**：为让 8 个模型在「**不依赖验证集**」上口径一致，并保证可逐字节复现；二者的学习率与正则已用于控过拟合。
   - ⚠️ **2026-10-14 订正**：LightGBM 行采样需 `subsample_freq > 0` 才生效，此前只写了 `subsample=0.9` 属**空转**，现已补 `subsample_freq=1`。
3. **`svm` 的 `probability=True`**：触发 libsvm 内部 5 折 Platt 校准，输出的是**校准后概率**、非 SVC 原生 `decision_function`。**保留它**是为了与其余 7 个模型共用同一套 `predict_proba` 口径——为「标准 SVC」而单独改用 `decision_function`，反而破坏模型间可比性。

**全部模型不设 `class_weight`**：统一不加类权重（正样本比例待 Camel 实测回填），避免只有个别模型加权而破坏可比性。

**可逐字节复现的两类划分**：`lr`/`rf`/`xgb`/`lgbm`/`et`/`svm` 属「同一命令连跑两次逐字节一致」类；`mlp_deep`/`tabnet` 因内部随机切验证子集 + 多线程浮点求和顺序，**不属于该类** —— 指标照常登记，**复现核对比对以固定迭代的模型为准**。

---

## 3. 对比设计：四类

| 类别 | 输入 | 分类由谁 | 冻结 backbone？ | 实例数 |
|---|---|---|---|---|
| 仅专家 | Kamei 14（14 维） | 8 个分类器 | — | 8 |
| 仅语义 | CodeBERT（768 维） | 8 个分类器 | 冻结 | 8 |
| 融合 | 14 + 768（782 维） | 8 个分类器 | 冻结 | 8 |
| **端到端** | 变更文本 | CodeBERT + 分类头 | **不冻结** | 1（+对标） |

- 前三类 = 两段式（8 × 3 = 24 实例），第四类 = 一段式（端到端）。
- 同一时间序切分、同一测试集、同一套指标 → 产出 `data_model/reports/three_way_comparison.md`（第四类另附）。
- **不预设谁赢**；小样本下 768 维语义易过拟合、Kamei 14 强归纳偏置可能更稳——正是对比要验证的假设（**维度高 ≠ 效果好、语义需更多标注数据**）。

> **四条线的分线细节**（用途 / 适用场景 / 核心步骤 / 输入输出 / 配置项 / 边界协作 / 红线）见 `pipelines/` 目录，**每线一篇自包含文档**：`expert-only.md`（仅专家，已跑通）/ `semantic-only.md`（仅语义，⬜）/ `fused.md`（融合，⬜）/ `end-to-end.md`（端到端，⬜ 待立项）。每篇自带产物命名纪律（报告名带线名，四线同名即互相覆盖）；四类共有的模型、切分与指标仍以本文件为唯一权威。

---

## 4. 评估与验收口径

### 4.1 切分铁规矩

- **按 `committed_at` 时间序切分，前 70% 训练 / 后 30% 测试，禁止随机切分**（EXP/NUC 等时间相关特征，随机 = 提前看未来，准确率是假的）。
- 写进 `AGENTS.md` 硬红线；`train_test_split(shuffle=True)` 或未指定 `shuffle=False` = 缺陷，必须打回。
- 切分后**不重新切分、不改特征**；覆盖矩阵只读切分文件。

### 4.2 两类指标（都要报）

| 类型 | 指标 | 状态 |
|---|---|---|
| Effort-unaware | AUC / F1 / Precision / Recall / Accuracy | ✅ 已实现 |
| Effort-aware（已实现） | `P_norm`、Recall@20% / @50%、曲线下面积、随机基线（200 次抽样均值 ± 标准差）、上界（真实缺陷密度降序）、四种排序（model / density / optimal / random）、两种工作量代理（LOC 与改动文件数） | ✅ 已实现 |
| Effort-aware（文献标准） | `CE@20%` / `Recall@20%` / `Popt` | ✅ 已实现（代码别名 `ce20` / `popt`，见 `pipelines/expert/metrics.py`） |
| Effort-aware（文献标准） | `ALPA` | ⬜ **待补**：多轮检索未获可核验的原始定义出处 → **不实现、不编造**；待拿到原始论文（JIT effort-aware 方向）后再补 |

**文献口径对照（2026-10-16 核实并回填）**：

- **`Popt`**：Mende & Koschke（**CSMR 2010**, pp. 107–116）提出，定义为 `Popt = 1 − Δopt`——Δopt 为「最优排序（按缺陷**密度**降序）与模型排序」之间的面积差，并按「最优 − 随机」归一（定义转述见 Çarka, Esposito & Falessi, *On effort-aware metrics for defect prediction*, EMSE 27(152), 2022）。本组 `P_norm = (A_model − A_random)/(A_optimal − A_random)` **与之一致**，故代码同时输出 `popt` 别名。**待复核项**：原始论文的积分表达形式（本组按综述转述，未逐字核对原文公式）。
- **`CE@20%` / `Recall@20%`**：20% 工作量截断处的缺陷召回率（20-80 原则；见 Huang, Xia & Lo, *Revisiting supervised and unsupervised models for effort-aware JIT defect prediction*, EMSE 24(5), 2019）。本组 `recall@20` 即该口径，代码输出 `ce20` 别名。
- **`ALPA`**：**未实现**（未获可核验定义），登记待补。**不得**用 `Popt` 或其它数字冒名顶替（红线 2）。
- ⚠️ 对外表述统一用文献名（`Popt` / `CE@20%`）；`P_norm` 仅作内部历史别名保留，**不再声称「自造变体、与 Popt 不同」**（该说法经核实不成立）——但**原始论文公式仍待逐字复核**，在复核完成前引用时必须带本注。
- 只报一类不足以说明问题；覆盖矩阵报告须与 `model_metrics.md` 逐项比对**差异为 0**。
- **统计检验**：Bootstrap（≥1000）+ Wilcoxon signed-rank（+ McNemar）；8 模型在同一测试集上配对比较。
- **显式基线**：随机排序、上界、两种工作量代理（LOC 与改动文件数）。
- ⚠️ **判读纪律**：AUC 差 < 0.01 的模型对，结论只能是「**在当前检验集上无法区分**」，不得排序；**不得用 p 值宣称模型优劣**（大样本下 p 极易极小），正确答法是引 CI 重叠情况。

### 4.3 覆盖矩阵（⑧）

`pipelines/expert/matrix.py` 产出 `pipelines/expert/reports/model_matrix.md`：8 种 × 2 类 × 两类指标，与 `model_metrics.md` 逐项比对**差异 0 项**。

> ⬜ **待重跑**：矩阵数字必须在 Apache Camel 数据上重训后重新登记。**本包不保留 ActiveMQ 阶段的指标数字**（已随换库清理）。收敛情况（神经网络迭代轮次 / 未收敛）须**如实登记，不许静默当已收敛**。

### 4.4 校准与阈值证据（⑨）

- `pipelines/expert/calibrate.py`：时间序折（`TimeSeriesSplit`，禁随机 `KFold`）校准；固定阈值 vs 工作量配额（LOC 与改动文件数各一版）的等工作量对照。
- ⑨ 只出证据、**不改契约**；两种策略对照必须同工作量口径。
- ⬜ **实测结论待回填**：阈值 vs 工作量的对照必须在 Apache Camel 数据上重跑后登记（旧仓库实测已随 2026-10-14 换库清理）；历史结论「阈值校准到 50% 语义在时间序切分下走不通、建议转向配额取前 N%」需在新数据上复核后保留或修订。

### 4.5 验收双轨（复现一致性 + 契约一致性）

- **复现一致性（模型线主验收）**：别人照 `data-pipeline.md` §5 复现命令跑出同一份统计（±0）、指标报告逐行一致、两类指标齐全。**可逐字节比对的范围见 §2.3**（`mlp_deep` / `tabnet` 除外）。
- **契约一致性（单测）**：模型线的单测不在本包重造，按职责落两处 ——
  - 特征口径（14 项列名与顺序）→ `data_model/tests/test_feature_contract.py`（把契约文档 / 实现 `FEATURE_FIELDS` / 后端装配 `FEATURE_COLUMNS` / 交付清单 `feature_order.txt` **四处钉在同一份有序清单**上）；
  - 模型加载与解释（`joblib.load`、特征数自检、SHAP 键名可回溯）→ `backend/tests/test_model_registry.py`。
- 测试总纲与退出准则见 `common/test-plan.md`。

---

## 5. 单仓库约束

- **主对象**：**Apache Camel**（`https://github.com/apache/camel.git`，tag `camel-4.23.0` / commit `b2329103df8f5d1edfca2ad262be09e3be95ee68`，JIRA `CAMEL-xxxx`）——**2026-10-14 换库变更**（原因：ActiveMQ 为自建非标准 benchmark、时间漂移明显）。
- **原 ActiveMQ 方案已废弃**：其仓库副本、中间数据、模型与全部评估报告已于 2026-10-14 一并清理（仅存于 git 历史），**不再作为对照基线**；本方案所有统计均以 Camel 重跑结果为准。
- **为什么单仓库**：Kamei et al. 2013（IEEE TSE 39(6):757–773）——JIT 预测**项目内可用、跨项目不可迁移**。管线插件化可扩展，但模型须逐仓库重训。
- **SZZ 局限已登记**（代理标注 / blame 过远 / 对重构敏感 / 双口径差 / D4 为自定启发式）：五条写入 `data-pipeline.md` §7.1，如实报告不包装。

> 2026-10-15 数据源订正：上条 Camel 的实测数字来自上游提交 `866b7dc` 的全量报告 —— 固定版本非合并提交 **84,461**，`szz` 正例 **22.23%** / `szz_lite` 正例 **14.38%**（两套差 **7.85 个百分点**）。本次只对齐口径，**未重新运行全量采集 / SZZ / 训练**。

### 5.1 常见质疑与答辩口径（必背）

| 质疑 | 我们的选择 | 依据 |
|---|---|---|
| 仓库范围 | 「测任何仓库」「多仓库」 | **单仓库 Apache Camel**，管线插件化可扩展 | Kamei 2013（IEEE TSE 39(6):757–773）：跨项目不可迁移 |
| 特征 | Kamei 14 是唯一主线；语义特征「可选附加、Sprint 3 才做」 | **CodeBERT 语义特征为主线**；Kamei 14 降基线 | 课程附加功能 (4)：现在主流是预训练语义特征；童老师「不能采用老旧方案」 |
| 语义模型 | MiniLM 打底全量 | **CodeBERT/GraphCodeBERT 主路线**；MiniLM 仅弱基线/可砍 | 代码专用预训练 vs 通用句向量域不匹配 |
| 评估 | 只报自造 `P_norm` | **标准 effort-aware（CE@20%/Recall@20%/Popt/ALPA）+ Wilcoxon**；`P_norm` 标注自造 | 文献 effort-aware 标准口径 |
| 交付 | 语义更优就静默替换 | **不静默切换**，须另开模型切换提案 | `model-coverage` R6 硬约束 |
| 形态 | 暗示端到端 SOTA | **特征式混合**，如实说明非端到端 | D10 答辩纪律 |

---

## 6. 交付边界

- **本期交付模型 = 8 个全部在线**（2026-10-25 组长裁定，Issue #139 / change `online-eight-model-selection`）：`lr_v1` / `rf_v1` / `xgb_v1` / `lgbm_v1` / `et_v1` / `svm_v1` / `mlp_deep_v1` / `tabnet_v1` 全部进后端 `[models]` 段、可在线切换；实测 8/8 加载（9.8s）、推理全部 <130ms、归因 5 非空 / 3 设计内降级为空，证据见 `backend/scripts/evidence/online-eight-model-selection-2026-10-25.md`。
- **不静默切换**：R6 的「不静默加模型」规矩不变——后续新增仍须另开 change 走契约三变更流程（本次是显式裁定，不是开口子）。
- **模型文件不入库**：`data_model/pipelines/expert/models/*.pkl` 被 `.gitignore` 排除，走打包交付；随包交付 `models/feature_order.txt`（**契约二第三节的副本**，不一致时以契约为准）。
- **后端加载**：统一 `joblib.load`（`lr_v1`/`rf_v1` 是 joblib 格式、`xgb_v1` 是标准 pickle；`svm_v1`/`mlp_deep_v1`/`tabnet_v1` 是 Pipeline，加载环境须有对应依赖）；`model_name` 与 `prediction.model_name` 及接口入参同名。

---

## 7. 缺陷归因 / 解释（SHAP）

> 课程模块：预测与解释模块（缺陷概率 + 归因/解释）。契约三冻结 `explanation` 算法 = SHAP。

- **为什么 SHAP**：契约三要求 `explanation` 逐特征且带 `direction`（推高/降低），SHAP 天然满足；全局特征重要性无方向、非逐样本，满足不了。树族用 `TreeExplainer`（`xgb` / `rf` / `lgbm` / `et`）、线性 Pipeline 解包后用 `LinearExplainer`（`lr`）；`svm_v1` / `mlp_deep_v1` / `tabnet_v1` 无高效精确解释器（KernelSHAP 单次 1–3s 会打穿 500ms 靶子），按 #139 裁定**设计内降级为空数组**、前端渲染「无归因」——这是登记在契约三 §4 的预期行为，不是缺陷。
- **接口结构**（与 `GET /api/commits/{hash}`、`POST /api/predict` **同一套，两处不许各写一份**）：

```json
"explanation": [
  { "feature": "entropy", "contribution": 0.21, "direction": "increase" },
  { "feature": "nuc",    "contribution": 0.14, "direction": "increase" },
  { "feature": "exp",    "contribution": 0.09, "direction": "decrease" }
]
```

- **展示约定**：`increase` 右、`decrease` 左；按 `|contribution|` 降序，页面只显前 8，多出折叠。
- **键名归属**：`feature` 字段名必须与 `feature-columns.md` 一致，否则解释条取不到值、静默空白。
- **验收**：实时推理与查询接口都产出 `explanation[]` 且带 direction；前端解释条与字段对应正确（联调核对）。
- **SHAP 单条耗时须实测**（`--shap-rows`），不达标不静默降级，只如实记录。

---

## 8. 执行计划

> 状态：🔄 进行中 / ✅ 已完成 / ⬜ 未开始 / 🔶 阻塞前置。

### 8.1 完成定义（DoD：模型线真正做完的硬标准）

1. 语义特征按 `feature_version=v2` 落盘（或明确降级为抽样并写明原因）。
2. 三类设置（仅专家 / 仅语义 / 融合）在**同一时间序切分、同一 8 模型、同一套指标**下产出 `three_way_comparison.md`。
3. Effort-unaware + 标准 Effort-aware（CE@20%/Recall@20%/Popt/ALPA）两类齐全；`P_norm` 已标注自造变体。
4. 显著性检验完成（Bootstrap ≥1000 + Wilcoxon + McNemar）→ `statistical_test.md`。
5. 专家特征消融（留一法 + 置换重要性）+ 多切分稳健性（70/30 + 60/40 + 80/20）。
6. 未静默切换交付模型；文档口径同步；复现命令跑出同一份统计（±0）。

### 8.2 阶段总览（关键路径）

| Phase | 名称 | 依赖 | 关键交付 | 状态 |
|---|---|---|---|---|
| **P0** | 环境与基线冻结 | — | 单环境 + torch 栈 + 测试绿 | ✅ |
| **P1** | 变更文本 → CodeBERT 语义落盘 | P0 | `semantic_text_v2.csv` / `semantic_codebert_v2.csv` | ⬜ |
| **P2** | 评测协议对齐（EV） | P0（可并行 P1） | 标准 effort-aware + 显著性 + `P_norm` 标注 | ⬜ |
| **P3** | 融合样本构建（三类设置） | P1 | 三套样本集 + 同切分下标 | ⬜ |
| **P4** | 三类对比实验（**核心交付**） | P2 + P3 | `three_way_comparison.md` | ⬜ |
| **P5** | 消融 + 多切分稳健性 | P4 | `feature_ablation.md` + 稳健性表 | ⬜ |
| **P6** | 公开数据集治理（PD，独立支线） | P0 | 按 PD-0 结论推进 | ⬜ |
| **P7** | 交付边界 + 文档同步 + 验收收口 | P4–P6 | DoD 全绿 | ⬜ |

- 关键路径：`P0 → P1 → P3 → P4 → P5 → P7`；P2 与 P1 并行但须早于 P4；P6 全程并行、不阻塞主线。
- **前置**：P1–P5 全部依赖 Camel 数据链路（`data-pipeline.md` §5）先跑通。

### 8.3 阶段要点

- **P0** ✅：单环境（torch 2.14.1 / transformers 5.19.0 等）+ 测试绿；CodeBERT 权重已预下载并离线验证（hidden=768）。
- **P1**：`10_semantic_text.py`（按文件构造变更文本）→ 先跑 100 条基准（SF-2）定时限 → `11_semantic_codebert.py` 落 v2 向量。CPU 超预期则按时间序分层抽样并如实登记。
- **P2**：补 CE@20%/Recall@20%/Popt/ALPA；`pipelines/expert/significance.py`（Bootstrap + Wilcoxon + McNemar）；复核测试集未参与调参。
- **P3**：`13_build_fused.py` 左连接专家 14 项与语义向量 → 三套样本集，**必须同一切分下标**，缺失向量显式标注不填 0。
- **P4**：`14_compare_settings.py` 三类 × 8 模型 × 两类指标 → `three_way_comparison.md`；语义不占优如实报告。
- **P5**：`15_feature_ablation.py`（留一法 + 置换重要性）+ 三切分点稳健性，翻转如实报告。
- **P6**：PD-0 可下载性验证（阻塞前置）→ PD-1~4；取不到则降级为「加载器框架 + Camel 自验」并写明原因。
- **P7**：确认交付段未改；形态如实标注（特征式混合 / 端到端）；DoD 全绿收口。

### 8.4 里程碑 Gate（卡口）

| Gate | 触发点 | 放行条件 | 不放行 |
|---|---|---|---|
| G0 | P0 出口 | torch 栈 import 通过 + 测试绿 | ✅ 已放行 |
| G1 | P1 出口 | 100 条基准计时报告 + 语义 CSV 落盘 | 未计时就跑全量 = 缺陷 |
| G2 | P2 出口 | 标准 effort-aware + 显著性脚本可跑 | **P4 不得开始** |
| G3 | P3 出口 | 三套样本集 + 同切分下标断言通过 | 下标不一致打回重切 |
| G4 | P4 出口 | `three_way_comparison.md` 产出且 8 模型齐全 | 缺模型即打回 |
| G5 | P5 出口 | 消融报告 + 三切分稳健性表 | 缺翻转说明不放行 |
| G6 | P7 出口 | DoD 全绿 + 未静默切换模型 | 模型线未完成 |

### 8.5 任务主清单（责任人：蒋励）

| 组 | 任务 | 状态 |
|---|---|---|
| SF-0 | Camel 数据链路跑通（①–⑨） | ⬜ |
| SF-2 | 100 条基准计时（CPU 50–150ms/条） | ⬜ |
| SF-3 | 变更文本构造（路径 + 类型 + 增删行 + 提交首行，截断记统计） | ⬜ |
| SF-4 | 语义向量落盘 `feature_version=v2` | ⬜ |
| SF-5 | 三类对比（同切分同 8 模型） | ⬜ |
| SF-6 | Kamei 14 消融 + 置换重要性 | ⬜ |
| SF-7 | 多切分稳健性（60/40、80/20） | ⬜ |
| PD-0 | 公开数据集可下载性验证（阻塞前置） | 🔶 |
| PD-1~4 | 加载器 / 质量治理 / 多语言 / 文献对照 | ⬜ |
| EV-1 | 补标准 effort-aware 指标 | 🔶 `CE@20%`/`Recall@20%`/`Popt` 已实现（别名 `ce20`/`popt`）；`ALPA` 未获可核验定义，登记待补 |
| EV-2 | Wilcoxon + McNemar 显著性检验 | ⬜ |
| EV-3 | `P_norm` 标注自造 | ✅ |

### 8.6 关键复现命令（语义线 ⑩–⑯）

```bash
conda activate jit-defect-prediction
cd data_model
python 10_semantic_text.py            # 构造变更文本
python 11_semantic_codebert.py        # 先 100 条基准，再决定全量/抽样
python 13_build_fused.py              # 三套样本集
python 14_compare_settings.py         # 三类对比
python 15_feature_ablation.py         # 消融
python -m pipelines.expert.significance   # 显著性
```

> 数据线 ①–⑨ 的复现命令见 `data-pipeline.md` §5（两段命令互补，不重复）。

### 8.7 风险与降级（红线）

| 风险 | 降级路径 | 红线 |
|---|---|---|
| CPU 跑不动全量（Camel ~2.3 万条） | 100 条基准 → 时间序分层抽样 + 如实登记 | 不得谎报全量 |
| CodeBERT 权重下载失败 | HF 代理/镜像；失败改 `HF_ENDPOINT=https://hf-mirror.com` | 不得伪造语义结果 |
| 公开数据集取不到 | PD-0 结论 → 加载器框架 + Camel 自验 + 写明原因 | 不得虚构数据 |
| 语义不如专家特征 | 如实报告三类对比结论 | 「不占优」不是失败 |
| 想换更优模型上线 | 另开「模型切换」提案（R6） | 不得静默切换 |
| 某模型未收敛 | 指标照常登记 + 收敛登记表写出 | 不得静默当已收敛 |

---

## 9. 纪律红线（一票否决）

1. 不声称全量 GPU 结果（无 GPU 则标 CPU / 抽样）。
2. 不把「未获可核验定义」的指标（当前为 `ALPA`）用别的数字冒名顶替；引用 `Popt` / `CE@20%` 时按 §4.2 注明的口径与待复核项如实标注。
3. 不暗示复现 SOTA（本组为特征式混合 + 端到端探索）。
4. 不静默切换交付模型（切换走提案）。
5. 不虚构公开数据集（下载不到则降级并说明）。
6. 只勾 tasks ≠ 功能合格；改需求只改码不改规格 = 缺陷。
7. 不引用已随换库清理的旧仓库实测数字。

> 补充：方法依据与文献阅读（6 篇文献 + 决策表 + 答辩讲法）见 `README.md` §9；协作纪律（组长不包揽、openspec 把关不代改）见 `common/openspec-task-template.md` §6；数据链路与 SZZ 局限见 `data-pipeline.md`。
