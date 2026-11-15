# lgbm_semantic_v1

**LightGBM · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lgbm_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线 **AUC 最高**的树模型（0.7615） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`num_leaves=31`、`subsample=0.9`、`subsample_freq=1`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lgbm_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | lightgbm 4.6.0、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7615** ｜ AP 0.2804 ｜ F1 0.1566 ｜ P 0.3084 ｜ R 0.1049 ｜ Acc 0.8374

## 局限

- 语义线整体天花板低：AUC 0.76、F1 0.157，明显弱于 expert 线（0.8281 / 0.4337）
- 召回仅 0.105，实际使用需下调阈值

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
