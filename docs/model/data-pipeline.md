# 数据链路与版本固定（模型包权威）

> 合并自原 `docs/data-pipeline.md`（已并入本文件）v1.1 ｜ 负责人：蒋励 ｜ 冻结：Sprint 0 末（10-02）
> Sprint 0 第 2 号交付物验收依据：可复现脚本 + 样本总数与正负样本比例。

## 0. 解决什么问题

Sprint 0 第 2 号交付物验收依据就是本文。权威边界：任务在飞书、代码在仓库。本文只写三件事：数据从哪来且固定在哪个版本、落在哪、每步脚本入口与复现命令。

## 1. 数据源

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/apache/camel.git`（**主对象，2026-10-14 换库**） |
| 仓库名（入库 `commit.repo_name`） | `camel` |
| 本期范围 | 只用这一个仓库，不跨仓库训练对比 |
| 数据源扩展 | 公开 JIT 数据集（G1-3）仅作对照，**不替换主对象** |

## 2. 版本固定（最重要）

**必须固定到某个 tag/commit，不用 `main`**（main 每天变，两个月后无法解释 F1 波动）。

- **主对象 Apache Camel**：tag `camel-4.23.0`，commit `b2329103df8f5d1edfca2ad262be09e3be95ee68`（克隆后 `git rev-parse HEAD` 必须与之一致）；提交总数待实测；JIRA 前缀 `CAMEL-`。注意 Camel 早期历史为 SVN 转换，**有效样本偏 2010 年后**。
- **原 ActiveMQ 方案已废弃**：其仓库副本、中间数据、模型与全部报告已于 2026-10-14 清理（仅存于 git 历史），本条不保留其统计数字。换库原因与边界见 `model-line-plan.md` §5。

## 3. 数据落盘路径

| 路径 | 内容 | 入库？ |
|---|---|---|
| `data_model/data/` | 仓库副本/中间数据 | ❌ 被 `.gitignore` 排除 |
| `data_model/models/` | 模型文件 | ❌ 排除 |
| `data_model/reports/` | 统计结果（样本数/比例/指标） | ✅ 可入库当证据 |
| `data_model/artifacts/` | 中间产物/缓存 | ❌ 排除 |

**不改 `.gitignore`、不用 `git add -f`** —— 数据集/模型不入库是课程硬要求。

## 4. 链路九步

```
① 克隆固定版本 → ② 抽取提交 → ③ SZZ 打标 → ④ Kamei14 特征(v1,基线对照) → ⑤ 样本集
                                                     ↓
                          ⑦ 全量预测出交付文件 ← ⑥ 时间序切分/训练/评估
                                                     ↓
                          ⑨ 校准与阈值证据 ← ⑧ 覆盖矩阵(8种/2类)
                                                     ↓
        ⑩–⑯ 语义特征主线(Sprint2, v2, 不入库): 10_语义文本→11_CodeBERT→13_融合样本→14_三类对比→15_消融→16_显著性
```

| 步 | 脚本 | 输出 |
|---|---|---|
| ① | 手工（§2 命令） | `data/camel/` |
| ② | `01_extract_commits.py` | `commits.csv` + 统计 |
| ③ | `02_szz_labeling.py --method both` | `commit_labels_{szz,szz_lite}.csv` |
| ④ | `03_extract_features.py` | `commit_features.csv` |
| ⑤ | `04_build_dataset.py` | `dataset_{szz,szz_lite}.csv` + 七项统计 |
| ⑥ | `05_split_dataset.py` `06_train_model.py` | 切分文件/模型/指标报告 |
| ⑦ | `07_predict_all.py` | `prediction_result.csv` |
| ⑧ | `08_model_matrix.py` | `model_matrix.md`（8 种×2 类×两类指标） |
| ⑨ | `09_calibration_threshold.py` | `calibration_threshold.md` |

**⑥ 两条铁规矩**：只能时间序切分（禁随机，防时序泄漏）；两类指标都要报。
**⑦ 三条边界**：字段与契约一表三逐字一致；不直连数据库；全量推理（含检验集）。
**①–⑤** 属 change `data-collection-and-szz-labeling`；**⑥⑦** 属 `model-training-and-delivery`；**⑧⑨** 属 `model-expansion`。

> **语义特征主线（Sprint 2，change `semantic-feature-mainline`）在九步之后追加 ⑩–⑯**：`10_semantic_text.py`（按文件构造变更文本）→ `11_semantic_codebert.py`（CodeBERT 语义向量，按提交聚合，落 `feature_version=v2`，**不入库**）→ `13_build_fused.py`（三类设置样本集，同切分下标）→ `14_compare_settings.py`（三类对比）→ `15_feature_ablation.py`（消融）→ `16_statistical_test.py`（显著性）。执行顺序、依赖、里程碑 Gate 与完成定义见 `model-line-plan.md` §8。契约二 14 项列名与顺序**一字不动**。
>
> **⑩–⑯ 之后再加 ⑰（端到端，待立项）**。四类设置各自的输入形态、脚本段与产物命名（含「四条线产物不许同名」的命名规范）见 `pipelines/` 目录 —— `data-pipeline.md` 仍只管**共享的数据链路 ①–⑨**。

## 5. 复现命令（从干净 clone）

```bash
cd data_model
git -C data/camel rev-parse HEAD     # 必须等于 b2329103df8f5d1edfca2ad262be09e3be95ee68（tag camel-4.23.0）
python 01_extract_commits.py
python 02_szz_labeling.py --method both
python 03_extract_features.py
python 04_build_dataset.py --labels data/commit_labels_szz.csv --labels data/commit_labels_szz_lite.csv
python 05_split_dataset.py --tag szz
python 06_train_model.py --train data/split_szz_train.csv --test data/split_szz_test.csv
python 07_predict_all.py --model models/xgb_v1.pkl
python 08_model_matrix.py
python 09_calibration_threshold.py
```

**⑥ 核对命令**：`python 05_split_dataset.py --selfcheck`（打乱输入断言必须拦住）；连跑两次 `06` 指标报告应逐行一致（仅 SHAP 计时行不同）。

**两条实测坑**：① 子集运行会覆盖全量四份统计报告（`--tag` 只改数据文件名不改报告名），跑完 `git checkout -- data_model/reports/` 恢复；② 改了 D4 判据必须重跑窗口对照，否则对照产物是旧口径。

## 6. 必须报出的统计

> 下表为 **Apache Camel** 采集后必须报出的统计（⬜ **待采集回填**，格式如下）。

| 指标 | szz | szz_lite |
|---|---|---|
| 总提交数 | ⬜ 待实测 | ⬜ 待实测 |
| 打标成功数 | ⬜ | ⬜ |
| 正样本数 | ⬜ | ⬜ |
| 负样本数 | ⬜ | ⬜ |
| **正样本比例** | ⬜ | ⬜ |

**正样本比例判据**：实现里 `ABNORMAL_LOW,HIGH = 0.40,0.60` —— **落在 40%–60% 之间就停下来先查打标逻辑**，不要带可疑标签往下走。另注意「正样本数 > 修复提交数」属正常：SZZ 一条修复可指控多个引入方，标准行级 SZZ 不做二次过滤，故意与 Kamei 可比。

## 7. 关键裁定（待定项已结清）

- PySZZ 不在 PyPI → 两套均为自研实现（标准行级 + 文件级简化版）。
- 不裁剪时间窗口（全链路耗时在 Sprint 预算内；Camel 全量实测值跑完后回填）。
- 打标判据 D4：**`CAMEL-\d+`** **且** `\b(fix|bug|patch)`（词首边界）。判据逻辑与词首边界沿用上一版仓库方案，**换库只需改前缀**；假阳性词族的实测条数须在 Camel 全量上重测回填（登记处见 `02_szz_labeling.py` 的 `EXPECTED_OUTER`）。

### 7.1 SZZ 打标的已知局限（必须如实登记，不许隐去）

> SZZ 出自 2005 年（Śliwerski/Zimmermann/Zeller, MSR '05），**不是最新方法**；但打标层 20 年来没有出现取代它的主流方案，DeepJIT / CC2Vec / LApredict / SimCom 等现代工作的数据集仍用 SZZ 类回溯标注。课程把「SZZ 算法实现」列为数据采集模块的**必做项**，故实现它符合要求；课程所称「现在主流方法」指**特征与模型层**（预训练语义特征），不是打标层。

本组 SZZ 实现强于多数论文之处：两套并行且差异量化、判据实测外沿数字、回溯未命中不记 0、自研标准行级并留决策记录。

**已知局限（文献已讨论，答辩须主动说）**：

| # | 局限 | 说明 |
|---|---|---|
| 1 | **代理标注，非 ground truth** | 「修复提交 → blame 回溯」是推断，不是事实。真缺陷引入可能漏，非缺陷可能误收 |
| 2 | **blame 追溯过远（假阳性主因）** | SZZ 经典问题：blame 可能一路追到文件创建或大重构那次提交，把老提交误判为引入方 |
| 3 | **对代码移动 / 重构敏感** | 行被移动或重构时，行级 blame 结果失真；这也是做 `szz_lite`（文件级）作对照的原因之一 |
| 4 | **「缺陷引入提交」定义本身不稳定** | 两套方法（行级 `szz` vs 文件级 `szz_lite`）的正样本比例存在**明显差异**，说明标签口径对方法选择敏感；**具体差值待 Apache Camel 全量实测回填**（旧仓库实测值已随 2026-10-14 换库失效） |
| 5 | **D4 判据是自定启发式** | 文献无统一标准，各论文判据不同；本组数字**不可与他组横向比较**，只能组内自比 |

应对：① 两套结果均产出并量化差异，不静默取其一；② 引用 da Costa et al.（IEEE TSE，SZZ 结果评估框架）说明「SZZ 结果需被评估而非默认正确」；③ 局限如实写入报告与答辩，**不包装成高精度标注**。


## 8. 变更日志（精简）

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-09 | 1.1 | 补权威边界指针；复现命令去 onboarding 引用 |
| 2026-09-19 | 1.0 | 链路扩到九步（补⑧⑨ 覆盖矩阵/校准阈值） |
| 2026-09-18 | 0.97~0.99 | 七步→九步、子集坑修正、Sprint 周期口径 |
| 2026-09-16 | 0.9~0.96 | 初版→全链路跑通→正样本比例判据统一 40%~60% |
