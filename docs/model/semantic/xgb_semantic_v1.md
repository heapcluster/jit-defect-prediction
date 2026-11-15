# xgb_semantic_v1

**XGBoost · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=xgb_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**梯度提升对照**，AUC 与 `lgbm_semantic_v1` 接近 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`max_depth=6`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/xgb_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | xgboost 3.4.1、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7605** ｜ AP 0.2831 ｜ F1 0.1683 ｜ P 0.3212 ｜ R 0.1140 ｜ Acc 0.8379

## 局限

- F1 仅 0.168、召回 0.114，语义特征对缺陷的判别力有限
- 比 expert 线同算法低 0.068 AUC（0.7605 vs 0.8281）

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
