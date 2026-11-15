# lr_fused_v1

**逻辑回归 · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lr_fused_v1` 返回指标与图集 |
| 定位 | fused 线**线性基线**，验证融合是否带来线性可分的增益 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 管道 | `StandardScaler → LogisticRegression`（Pipeline） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lr_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8134** ｜ AP 0.3998 ｜ F1 0.3508 ｜ P 0.4586 ｜ R 0.2841 ｜ Acc 0.8488

## 局限

- 融合后仍弱于 expert 同算法（0.8134 vs 0.8020 略升，但 F1 相近），语义增益有限
- 召回 0.284，固定阈值下漏报偏多

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
