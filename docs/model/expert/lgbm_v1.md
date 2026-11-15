# lgbm_v1

**LightGBM · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lgbm_v1` 返回指标与图集 |
| 定位 | expert 线 **F1 最优**的树模型（0.4337），与 `xgb_v1` 互为对照 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`num_leaves=31`、`subsample=0.9`、`subsample_freq=1`（行采样必须配 freq 才生效）、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lgbm_v1.pkl`，`joblib.load` 读取 |
| 依赖 | lightgbm 4.6.0、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8260** ｜ AP 0.4549 ｜ F1 0.4337 ｜ P 0.4510 ｜ R 0.4177 ｜ Acc 0.8431

## 局限

- 精确率偏低（0.45），高召回伴随较多误报
- 仅用结构化特征；fused 线 `lgbm_fused_v1` 同算法 AUC 更高（0.8395）

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
