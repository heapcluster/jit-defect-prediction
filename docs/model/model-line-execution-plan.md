# 模型线端到端执行计划清单（启动 → 完成）

> 负责人：蒋励（数据与模型线）｜版本 1.0 ｜ 2026-10-14 ｜ 关联 change：`semantic-feature-mainline`、`public-dataset-quality`
> 三层分工：`model-line-plan.md`（方案权威，管"是什么 / 谁来做"）· `openspec/changes/*/tasks.md`（change 明细，管"怎么改"）· **本文件（端到端计划，管"按什么顺序做完、做完的标志是什么"）**
> 铁律：勾了 tasks ≠ 功能合格；每个阶段必须有**可复现命令 + 证据文件路径**。

---

## 0. 完成定义（DoD）：模型线真正"做完"的十条硬标准

全部满足才算模型线闭环验收：

1. 语义特征已按 `feature_version=v2` 落盘（或明确降级为抽样/听取，并写明原因）。
2. 三类设置（仅专家 / 仅语义 / 融合）在**同一时间序切分、同一 8 模型、同一套指标**下产出 `data_model/reports/three_way_comparison.md`。
3. Effort-unaware（AUC/F1/P/R/Acc）与标准 Effort-aware（CE@20% / Recall@20% / Popt / ALPA）**两类齐全**；`P_norm` 已标注为自造变体（非 `Popt`）。
4. 显著性检验完成：Bootstrap（≥1000 次）+ Wilcoxon signed-rank + McNemar，产出 `data_model/reports/statistical_test.md`。
5. 专家特征消融完成（留一法 + 置换重要性，两口径交叉），产出 `data_model/reports/feature_ablation.md`。
6. 多切分点稳健性完成（70/30 主切分 + 60/40、80/20），翻转须如实报告。
7. PD 公开数据集支线按 PD-0 结论推到应有终点（取到则 PD-1~4；取不到则降级为「加载器框架 + Camel 自验」并写明原因）。
8. 单测 + 集成测试通过：`test_semantic_text.py` / `test_feature_ablation.py`（计划 ≥20 条）、`test_compare_settings_pipeline.py`（计划 ≥6 条）。
9. 交付边界确认：未静默切换模型（`model-coverage` R6）；若要切换须另开「模型切换」提案。
10. 文档口径同步完成：`training-eval.md` §4、`methodology-references.md` §3、`design/addons.md` §4、周报。

---

## 1. 阶段总览（关键路径）

| Phase | 名称 | 依赖 | 关键交付 | 状态 |
|---|---|---|---|---|
| **P0** | 环境与基线冻结 | — | `jit-defect-prediction` 单环境 + torch 栈 + 146 测试绿 | ✅ 完成 |
| **P1** | 变更文本构造 → CodeBERT 语义特征落盘 | P0 | `semantic_text_v2.csv` / `semantic_codebert_v2.csv` | ⬜ |
| **P2** | 评测协议对齐（EV） | P0（**可与 P1 并行**） | 标准 effort-aware + 显著性 + `P_norm` 标注 | ⬜ |
| **P3** | 融合样本构建（三类设置） | P1 | 三套样本集 + 同切分下标 | ⬜ |
| **P4** | 三类对比实验（**核心交付**） | P2 + P3 | `three_way_comparison.md` | ⬜ |
| **P5** | 消融 + 多切分稳健性 | P4 | `feature_ablation.md` + 稳健性表 | ⬜ |
| **P6** | 公开数据集治理（PD，独立支线） | P0 | 按 PD-0 结论推进 | ⬜ |
| **P7** | 交付边界 + 文档同步 + 验收收口 | P4–P6 | 十条 DoD 全绿 | ⬜ |

- **关键路径**：`P0 → P1 → P3 → P4 → P5 → P7`
- **可并行**：P2（评测对齐）与 P1 并行，但**必须在 P4 前完成**；P6（PD）全程并行，不阻塞主线。

---

## 2. 分阶段计划

### P0 环境与基线冻结 ✅ 已完成

- **目标**：单环境就绪，且证明未破坏既有基线。
- **已交付**：`jit-defect-prediction`（python 3.12），含 `torch 2.5.1`（4060 装 cu124 wheel）/ `transformers 4.46.1`，以及 `numpy 2.5.3 / pandas 3.0.5 / scikit-learn 1.9.1 / scipy 1.18.1 / xgboost 3.4.1 / shap 0.52`（版本已随 change `env-single-source` 与各线 requirements 对齐）。
- **验收证据**：
  - `conda activate jit-defect-prediction` → `python -c "import torch,transformers,numpy,pandas,sklearn,xgboost,shap"` 通过；
  - 项目根 `python -m pytest -q` → **146 passed**（合并 torch 后基线无破坏）。
- **事实源**：`data_model/environment.yml`（已去除写死 `prefix` 与 win-64 专属 build，可移植；仓库内不再保留 requirements.txt）。
- **权重（已就绪）**：CodeBERT 权重（`microsoft/codebert-base`，124.6M 参数）**已预下载**到本地 HF 缓存，并**离线验证通过**（`HF_HUB_OFFLINE=1` 加载成功、`hidden=768`、前向输出 `(1,15,768)`）；缓存路径 `~/.cache/huggingface/hub/models--microsoft--codebert-base`。SF-2 / SF-3 可离线直接调用，无需联网。

### P1 变更文本构造 → CodeBERT 语义特征落盘

- **目标**：把每次代码变更转成可喂给 CodeBERT 的文本，抽出语义向量并落盘 v2。
- **任务**（对应 openspec §4–§5、SF-2/SF-3/SF-4）：
  - 新增 `data_model/10_semantic_text.py`：按**文件**构造变更文本（路径 + 变更类型 + 增删行 + 提交信息首行），单文件超上限**按行截断并记录**截断文件数与行数；输出 `semantic_text_v2.csv`。
  - 同一份文本供 CodeBERT 与 MiniLM 两条路线**共用**，避免双份构造漂移。
  - **先跑 100 条基准测试**（SF-2）：实测单条耗时与吞吐（CPU 预期 50–150ms/条），据此决定全量或抽样；记录设备、耗时、是否全量、截断统计。
  - 新增 `data_model/11_semantic_codebert.py`：CodeBERT / GraphCodeBERT 对当前 Camel 固定版本的 84,461 条提交提特征，按提交聚合（多文件取均值），落 `data_model/data/semantic_codebert_v2.csv`（`feature_version=v2`，**不入库、不进交付链**）。
  - 降级项：CPU 超预期则按时间序**分层抽样**（禁随机），产出 `semantic_codebert_v2_sample.csv` + 抽样说明。
  - 可选：`11b_semantic_minilm.py`（`all-MiniLM-L6-v2`，通用句向量非代码专用），仅作弱基线对照，进度紧可直接砍。
- **输出**：`semantic_text_v2.csv`、`semantic_codebert_v2.csv`（或 `_sample`）、100 条基准计时报告、截断统计。
- **DoD**：落盘行数与 SZZ 标注提交数对齐；契约二 14 项列名与顺序未动；向量非全零；抽样与否如实登记。
- **风险**：CPU 耗时 → 先 100 条基准；**禁止谎报全量**。

### P2 评测协议对齐（EV，与 P1 并行，必须早于 P4）

- **目标**：把评估口径换成文献标准 + 显著性，避免"自造指标"被质疑。
- **任务**（openspec §11、EV-1/EV-2/EV-3）：
  - 补标准 effort-aware：**CE@20% / Recall@20% / Popt / ALPA**；`P_norm` 加标注（自造归一化变体，锚点=实测随机均值与上界，**与文献 `Popt` 非同一指标**）；补单特征基线（`la` / `ld` 单特征排序对照）。
  - 新增 `data_model/16_statistical_test.py`：Bootstrap 重采样（≥1000 次）+ Wilcoxon signed-rank（配对于 bootstrap 样本）+ McNemar（阈值 0.5），产出 `statistical_test.md`。
  - 复核测试集未参与调参（`fit` 只用训练集、早停验证子集来自训练集内部），结论写入报告。
  - EV-3 已 ✅：`P_norm` 标注已落（`training-eval.md` §3、`methodology-references.md` §3）。
- **输出**：指标进 `model_matrix.md`；显著性表；`P_norm` 标注文字。
- **DoD**：两类指标齐全且脚本可复现；任何对外表述中 `P_norm` 均不与 `Popt` 混称。

### P3 融合样本构建（三类设置）

- **目标**：造出"仅专家 / 仅语义 / 融合"三套可训样本集，保证公平对比。
- **任务**（openspec §7）：
  - 新增 `data_model/13_build_fused.py`：按 `commit_hash` 左连接专家 14 项与语义向量，产出三套样本集；**缺失语义向量的提交显式标注并单列数量，不得用 0 填充冒充**。
  - 切分沿用 `05_split_dataset.py` 时间序切分与 `validate_split` 断言，**三套样本集必须使用同一切分下标**。
- **输出**：三类样本集 + 缺失向量计数表 + 切分下标证据。
- **DoD**：三套的 train/test `commit_hash` 集合**逐字相同**（集成测试断言）。

### P4 三类对比实验（核心交付）

- **目标**：模型线最重要的证据——同一条件下比较"专家 vs 语义 vs 融合"。
- **任务**（openspec §8、SF-5）：
  - 新增 `data_model/14_compare_settings.py`：三类设置 × 同一 8 模型（`lr_v1 / rf_v1 / xgb_v1 / nb_v1 / dt_v1 / knn_v1 / mlp_v1 / mlp_deep_v1`），跑 Effort-unaware + Effort-aware。
  - 产出 `data_model/reports/three_way_comparison.md`（三类 × 8 模型 × 两类指标），标注每组所用特征版本与模型清单。
- **输出**：`three_way_comparison.md`。
- **DoD**：8 模型齐全、两类指标齐全；语义不占优时**如实报告**（不是失败）；后端不接新模型。

### P5 消融 + 多切分稳健性

- **目标**：回答"哪些特征真有用""结论是否依赖切分点"。
- **任务**（openspec §9、§13、SF-6/SF-7）：
  - 新增 `data_model/15_feature_ablation.py`：Kamei 14 **留一法消融** + 检验集**置换重要性**，两个口径交叉验证，产出 `feature_ablation.md`（Top-K 效力排序）。
  - 多切分稳健性：除主切分 70/30，再用 **60/40 与 80/20** 两个时间序切分点各跑一遍三类设置，产出「切分点 × 设置 × 指标」稳健性表；结论翻转须**如实报告**，不挑好结果。
  - 前置约束：openspec §13.3——评测协议（P2）未完成前不做稳健性。
- **输出**：`feature_ablation.md` + 稳健性表。
- **DoD**：两份产出齐备；稳健性结论与三个切分点一致，或明确登记翻转原因。

### P6 公开数据集治理（PD，独立支线，不阻塞主线）

- **目标**：把 G1-3 从"可选"做成承诺范围内的质量治理 + 多语言证据。
- **任务**：
  - **PD-0（阻塞前置）**：公开 JIT 数据集**可下载性验证**（HF 经代理/镜像已 200，但公开数据集需单独验证）；不通过则降级为「加载器框架 + Camel 自验」并写明原因，**不虚构数据**。
  - PD-1：对齐 `commit` / `commit_label` / `commit_feature` 的加载器；缺字段报错终止，不产半成品。
  - PD-2：三维度质量治理（标签粒度 / 语种分布 / 缺失率·重复率·时间序一致性）→ 质量报告。
  - PD-3：多语言证据（非 Java 样本单列统计）→ 语种分布报告。
  - PD-4（可选）：若取到 OpenStack / Qt 等标准 benchmark，与已发表结果（AUC/F1）做量级对照；取不到不强求，不得为凑对照选用非标准数据集。
- **DoD**：PD-0 有明确通过/降级结论；后续按结论推进；任何降级写明原因。

### P7 交付边界 + 文档同步 + 验收收口

- **目标**：把模型线证据固化进交付物，且不越界。
- **任务**（openspec §10、§12）：
  - 确认 `backend/app/model_registry.py` 与 `data_model/models/[models]` 段**未被改动**；若三类对比显示语义/融合更优，**另开「模型切换」提案**（`model-coverage` R6），本线不静默切换。
  - 文档口径同步：`training-eval.md` §4、`methodology-references.md` §3、`design/addons.md` §4、周报「已完成 / 下一步 / 存在问题」。
  - 形态说明：写明「**预训练模型提特征 → 经典分类器**」的混合形态，**非端到端**；并列 DeepJIT / CC2Vec / LApredict / SimCom 各自形态，**不得暗示复现 SOTA**。
  - 验收：按 `specs/semantic-features/spec.md` 的 7 条 Requirement 逐条走，比对 `three_way_comparison.md`。
- **DoD**：§0 十条完成定义全部满足；证据归档至 `data_model/reports/`。

---

## 3. 里程碑 Gate（卡口）

| Gate | 触发点 | 放行条件 | 不放行怎么办 |
|---|---|---|---|
| G0 | P0 出口 | torch 栈 import 通过 + 146 测试绿 | ✅ 已放行 |
| G1 | P1 出口 | 100 条基准计时报告 + 语义 CSV 落盘 | 未计时就跑全量 = 缺陷，打回 |
| G2 | P2 出口 | 标准 effort-aware + 显著性脚本可跑 | **P4 不得开始** |
| G3 | P3 出口 | 三套样本集 + 同切分下标断言通过 | 下标不一致打回重切 |
| G4 | P4 出口 | `three_way_comparison.md` 产出且 8 模型齐全 | 缺模型即打回 |
| G5 | P5 出口 | 消融报告 + 三切分稳健性表 | 缺翻转说明不放行 |
| G6 | P7 出口 | 十条 DoD 全绿 + 未静默切换模型 | **模型线完成** |

---

## 4. 关键复现命令

```bash
conda activate jit-defect-prediction

# P1 文本构造与语义特征
cd data_model
python 10_semantic_text.py                 # 构造变更文本
python 11_semantic_codebert.py             # 先跑 100 条基准，再决定全量/抽样

# P2 评测对齐与显著性
python 16_statistical_test.py

# P3 融合样本
python 13_build_fused.py

# P4 三类对比
python 14_compare_settings.py

# P5 消融
python 15_feature_ablation.py

# 单测与集成测试
python -m pytest tests/test_semantic_text.py tests/test_feature_ablation.py -q
python -m pytest tests/test_compare_settings_pipeline.py -q

# 回归：基线不得被破坏
cd .. && python -m pytest -q               # 期望 146 passed
```

---

## 5. 风险与降级（红线）

| 风险 | 降级路径 | 红线 |
|---|---|---|
| CPU 跑不动 Camel 全量 84,461 条 | 100 条基准 → 时间序分层抽样 + 如实登记 | **不得谎报全量** |
| CodeBERT 权重下载失败 | HF 经代理/镜像均 200 可用；失败改用 `HF_ENDPOINT=https://hf-mirror.com` | **不得伪造语义结果** |
| 公开数据集取不到 | PD-0 结论 → 加载器框架 + Camel 自验 + 写明原因 | **不得虚构数据** |
| 语义特征不如专家特征 | 如实报告三类对比结论 | "不占优"不是失败 |
| 想换更优模型上线 | 另开「模型切换」提案（R6） | **不得静默切换** |

---

## 6. 状态总表（勾选用）

| Phase | 编号 | 任务 | 依赖 | 交付物 | 状态 |
|---|---|---|---|---|---|
| P0 | SF-1 | 单环境 `jit-defect-prediction` + torch 栈 | — | `data_model/environment.yml` + 146 测试绿 | ✅ |
| P1 | SF-3 | `10_semantic_text.py` 变更文本构造 | P0 | `semantic_text_v2.csv` | ⬜ |
| P1 | SF-2 | 100 条基准定时限 | P0 | 计时报告（全量/抽样判据） | ⬜ |
| P1 | SF-4 | `11_semantic_codebert.py` 向量落盘 v2 | SF-2 | `semantic_codebert_v2.csv` | ⬜ |
| P2 | EV-1 | 标准 effort-aware + `P_norm` 标注 + 单特征基线 | P0 | 指标进 `model_matrix.md` | ⬜ |
| P2 | EV-2 | Bootstrap + Wilcoxon + McNemar | EV-1 | `statistical_test.md` | ⬜ |
| P2 | EV-3 | `P_norm` 自造变体标注 | — | 文档已就位 | ✅ |
| P3 | 融合 | `13_build_fused.py` 三套样本集 + 同切分 | P1 | 三类样本集 | ⬜ |
| P4 | SF-5 | `14_compare_settings.py` 三类对比 | P2, P3 | `three_way_comparison.md` | ⬜ |
| P5 | SF-6 | `15_feature_ablation.py` 留一法 + 置换重要性 | P4 | `feature_ablation.md` | ⬜ |
| P5 | SF-7 | 60/40、80/20 多切分稳健性 | P4（且 P2 完成） | 稳健性表 | ⬜ |
| P6 | PD-0 | 公开数据集可下载性验证 | P0 | 结论（通过/降级） | ⬜ |
| P6 | PD-1~4 | 加载器 / 质量治理 / 多语言 / 文献对照 | PD-0 | 质量报告 | ⬜ |
| P7 | 收口 | 交付边界确认 + 文档同步 + 验收 | P4–P6 | 十条 DoD | ⬜ |

> 状态口径：✅ 已完成 / 🔄 进行中 / ⬜ 未开始 / 🔶 阻塞前置。
> 运行顺序与完成标志以本文件为准；方案结论以 `model-line-plan.md` 为准；改法细节以 `openspec/changes/*/tasks.md` 为准。
