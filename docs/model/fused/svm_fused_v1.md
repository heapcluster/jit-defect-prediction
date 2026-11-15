# svm_fused_v1

**RBF 核支持向量机 · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=svm_fused_v1` 返回指标与图集 |
| 定位 | fused 线**核方法对照**，AUC 明显低于同线树模型 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 管道 | `StandardScaler → SVC(RBF)` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/svm_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7540** ｜ AP 0.3926 ｜ F1 0.3531 ｜ P 0.4796 ｜ R 0.2794 ｜ Acc 0.8528

## 局限

- AUC 0.7540，融合后反而低于 expert 同算法（0.7096 → 0.7540 略升但仍属低位）
- 高维距离度量仍不稳定

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
