# rf_v1

**随机森林 · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=rf_v1` 返回指标与图集 |
| 定位 | expert 线**装袋树基线**，参数按 SHAP 可算性收敛（见 `model.py` 注释） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 超参 | `n_estimators=300`、`min_samples_leaf=100`、`max_depth=15`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/rf_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8169** ｜ AP 0.4274 ｜ F1 0.3659 ｜ P 0.5321 ｜ R 0.2789 ｜ Acc 0.8610

## 局限

- 为压 SHAP 计算量把 `min_samples_leaf` 放大到 100、`max_depth` 限到 15，拟合能力弱于 `xgb_v1`/`lgbm_v1`
- 召回偏低（0.28），固定 0.5 阈值下漏报较多

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
