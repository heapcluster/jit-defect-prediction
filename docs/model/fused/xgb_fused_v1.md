# xgb_fused_v1

**XGBoost · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=xgb_fused_v1` 返回指标与图集 |
| 定位 | fused 线**梯度提升**，AUC 0.8342，仅次于 `lgbm_fused_v1` |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`max_depth=6`、`subsample=0.9`、`colsample_bytree=0.9`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/xgb_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | xgboost 3.4.1、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8342** ｜ AP 0.4591 ｜ F1 0.4187 ｜ P 0.4895 ｜ R 0.3658 ｜ Acc 0.8539

## 局限

- 融合收益有限：比 expert 同算法高 0.006 AUC（0.8342 vs 0.8281）
- 语义向量缺失时该模型不可用（依赖 `semantic_embeddings` 产物）

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
