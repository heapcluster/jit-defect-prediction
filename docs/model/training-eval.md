# 模型训练与评估（8 种 / 2 类 / 两类指标）

> **状态：指针（2026-10-24 降级）。** 指标口径、超参、评估结论的**唯一权威**是
> [`model-line-plan.md`](model-line-plan.md)。本文只保留「切分铁规矩」与「8 模型覆盖矩阵」两节，
> 其余如与 `model-line-plan.md` 冲突，**以 `model-line-plan.md` 为准**。
>
> 负责人：蒋励 ｜ 关联 change：`model-training-and-delivery`、`model-expansion`
> 课程硬要求：「至少 2 类（经典机器学习和深度学习）不少于 8 种预测模型、Effort-unware 和 effort-aware 两类、训练集和测试集划分」。

## 1. 切分铁规矩

- **按 `committed_at` 时间序切分，前 70% 训练 / 后 30% 测试，禁止随机切分**（EXP/NUC 等时间相关特征，随机=提前看未来，准确率假的）。
- 写进 `AGENTS.md` 硬红线；`train_test_split(shuffle=True)` 或未指定 `shuffle=False` = 缺陷，必须打回。

## 2. 8 种模型（2 类，全部已实测）

| 类别 | 模型（`model_name`） | 状态 |
|---|---|---|
| 经典机器学习 | `lr_v1` 逻辑回归、`rf_v1` 随机森林、`xgb_v1` XGBoost、`nb_v1` 高斯朴素贝叶斯、`dt_v1` 决策树、`knn_v1` k 近邻 | ✅ 已实测 |
| 神经网络（深度学习） | `mlp_v1` 多层感知机（1 隐藏层）、`mlp_deep_v1` 深层 MLP（3 隐藏层 + 早停） | ✅ 已实测 |

> 课程「至少 2 类不少于 8 种」**已达标**（2 类 8 种）。来源：change `model-expansion`（PR #42），实测清单见 `data_model/pipelines/expert/reports/model_matrix.md`。
> **交付边界**：8 个模型**全部为评估用**；后端加载的交付模型与 `models/feature_order.txt` 的 `[models]` 段不变（specs/model-coverage R6），若要切换须另开「模型切换」提案，不静默改。

## 3. 指标口径（指针）

- 指标定义：Effort-unaware（AUC / Precision / Recall / F1）与 Effort-aware（`P_norm`、Recall@20% / @50%；`P_norm` 为本组自造归一化变体，与文献 `Popt` 非同一指标，不得对外宣称「标准 effort-aware 指标」）→ [`model-line-plan.md`](model-line-plan.md)。
- 实测数值（8 种 × 2 类 × 两类指标）→ `data_model/pipelines/expert/reports/model_matrix.md` 与同目录 `model_metrics.md`（两者逐项比对差异为 0）。
- 本文**不复制任何指标数值、超参与结论**；上述两处与本节不一致时，以 `model-line-plan.md` 与报告文件为准。

## 4. 覆盖矩阵入口（指针）

- 产出脚本 `08_model_matrix.py`；报告 `data_model/pipelines/expert/reports/model_matrix.md`（8 种 × 2 类 × 两类指标，与 `model_metrics.md` 的比对结论在该报告内）。
- 切分口径、样本量与超参 → `model-line-plan.md`；本文 §1 只保留铁规矩，数值不复制。
- 「每类最优」只用于说明各类都有可用模型，**不等于「该模型上线」**——上线走模型切换提案。
- 排序口径（`risk_score` 降序 → 风险密度降序）属契约变更提案，登记 Issue #37，**本包不改契约**。

## 5. 校准与阈值证据（指针）

- 脚本 `09_calibration_threshold.py`（时间序折 `TimeSeriesSplit`，禁随机 `KFold`）；报告 `data_model/pipelines/expert/reports/calibration_threshold.md`。
- 阈值语义与配额方案的结论 → `model-line-plan.md`；登记 Issue #38，本包不改契约。

## 6. 模型交付（指针）

- 权重目录、打包与校验方式 → `data_model/ENVIRONMENT.md` §7 与 `data_model/pipelines/expert/README.md`（权威正文在那里；本文不复述包名、清单与体积）。
- 特征顺序以 `feature-columns.md` 为准，不另发清单；`model_name` 与 `prediction.model_name` 及接口入参同名。
- 后端加载 `.pkl` 用 `joblib.load`（lr/rf 是 joblib 格式、xgb 是标准 pickle）。

## 7. 验收（指针）

- 复现一致性（模型线主验收）与契约一致性（单测落点：特征口径 → `data_model/tests/test_feature_contract.py`；模型加载与解释 → `backend/tests/test_model_registry.py`）的判据 → `model-line-plan.md`。
- 测试总纲、用例清单与退出准则见 `common/test-plan.md`。
