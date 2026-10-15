# 仅专家（基线）· Pipeline 说明

> 版本 1.1 ｜ 更新 2026-10-14 ｜ 主笔 蒋励 ｜ 审核 苏哲勋
> **一句话**：从 Apache Camel 固定版本出发，用 Kamei 14 专家特征训练 8 个分类器，产出课程必做的**基线结果**；同时它是四条 pipeline 中**唯一进入在线交付链**的一条，向后端交模型文件与全量预测结果。
> 本文自包含：用途、步骤、输入输出、配置项、边界全部写在本文，照本文即可开工与复查。

## 1. 用途

1. **跑通「原始仓库 → 可交付模型」的完整参照链路**（九步），为其余三条 pipeline 提供数据上游：提交清单、缺陷标签、14 维特征表、样本集与切分下标都由本线产出，被仅语义 / 融合 / 端到端三条线复用。
2. **产出课程必做的基线组结果**：Kamei 14 + 8 模型 + 两类指标，作为与语义主线对照的基准。
3. **产出在线交付物**：`lr` / `rf` / `xgb` 三个模型文件 + 全量预测结果文件，是后端接口能加载、前端三页面能展示的唯一来源。

## 2. 适用场景

| 场景 | 走本线？ |
|---|---|
| 从零复现整条链路 / 重建数据上游 | ✅ 唯一入口 |
| 需要「专家特征 vs 语义特征」的对照组数字 | ✅ 本线即对照组 |
| 给后端交付可加载的模型与全量预测结果 | ✅ 只有本线能进交付链 |
| 检验预训练语义特征是否更优 | ❌ 走 `semantic-only.md` |
| 检验「专家 + 语义」混合是否更优 | ❌ 走 `fused.md` |
| 端到端联合优化（不冻结 backbone） | ❌ 走 `end-to-end.md` |

## 3. 核心处理步骤（九步，顺序固定）

数据源与版本固定：**Apache Camel**（`https://github.com/apache/camel.git`），tag `camel-4.23.0` / commit `b2329103df8f5d1edfca2ad262be09e3be95ee68`，JIRA 前缀 `CAMEL-`。克隆后 `git rev-parse HEAD` 必须与该 commit 一致（版本浮动 `main` = 一票否决）。Camel 早期历史为 SVN 转换，**有效样本偏 2010 年后**。

| 步 | 动作 | 脚本 / 命令 | 输出 | 关键校验 |
|---|---|---|---|---|
| ① | 克隆固定版本 | 手工：`git clone` + `git checkout camel-4.23.0` | `data_model/data/camel/`（四线共享） | `git rev-parse HEAD` 等于固定 commit |
| ② | 抽取提交（GitPython，过滤合并提交） | `01_extract_commits.py` | `data_model/data/commits.csv` + 统计 | 84,461 条；上游统计见 `docs/model/data-pipeline.md` §2、§6 |
| ③ | SZZ 打标（两套：标准行级 + 文件级简化版） | `02_szz_labeling.py --method both` | `data_model/data/commit_labels_szz.csv`、`commit_labels_szz_lite.csv` | 修复判据 `CAMEL-\d+` 且词首边界；两套结果都要出 |
| ④ | 计算 Kamei 14 项特征 | `03_extract_features.py` | `data_model/data/commit_features.csv`（`feature_version = v1`） | 列名与口径以契约二为准（见 §6.3） |
| ⑤ | 汇总为可训练样本集 | `04_build_dataset.py --labels data/commit_labels_szz.csv --labels data/commit_labels_szz_lite.csv` | `data_model/data/dataset_szz.csv`、`dataset_szz_lite.csv` + 七项统计 | **正样本比例落在 40%–60% 必须停下查打标逻辑** |
| ⑥ | 时间序切分 + 训练 + 评估 | `05_split_dataset.py --tag szz` → `python -m pipelines.expert.train`（驱动 06，8 模型） | 共享：`data_model/data/split_szz_{train,test}.csv`；**本线**：`pipelines/expert/models/*_v1.pkl`、`pipelines/expert/reports/model_metrics.md` | 禁随机切分；两类指标都要报 |
| ⑦ | 全量推理出交付文件 | `07_predict_all.py --model pipelines/expert/models/xgb_v1.pkl --out pipelines/expert/data/prediction_result.csv --report pipelines/expert/reports/prediction_stats.md` | `pipelines/expert/data/prediction_result.csv` + `pipelines/expert/reports/prediction_stats.md` | 字段与契约一表三逐字一致；含检验集 |
| ⑧ | 覆盖矩阵 | `08_model_matrix.py --report pipelines/expert/reports/model_matrix.md --baseline-report pipelines/expert/reports/model_metrics.md` | `pipelines/expert/reports/model_matrix.md` | 与 `model_metrics.md` 逐项比对差异为 0 |
| ⑨ | 校准与阈值证据 | `09_calibration_threshold.py --report pipelines/expert/reports/calibration_threshold.md` | `pipelines/expert/reports/calibration_threshold.md` | 只出证据、不改契约；时间序折 |

**切分铁规矩**：按 `committed_at` 时间序，前 70% 训练 / 后 30% 检验，**禁止随机切分**（`EXP`/`NUC` 与时间相关，随机 = 提前看未来）。切分后不重新切分、不改特征。`python 05_split_dataset.py --selfcheck` 必须拦住人为乱序的输入。

## 4. 输入

| 输入 | 来源 | 形态 |
|---|---|---|
| Apache Camel 仓库副本 | 外部（步骤①克隆） | Git 仓库，固定 tag |
| （无其他外部输入） | — | 本线不依赖另三条 pipeline 的任何产物 |

## 5. 输出

**目录约定（2026-10-14 起，四线隔离）**：本线产物**全部落在 `data_model/pipelines/expert/`** 下
（`models/` 模型文件、`reports/` 报告、`data/` 本线私有中间结果），由
`python -m pipelines.expert.train` 驱动产出；**四线共享的上游产物**（仓库副本、提交清单、
标签、特征表、切分下标）仍放 `data_model/data/`，不按线分。

| 产物 | 路径 | 入库？ | 去向 |
|---|---|---|---|
| 提交清单 | `data_model/data/commits.csv` | ❌ | 供语义线构造变更文本 |
| 缺陷标签 | `data_model/data/commit_labels_{szz,szz_lite}.csv` | ❌ | 供语义/融合/端到端共用 |
| 特征表 | `data_model/data/commit_features.csv`（14 项，v1） | ❌ | 落库前由后端按契约二读取 |
| 样本集 | `data_model/data/dataset_{szz,szz_lite}.csv` | ❌ | **融合线的左表**（四线共享） |
| 切分文件 | `data_model/data/split_szz_{train,test}.csv` | ❌ | **四线共用的切分下标**，只读不重切 |
| 切分统计 | `pipelines/expert/reports/split_stats{tag}.md` | ✅ | 证据 |
| 模型文件 | `pipelines/expert/models/{lr,rf,xgb}_v1.pkl` | ❌ | **交付后端**（随包交付） |
| 交付清单 | `pipelines/expert/models/feature_order.txt`（`[models]` 段只列交付三件套） | ❌ | 契约二第三节的副本，供后端装配 |
| 指标报告 | `pipelines/expert/reports/model_metrics.md` | ✅ | ⑧ 的比对基线 |
| 覆盖矩阵 | `pipelines/expert/reports/model_matrix.md` | ✅ | 8 模型 × 2 类 × 两类指标 |
| 校准与阈值 | `pipelines/expert/reports/calibration_threshold.md` | ✅ | 阈值 vs 工作量配额对照 |
| 全量预测 | `pipelines/expert/data/prediction_result.csv` | ❌（灌库后不留） | **交付后端灌 `prediction` 表** |
| 预测统计 | `pipelines/expert/reports/prediction_stats.md` | ✅ | 证据 |

## 6. 关键配置项及其作用

### 6.1 脚本参数

| 脚本 | 参数 | 作用 |
|---|---|---|
| `02_szz_labeling.py` | `--method both` | 两套 SZZ 同时跑并量化差异；不许静默只取其一 |
| `04_build_dataset.py` | `--labels`（可多次） | 指定标签文件，两套标签各产一份样本集 |
| `05_split_dataset.py` | `--tag` | 数据文件名标记（`szz` / `szz_lite`）；`--train-ratio` 切分比例（默认 0.70）；`--train-out` / `--test-out` / `--report` 输出路径；`--selfcheck` 乱序输入断言自检 |
| `06_train_model.py` | `--train` / `--test` | 切分文件路径；`--models` 训练哪些模型（默认 `lr,rf,xgb`，**首 change 复现命令依赖该默认值**）；`--seed` 随机种子（必须固定）；`--report` 指标报告路径；`--features-raw` 原始特征表（算工作量代理用）；`--shap-rows` SHAP 单条耗时实测样本数；`--skip-shap` 仅调试用；`--no-export` 只出指标不导出 `.pkl`（做敏感性对照、避免覆盖主模型） |
| `07_predict_all.py` | `--model` 交付模型；`--dataset` 推理样本集；`--out` 交付文件路径；`--report` 统计报告 | 全量推理（含检验集），不直连数据库 |
| `08_model_matrix.py` | `--report` 矩阵输出；`--baseline-report` 比对基线 | 与 `model_metrics.md` 逐项比对，差异必须为 0 |
| `09_calibration_threshold.py` | `--report` 报告路径 | 时间序折校准 + 阈值/配额对照 |

### 6.2 8 个模型与关键超参（性能优先选型）

课程硬要求「至少 2 类（经典 ML + 神经网络）不少于 8 种」。8 个共用同一份特征、同一切分、同一种子；每个模型用自己的**标准超参**（不为统一而简化）。

| 类别 | 模型 | 关键超参 | 停止方式 | 可逐字节复现 |
|---|---|---|---|---|
| 经典 ML（6） | `lr` 逻辑回归 | `max_iter=1000` | 凸优化，唯一解 | ✅ |
| | `rf` 随机森林 | `n_estimators=300, min_samples_leaf=2` | 树建完即止 | ✅ |
| | `xgb` XGBoost | `n_estimators=300, lr=0.1, max_depth=6, subsample=0.9, colsample_bytree=0.9` | 固定 300 棵 | ✅ |
| | `lgbm` LightGBM | `n_estimators=300, lr=0.1, num_leaves=31, subsample=0.9, subsample_freq=1, colsample_bytree=0.9` | 固定 300 棵 | ✅ |
| | `et` Extra Trees | `n_estimators=300, min_samples_leaf=2` | 树建完即止 | ✅ |
| | `svm` RBF-SVM | `C=1.0, gamma="scale"`, `probability=True` | 凸二次规划，唯一解 | ✅ |
| 神经网络（2） | `mlp_deep` 深层 MLP | 3 隐藏层 (64/32/16)，`alpha=1e-4, max_iter=500, n_iter_no_change=15, validation_fraction=0.1` | 早停（训练集内部验证子集） | ❌ |
| | `tabnet` TabNet | `n_d=n_a=8, n_steps=3, gamma=1.3, max_epochs=100, patience=15, validation_fraction=0.1` | 早停（训练集内部验证子集） | ❌ |

**三条必须能解释的口径**：① 早停只从**训练集内部**切验证子集，检验集始终更晚、不参与早停决策；② `xgb`/`lgbm` 用固定 300 棵而非早停轮数，为让 8 个模型在「不依赖验证集」上口径一致且可逐字节复现（`lgbm` 的 `subsample` 必须配 `subsample_freq>0` 才生效）；③ `svm` 的 `probability=True` 触发 libsvm 内部 5 折 Platt 校准，输出的是校准后概率 —— 保留它是为了与其余 7 个共用同一套 `predict_proba` 口径。**全部模型不设 `class_weight`**，避免个别模型加权破坏可比性。

### 6.3 固定口径（改口径 = 升 `feature_version` 全量重算）

- 14 项列名、顺序、归一化与对数口径以契约二（`docs/model/feature-columns.md`）为唯一权威，`la/ld` 除以 `lt`、`lt/nuc` 除以 `nf`、全部取 `ln`、`entropy` 用 14 天滚动窗口、`rexp` 衰减 `Σ count(n)/(n+1)`。
- 口径一改必须升 `feature_version`（v1 → v2）并全量重算，**不覆盖旧版**；下游对照产物全部重跑。
- 交付模型名 `lr_v1` / `rf_v1` / `xgb_v1` 与接口入参 `model_name` 同名，不得自行改名。

## 7. 与其他 pipeline 的边界与协作关系

| 对象 | 关系 | 具体内容 |
|---|---|---|
| 仅语义 `semantic-only.md` | **上游 → 下游** | 本线交出 `commits.csv`（提交清单）、`commit_labels_szz.csv`（标签）与切分下标；语义线只加 768 列，不改本线任何产物 |
| 融合 `fused.md` | **上游 → 下游** | 本线的 `dataset_{szz,szz_lite}.csv` 是融合线的**左表**；融合线右连接语义向量，前 14 列必须与本线逐字一致 |
| 端到端 `end-to-end.md` | **上游 → 下游** | 本线交出仓库副本、标签与切分下标；端到端只吃变更文本，不吃本线特征表 |
| 后端线 | **下游（跨线交付）** | 收 `models/*.pkl` + `feature_order.txt` + `prediction_result.csv`；本线**不建库表、不直连数据库** |
| 前端线 | 间接 | 通过 `explanation[]` 的 `feature` 键名间接依赖契约二列名 |

**边界红线**：本线不碰接口 / 页面 / 库表；模型文件不入库（走打包交付）；不静默切换交付模型（更优模型须另开「模型切换」提案）。

## 8. 红线

1. **禁随机切分**；`train_test_split(shuffle=True)` 或未指定 `shuffle=False` = 缺陷，必须打回。
2. **只报一类指标 = 一票否决**（Effort-unaware 与 effort-aware 都要报）；`P_norm` 是本组自造变体，**不得对外宣称文献标准 `Popt`**。
3. 正样本比例落在 40%–60% 之间，停下先查打标逻辑，不带可疑标签往下走。
4. 换库后（2026-10-14 ActiveMQ → Apache Camel）**旧仓库实测数字一律不引用**；Camel 全量重跑前的指标位一律标「待回填」。
5. 子集运行会覆盖全量统计报告（`--tag` 只改数据文件名、不改报告名）：跑子集前确认报告名，跑完 `git checkout -- data_model/reports/` 恢复。
6. 神经网络未收敛要**如实登记**，不许静默当已收敛；`mlp_deep` / `tabnet` 不属于「可逐字节复现」类，复现核对比对以固定迭代的模型为准。

## 9. 变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-14 | 1.2 | 训练入口落为 `data_model/pipelines/expert/train.py`（`python -m pipelines.expert.train`），产物全部落到 `pipelines/expert/{models,reports}`；`06_train_model.py` 修两处 pytorch-tabnet 4.1.0 API 不一致（导入路径 `pytorch_tabnet.tabnet` → `pytorch_tabnet.tab_model`；`max_epochs`/`patience` 从构造器移到 `fit()`），并新增 `--delivery-models`（训练 8 个而清单只列 3 个交付模型） |
| 2026-10-14 | 1.1 | 重写为独立自包含的 pipeline 说明（不再依赖 `data-pipeline.md`）：补齐用途/适用场景/九步/输入输出/参数与超参/边界协作/红线；产物表按脚本实际输出核对（补 `reports/split_stats{tag}.md`、`reports/prediction_stats.md`，`prediction_result.csv` 归属改 `data/`） |
| 2026-10-14 | 1.0 | 从 `model-line-plan.md` §3 / `data-pipeline.md` §4 拆出仅专家线独有内容 |
