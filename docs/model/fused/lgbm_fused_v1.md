# lgbm_fused_v1

**LightGBM · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lgbm_fused_v1` 返回指标与图集 |
| 定位 | **全部 25 个模型中 AUC 最高**（0.8395） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`num_leaves=31`、`subsample=0.9`、`subsample_freq=1`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lgbm_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | lightgbm 4.6.0、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8395** ｜ AP 0.4663 ｜ F1 0.4316 ｜ P 0.4962 ｜ R 0.3818 ｜ Acc 0.8553

## 局限

- 仍是 **AUC 视角最优、F1 非最优**（F1 0.4316 与 `xgb_v1` 持平）
- 依赖语义向量产物；纯结构化场景应回退到 expert 线

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
