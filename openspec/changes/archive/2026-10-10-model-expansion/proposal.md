# 模型覆盖补齐（2 类 8 种）

> Sprint 1 ｜ 承接 `docs/sprint0-scope.md` 第 2 节的**分期口径**（先做 2–3 个经典模型跑通链路，其余模型后置补齐，总数达到 8 种）
> 起草 2026-09-19 ｜ 起草人 蒋励 ｜ 关联契约：`docs/contracts/feature-columns.md`（契约二，冻结日期 2026-09-18）
>
> ⚠️ 契约基线的判定方式沿用首 change：**以各契约文件头部的「版本 + 冻结日期」为准，不引用 PR 编号或合并时机。**

## Why

课程《项目要求》要求「至少 **2 类**（经典机器学习、深度学习）不少于 **8 种**预测模型」。现状是 **1 类 3 种**：

| 现状 | 值 | 证据 |
|---|---|---|
| 类别数 | **1**（经典机器学习） | `data_model/06_train_model.py` 的 `MODEL_NAMES` |
| 模型数 | **3**（`lr_v1` / `rf_v1` / `xgb_v1`） | `data_model/reports/model_metrics.md` |

首 change（`model-training-and-delivery`）按 MVP 分期只做 2–3 个经典模型跑通链路，`docs/sprint0-scope.md` 第 2 节同时写明「**其余模型后置补齐，总数达到 8 种**」。链路现已跑通（时间序切分、两类指标、`.pkl` 导出、全量预测均已交付），**「后置」的这一段到期**，本 change 执行补齐。

同时清一笔评估欠账：首 change 的 Effort-aware 表已实测出「按 `risk_score` 排序在 LOC 工作量代理下不如按风险密度排序」，登记为契约三提案（与 Issue #38「高风险阈值语义」同源），但**决策缺证据** —— 缺概率校准质量，以及「固定阈值 vs 配额取前 N%」在**同一工作量**下的召回对照。本 change 把这份证据补上（只出证据，不改契约）。

## What Changes

1. **新增 3 个经典机器学习模型**：`nb_v1`（高斯朴素贝叶斯）、`dt_v1`（决策树）、`knn_v1`（k 近邻，k=25，标准化后计算）
2. **新增第 2 类：神经网络（深度学习）类 2 个**：`mlp_v1`（1 隐藏层）、`mlp_deep_v1`（3 隐藏层 + 早停）→ 类别数 **1 → 2**、模型数 **3 → 8**
3. **产出覆盖矩阵报告** `data_model/reports/model_matrix.md`：8 种 × 所属类别 × 两类指标，并标注**每类最优**
4. **产出概率校准与阈值策略证据** `data_model/reports/calibration_threshold.md`：时间序 CV 下的校准质量（Brier / 对数损失 / 分箱可靠性）＋「固定阈值 0.50」与「配额取前 1% / 5% / 10%」在**同一工作量**下的召回对照
5. **文档回填**：`data_model/README.md`（模型覆盖与类别口径）、`docs/data-pipeline.md`（链路表与复现命令补评估扩展步骤）

**为什么不是 LSTM / RNN**（把话说在前面，别被问住）：现有样本集是**提交级特征矩阵**（10,893 条可训练样本 × 14 项），没有序列结构；要做序列模型得先建序列化数据集（按时间窗切片），那是新的数据工程 + 新的数据口径，与「先把覆盖补齐」不是一件事。重开条件写在 `design.md`，**不在本 change 里做**。

## Capabilities

### New Capabilities

- `model-coverage`: 模型组合的类别与数量覆盖（≥2 类、≥8 种）、每个模型的类别登记与两类指标汇总，以及支撑契约三阈值提案的概率校准与阈值策略证据

### Modified Capabilities

无 —— 首 change 的能力（`model-training` 等）尚未归档进 `openspec/specs/`，本 change **不修改其 Requirement**（避免依赖未归档规格），只新增 `model-coverage`。

## 影响与边界

| 项 | 内容 |
|---|---|
| 影响目录 | `data_model/`（扩展 `06_train_model.py`、新增 `08_model_matrix.py`、`09_calibration_threshold.py` 与两份报告）、`docs/data-pipeline.md`（链路表与复现命令回填） |
| 新增依赖 | **无** —— 8 个模型全部由既有依赖承载（`scikit-learn` 的 `linear_model` / `ensemble` / `naive_bayes` / `tree` / `neighbors` / `neural_network`）。按 `AGENTS.md` 第五节，新增依赖必须先问，本 change 不触发该流程 |
| 交付物是否变化 | **否** —— 后端加载的交付模型仍是 `xgb_v1`，`models/feature_order.txt` 的 `[models]` 段不变，`prediction_result.csv` 仍由 `07` 产出。新模型只进**评估矩阵**，不进后端加载路径 |
| 契约 | 只读不改。阈值语义与排序口径仍以契约三为准，证据交给提案（Issue #37 / #38）决策 |
| 数据边界 | 模型与中间产物不入库；只入库 `reports/` 下的小体积报告 |
| 不做什么 | 不引入 PyTorch / TensorFlow；不做序列模型；不改特征口径（`feature_version` 仍 `v1`）；不改时间序切分规则；不做超参自动搜索；不改契约字段名、列名与接口路径 |
