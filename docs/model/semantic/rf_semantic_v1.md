# rf_semantic_v1

**随机森林 · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=rf_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**装袋树对照**，精确率偏高、召积极低 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 超参 | `n_estimators=300`、`min_samples_leaf=2`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/rf_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7522** ｜ AP 0.2828 ｜ F1 0.0694 ｜ P 0.3629 ｜ R 0.0384 ｜ Acc 0.8520

## 局限

- **召回仅 0.038**，几乎不报缺陷；F1 0.069 为全线最低
- 高维语义特征下树模型难以找到有效分裂点

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
