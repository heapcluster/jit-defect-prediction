# xgb_v1

**XGBoost · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score`，决定风险等级与列表排序 |
| 展示 | `/api/figures?model_name=xgb_v1` 返回指标与图集；前端「模型性能看板」可选中 |
| 定位 | expert 线 8 个模型中 AUC 第二，作为树模型基线对照 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 超参 | `n_estimators=300`、`learning_rate=0.1`、`max_depth=6`、`subsample=0.9`、`colsample_bytree=0.9`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/xgb_v1.pkl`，`joblib.load` 读取 |
| 依赖 | xgboost 3.4.1、scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8281** ｜ AP 0.4591 ｜ F1 0.4316 ｜ P 0.4587 ｜ R 0.4075 ｜ Acc 0.8456

## 局限

- 正样本仅 14.38%，固定 0.5 阈值下 F1 偏低（0.43）
- 仅用结构化特征，无语义/文本信息；fused 线 `xgb_fused_v1` 同算法 AUC 更高（0.8342）

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
