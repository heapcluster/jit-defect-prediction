# 模型训练与评估（8 种 / 2 类 / 两类指标）

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

> 课程「至少 2 类不少于 8 种」**已达标**（2 类 8 种）。来源：change `model-expansion`（PR #42），实测清单见 `data_model/reports/model_matrix.md`。
> **交付边界**：8 个模型**全部为评估用**；后端加载的交付模型与 `models/feature_order.txt` 的 `[models]` 段不变（specs/model-coverage R6），若要切换须另开「模型切换」提案，不静默改。

## 3. 两类评估指标（都要报）

| 类型 | 指标 | 说明 |
|---|---|---|
| Effort-unaware | AUC / Precision / Recall / F1（/ Accuracy） | 不计审查成本，衡量整体判别力 |
| Effort-aware | `P_norm`、Recall@20% / @50% | 以审查工作量为权重，衡量「优先审高风险提交」的收益 |

只报一类不足以说明问题；覆盖矩阵报告须与 `model_metrics.md` 逐项比对**差异为 0**。

## 4. 覆盖矩阵（change `model-expansion`，实测）

`08_model_matrix.py` 产出 `reports/model_matrix.md`：8 种 × 2 类 × 两类指标；**不重新切分、不改特征**，只读 ⑥ 切分文件（训练 7625 / 检验 3268，种子 42），与 `model_metrics.md` 逐项比对**差异 0 项**。

**Effort-unaware（检验集）**：

| 类别 | 模型 | AUC | F1 | Precision | Recall | Accuracy |
|---|---|---|---|---|---|---|
| 神经网络（深度学习） | `mlp_v1`（1 隐藏层） | 0.7300 | 0.3998 | 0.2877 | 0.6549 | 0.6775 |
| 神经网络（深度学习） | `mlp_deep_v1`（3 隐藏层 + 早停）⭐ | 0.7454 | 0.3955 | 0.2976 | 0.5896 | 0.7044 |
| 经典机器学习 | `lr_v1`（逻辑回归） | 0.6407 | 0.3265 | 0.2269 | 0.5821 | 0.6062 |
| 经典机器学习 | `rf_v1`（随机森林）⭐ | 0.7463 | 0.4195 | 0.3046 | 0.6735 | 0.6943 |
| 经典机器学习 | `xgb_v1`（XGBoost） | 0.7397 | 0.4133 | 0.2964 | 0.6828 | 0.6821 |
| 经典机器学习 | `nb_v1`（高斯朴素贝叶斯） | 0.6573 | 0.3343 | 0.2654 | 0.4515 | 0.7050 |
| 经典机器学习 | `dt_v1`（决策树） | 0.7005 | 0.3898 | 0.2680 | 0.7146 | 0.6331 |
| 经典机器学习 | `knn_v1`（k 近邻） | 0.6864 | 0.3507 | 0.2558 | 0.5578 | 0.6613 |

> ⭐ = 类别内 AUC 最优。「每类最优」只用于说明各类都有可用模型，**不等于「该模型上线」**（后者走模型切换提案）。

**Effort-aware（工作量代理 = LOC 改动行数 la+ld，排序按契约三 `risk_score` 降序）**：三个经典模型的 `P_norm` 为 **-0.67 / -0.25 / -0.42**（不如随机基线），改按「`risk_score` ÷ 工作量」降序后升至 **0.79 / 0.81 / 0.80**（`model_metrics.md`）；另一次实跑 `calibration_threshold.md` 给出**同工作量预算**下召回 **+31.72 pp**（LOC）/ **+22.01 pp**（文件数）的对照。

> 结论指向**契约变更提案**：排序口径由「`risk_score` 降序」改为「风险密度降序」；**本包不改契约**（登记 Issue #37）。
> ⚠️ 神经网络收敛登记（如实记录，不静默当已收敛）：`mlp` 迭代上限 500 未达收敛判据、`mlp_deep` 40 轮收敛 —— 指标按实际训练结果登记，不重跑调参。

## 5. 校准与阈值证据（⑨）

- `09_calibration_threshold.py`：时间序折（`TimeSeriesSplit`，禁随机 `KFold`）校准；固定阈值 vs 工作量配额（LOC 与改动文件数各一版）的等工作量对照。
- ⑨ 只出证据、不改契约；两种策略对照必须同工作量口径。
- 实测结论：`p >= 0.50` 的真实缺陷率仅 **29.6%**（Isotonic 校准后 29.1%，差 -0.5 pp）→「把阈值校准到 50% 语义」在时间序切分下走不通（Issue #38），建议转向「配额取前 N%」。

## 6. 模型交付（跨线 A+C）

- 模型文件放 `data_model/models/`（`.gitignore` 排除，走打包交付）。
- 特征顺序以 `feature-columns.md` 为准，不另发清单；`model_name` 与 `prediction.model_name` 及接口入参同名。
- 后端加载 `.pkl` 用 `joblib.load`（lr/rf 是 joblib 格式、xgb 是标准 pickle）。

## 7. 验收（复现一致性 + 契约一致性双轨）

- **复现一致性（模型线主验收）**：别人照 §5 复现命令跑出同一份统计（±0）、指标报告逐行一致、两类指标齐全。
- **契约一致性（单测）**：模型线的单测**不在本包重造**，按职责落在两处：
  - 特征口径（14 项列名与顺序）→ `data_model/tests/test_feature_contract.py`（T-MO-01：把契约文档 / 实现 `FEATURE_FIELDS` / 后端装配 `FEATURE_COLUMNS` / 交付清单 `feature_order.txt` 四处钉在同一份有序清单上）；
  - 模型加载与解释（`joblib.load`、特征数自检、SHAP 键名可回溯）→ `backend/tests/test_model_registry.py`（T-MO-02 / T-MO-03）。
- 测试总纲、用例清单与退出准则见 `common/test-plan.md`。
