# 数据链路与版本固定（模型包权威）

> 合并自原 `docs/data-pipeline.md`（已并入本文件）v1.2 ｜ 更新：2026-10-15 ｜ 负责人：蒋励 ｜ 冻结：Sprint 0 末（10-02）
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

- **主对象 Apache Camel**：tag `camel-4.23.0`，commit `b2329103df8f5d1edfca2ad262be09e3be95ee68`（克隆后 `git rev-parse HEAD` 必须与之一致）；JIRA 前缀 `CAMEL-`。注意 Camel 早期历史为 SVN 转换，**有效样本偏 2010 年后**。
- **原 ActiveMQ 方案已废弃**：其仓库副本、中间数据、模型与全部报告已于 2026-10-14 清理（仅存于 git 历史），本条不保留其统计数字。换库原因与边界见 `model-line-plan.md` §5。

固定信息登记（2026-10-15 对齐上游 2026-10-14 的 Camel 运行）：

| 项 | 值 |
|---|---|
| 固定 tag | `camel-4.23.0`（附注标签） |
| 完整 commit | `b2329103df8f5d1edfca2ad262be09e3be95ee68` |
| tag 对象 | `e7094f7ca2abb03f36d118df0572b569eb28ca4f`（不是 commit） |
| 非合并提交数 | 84,461 |
| UTC 时间范围 | 2007-03-19 10:54:57 ～ 2026-10-11 11:16:49 |
| 数字来源 | 上游提交 `866b7dc` 的 `data_model/preparation/reports/commit_extract_stats.md` |

本次通过官方 `git ls-remote` 核验 tag 的 peeled commit；样本数和时间范围引用既有全量报告，**本机未重新跑全量采集/SZZ/训练**。切换动机是扩大训练样本，沿用队友已训练的固定版本，不使用浮动 `main`。

从项目根目录克隆（目标目录须不存在；保留完整历史，不加 `--depth`）：

```bash
git clone --single-branch --branch camel-4.23.0 https://github.com/apache/camel.git data_model/data/camel
git -C data_model/data/camel rev-parse HEAD
# 必须等于 b2329103df8f5d1edfca2ad262be09e3be95ee68
```

旧 ActiveMQ 副本和产物不得与 Camel 混用。已有产物先另行保留；换库后从 `preparation/01–05` 重新生成提交、标签、特征、样本、切分，再由 `pipelines/expert/train.py` 重训并 `predict.py` 重预测，不能只修改 CSV 的 repo_name。历史归档保留旧数据源，不作为当前运行基准。

## 3. 数据落盘路径

| 路径 | 内容 | 入库？ |
|---|---|---|
| `data_model/data/` | 仓库副本/中间数据 | ❌ 被 `.gitignore` 排除 |
| `data_model/pipelines/expert/models/` | 专家线模型文件；清单 feature_order.txt 可入库 | 模型 ❌ 排除 |
| `data_model/reports/` / `data_model/pipelines/expert/reports/` | 共享数据统计 / 专家线训练评估证据 | ✅ 可入库当证据 |
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
| ② | `preparation/01_extract_commits.py` | `commits.csv` + 统计 |
| ③ | `preparation/02_szz_labeling.py --method both` | `commit_labels_{szz,szz_lite}.csv` |
| ④ | `preparation/03_extract_features.py` | `commit_features.csv` |
| ⑤ | `preparation/04_build_dataset.py` | `dataset_{szz,szz_lite}.csv` + 七项统计 |
| ⑥ | `preparation/05_split_dataset.py` ＋ `python -m pipelines.expert.train`（含 ⑧ 覆盖矩阵） | 切分文件/模型/指标报告 |
| ⑦ | `python -m pipelines.expert.predict` | `prediction_result.csv` |
| ⑧ | `python -m pipelines.expert.matrix` | `model_matrix.md`（8 种×2 类×两类指标） |
| ⑨ | `python -m pipelines.expert.calibrate` | `calibration_threshold.md` |

**⑥ 两条铁规矩**：只能时间序切分（禁随机，防时序泄漏）；两类指标都要报。
**⑦ 三条边界**：字段与契约一表三逐字一致；不直连数据库；全量推理（含检验集）。
**①–⑤** 属 change `data-collection-and-szz-labeling`；**⑥⑦** 属 `model-training-and-delivery`；**⑧⑨** 属 `model-expansion`。

> **语义特征主线（Sprint 2，change `semantic-feature-mainline`）在九步之后追加 ⑩–⑯**：`10_semantic_text.py`（按文件构造变更文本）→ `11_semantic_codebert.py`（CodeBERT 语义向量，按提交聚合，落 `feature_version=v2`，**不入库**）→ `13_build_fused.py`（三类设置样本集，同切分下标）→ `14_compare_settings.py`（三类对比）→ `15_feature_ablation.py`（消融）→ 显著性检验（已落地为 `pipelines/expert/significance.py`）。执行顺序、依赖、里程碑 Gate 与完成定义见 `model-line-plan.md` §8。契约二 14 项列名与顺序**一字不动**。
>
> **⑩–⑯ 之后再加 ⑰（端到端，待立项）**。四类设置各自的输入形态、脚本段与产物命名（含「四条线产物不许同名」的命名规范）见 `pipelines/` 目录 —— `data-pipeline.md` 仍只管**共享的数据链路 ①–⑨**。

## 5. 复现命令（从干净 clone）

```bash
cd data_model
git -C data/camel rev-parse HEAD     # 必须等于 b2329103df8f5d1edfca2ad262be09e3be95ee68（tag camel-4.23.0）
python preparation/01_extract_commits.py
python preparation/02_szz_labeling.py --method both
python preparation/03_extract_features.py
python preparation/04_build_dataset.py --labels data/commit_labels_szz.csv --labels data/commit_labels_szz_lite.csv
python preparation/05_split_dataset.py --tag szz
python -m pipelines.expert.train --train data/split_szz_train.csv --test data/split_szz_test.csv
python -m pipelines.expert.predict --model pipelines/expert/models/xgb_v1.pkl
python -m pipelines.expert.matrix
python -m pipelines.expert.calibrate
```

`pipelines.expert.train` 已包含 ⑧ 覆盖矩阵；模型与评估报告留在 expert 目录。完整训练依赖按 `data_model/environment.yml` 准备，本次测试环境只覆盖采集/SZZ/切分回归。

**⑥ 核对命令**：`python preparation/05_split_dataset.py --selfcheck`（打乱输入断言必须拦住）；连跑两次 `pipelines.expert.train` 指标报告应逐行一致（仅 SHAP 计时行不同）。

**两条实测坑**：① 子集运行会覆盖全量统计报告（`--tag` 只改数据文件名不改报告名），子集验证使用独立副本或备份，不能用破坏性恢复丢弃他人的改动；确认无用后跑 `git checkout -- data_model/preparation/reports/` 恢复；② 改了 D4 判据必须重跑窗口对照，否则对照产物是旧口径。

## 6. 必须报出的统计

> 下表为 **Apache Camel** 采集后必须报出的统计（⬜ **待采集回填**，格式如下）。

| 指标 | szz | szz_lite |
|---|---|---|
| 总提交数 | 84,461 | 84,461 |
| 打标成功数 | 83,943 | 83,887 |
| 正样本数 | 18,662 | 12,066 |
| 负样本数 | 65,281 | 71,821 |
| **正样本比例** | **22.23%** | **14.38%** |

来源：上游 `866b7dc` 的 `data_model/preparation/reports/dataset_stats.md`、`szz_labeling_stats.md`，不是本次本机重跑。旧版 11,050 条与 38.98%/27.74% 属于 ActiveMQ 历史实验，不能用作当前 Camel 验收基准。

注意「正样本数 > 修复提交数」属正常：SZZ 一条修复可指控多个引入方，标准行级 SZZ 不做二次过滤，故意与 Kamei 可比。

**正样本比例判据不变**：`02_szz_labeling.py` 的 `ABNORMAL_LOW,HIGH = 0.40,0.60`。落在该区间先排查标签逻辑，不带可疑标签继续训练。

## 7. 关键裁定与判据登记

- PySZZ 不在 PyPI → 两套均为已有自研实现（标准行级 + 文件级简化版）。
- 默认使用完整固定版本历史，不裁剪时间窗口（全链路耗时在 Sprint 预算内）；旧 ActiveMQ 的 24.5 分钟耗时不适用于 Camel，Camel 全量实测值跑完后回填。
- 打标判据 D4：**`CAMEL-\d+`** **且** `\b(fix|bug|patch)`（词首边界），大小写不敏感。仅含 AMQ 编号不是 Camel 修复候选。判据逻辑与词首边界沿用上一版仓库方案，**换库只需改前缀**。
- 保持词首边界以排除 dispatch/debug/prefix 的内嵌子串；旧仓库的 122 条假阳性数量不能移作 Camel 证据。假阳性词族的实测条数见下方登记（`preparation/02_szz_labeling.py` 的 `EXPECTED_OUTER`）。

| 自检基准 | 登记值 |
|---|---|
| 完整版本非合并提交数 | 84461 |
| 含 CAMEL 编号（has_id） | 38716 |
| 编号且修复语义（id_and_fix_word） | 7787 |
| 编号且 fix 词形（id_and_fix_form） | 6631 |

登记来源为 `866b7dc` 的全量报告。原运行时基准尚未登记；本次将已提交的复算值登记供后续独立运行对照，不倒填原运行的自检成功状态。完整基准已登记且输入数恰为 84461 时才比较三项外沿；不一致则在回溯、写标签之前失败。未登记或输入规模不同均为「不可比」，不是通过。规模一致也不能替代对采集版本与输入来源的核验。

### 7.1 SZZ 打标的已知局限（必须如实登记，不许隐去）

> SZZ 出自 2005 年（Śliwerski/Zimmermann/Zeller, MSR '05），**不是最新方法**；但打标层 20 年来没有出现取代它的主流方案，DeepJIT / CC2Vec / LApredict / SimCom 等现代工作的数据集仍用 SZZ 类回溯标注。课程把「SZZ 算法实现」列为数据采集模块的**必做项**，故实现它符合要求；课程所称「现在主流方法」指**特征与模型层**（预训练语义特征），不是打标层。

本组 SZZ 实现强于多数论文之处：两套并行且差异量化、判据实测外沿数字、回溯未命中不记 0、自研标准行级并留决策记录。

**已知局限（文献已讨论，答辩须主动说）**：

| # | 局限 | 说明 |
|---|---|---|
| 1 | **代理标注，非 ground truth** | 「修复提交 → blame 回溯」是推断，不是事实。真缺陷引入可能漏，非缺陷可能误收 |
| 2 | **blame 追溯过远（假阳性主因）** | SZZ 经典问题：blame 可能一路追到文件创建或大重构那次提交，把老提交误判为引入方 |
| 3 | **对代码移动 / 重构敏感** | 行被移动或重构时，行级 blame 结果失真；这也是做 `szz_lite`（文件级）作对照的原因之一 |
| 4 | **「缺陷引入提交」定义本身不稳定** | 两套方法正样本比例差 **7.85 个百分点**（Camel 上游报告：`szz` 22.23% vs `szz_lite` 14.38%），说明标签口径对方法选择敏感 |
| 5 | **D4 判据是自定启发式** | 文献无统一标准，各论文判据不同；本组数字**不可与他组横向比较**，只能组内自比 |

应对：① 两套结果均产出并量化差异，不静默取其一；② 引用 da Costa et al.（IEEE TSE，SZZ 结果评估框架）说明「SZZ 结果需被评估而非默认正确」；③ 局限如实写入报告与答辩，**不包装成高精度标注**。


## 8. 变更日志（精简）

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-15 | 1.2 | Camel 固定源、复现路径与判据基准对齐上游 866b7dc；区分既有证据与本机测试，保留历史来源 |
| 2026-10-09 | 1.1 | 补权威边界指针；复现命令去 onboarding 引用 |
| 2026-09-19 | 1.0 | 链路扩到九步（补⑧⑨ 覆盖矩阵/校准阈值） |
| 2026-09-18 | 0.97~0.99 | 七步→九步、子集坑修正、Sprint 周期口径 |
| 2026-09-16 | 0.9~0.96 | 初版→全链路跑通→正样本比例判据统一 40%~60% |
