# 模型训练与评估（8 种 / 2 类 / 两类指标）

> 负责人：蒋励 ｜ 关联 change：`model-training-and-delivery`、`model-expansion`
> 课程硬要求：「至少 2 类（经典机器学习和深度学习）不少于 8 种预测模型、Effort-unware 和 effort-aware 两类、训练集和测试集划分」。

## 1. 切分铁规矩

- **按 `committed_at` 时间序切分，前 70% 训练 / 后 30% 测试，禁止随机切分**（EXP/NUC 等时间相关特征，随机=提前看未来，准确率假的）。
- 写进 `AGENTS.md` 硬红线；`train_test_split(shuffle=True)` 或未指定 `shuffle=False` = 缺陷，必须打回。

## 2. 8 种模型（总量不减，分期交付）

| 类别 | 模型 | 状态 |
|---|---|---|
| 经典机器学习 | 逻辑回归 lr、随机森林 rf、XGBoost xgb、朴素贝叶斯 nb、决策树 dt、KNN knn | 2–3 个先跑通链路（lr/rf/xgb），其余后置 |
| 深度学习 | MLP mlp、深层 MLP mlp_deep | 后置（需 GPU/更大批量） |

> ⚠️ 课程原文明确要求「至少 2 类不少于 8 种」，**不是可选项**，口径是「什么时候做完」不是「做不做」。深度学习仍要实现，只是排在经典模型之后。

## 3. 两类评估指标（都要报）

| 类型 | 指标 | 说明 |
|---|---|---|
| Effort-unaware | AUC / Precision / Recall / F1 | 不计审查成本 |
| Effort-aware | Popt、IFA、Effort@20% 等 | 按审查精力算性价比（Cost-aware） |

只报一类不足以说明问题；⑧ 覆盖矩阵报告须与 ⑥ `model_metrics.md` 逐项比对**差异为 0**。

## 4. 覆盖矩阵（change `model-expansion`）

- `08_model_matrix.py`：8 种 × 2 类 × 两类指标，产出 `reports/model_matrix.md`。
- 口径：⑧ **不重新切分、不改特征**，只读 ⑥ 切分文件；报告写明「与 `model_metrics.md` 差异项数（必须为 0）」。

## 5. 校准与阈值证据（⑨）

- `09_calibration_threshold.py`：时间序折（`TimeSeriesSplit`，禁随机 `KFold`）校准；固定阈值 vs 工作量配额（LOC 与改动文件数各一版）的等工作量对照。
- ⑨ 只出证据、不改契约；两种策略对照必须同工作量口径。

## 6. 模型交付（跨线 A+C）

- 模型文件放 `data_model/models/`（`.gitignore` 排除，走打包交付）。
- 特征顺序以 `feature-columns.md` 为准，不另发清单；`model_name` 与 `prediction.model_name` 及接口入参同名。
- 后端加载 `.pkl` 用 `joblib.load`（lr/rf 是 joblib 格式、xgb 是标准 pickle）。

## 7. 验收（可复现优先于单测）

别人照 §5 复现命令跑出同一份统计（±0）、指标报告逐行一致、两类指标齐全 = 通过。
