# lr_v1

**逻辑回归 · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lr_v1` 返回指标与图集 |
| 定位 | expert 线**线性基线**，可解释性最强（SHAP 线性解释器） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 管道 | `StandardScaler → LogisticRegression`（Pipeline；取系数须走 `model.named_steps["lr"].coef_`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lr_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8020** ｜ AP 0.4051 ｜ F1 0.3497 ｜ P 0.5303 ｜ R 0.2609 ｜ Acc 0.8605

## 局限

- 线性模型拟合能力有限，AUC 为 expert 线最低档（0.80）
- 召回偏低（0.26），高阈值下漏报较多

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
