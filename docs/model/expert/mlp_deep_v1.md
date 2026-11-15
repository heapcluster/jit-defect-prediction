# mlp_deep_v1

**多层感知机（3 隐藏层 + 早停） · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=mlp_deep_v1` 返回指标与图集 |
| 定位 | expert 线**深度学习对照**（与 `tabnet_v1` 同属神经网络类） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 结构 | 3 隐藏层 64/32/16 + 早停（`MLPClassifier`，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/mlp_deep_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8254** ｜ AP 0.4497 ｜ F1 0.4084 ｜ P 0.5116 ｜ R 0.3399 ｜ Acc 0.8584

## 局限

- **不属于「同一命令连跑两次逐字节一致」那一类**（内部切分与浮点求和顺序不保证一致），复现核对比对只认 lr/rf/xgb/lgbm/et/svm
- 仅用结构化特征，14 维输入对深层网络的表达空间有限

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
