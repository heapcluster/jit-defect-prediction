# svm_semantic_v1

**RBF 核支持向量机 · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=svm_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**核方法对照**，AUC 为全线最低 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 管道 | `StandardScaler → SVC(RBF)`（必须先标准化） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/svm_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.6538** ｜ AP 0.2569 ｜ F1 0.1521 ｜ P 0.3538 ｜ R 0.0969 ｜ Acc 0.8447

## 局限

- **AUC 0.6538 为全部 25 个模型最低**，768 维下 RBF 核距离度量失效
- 训练与推理成本随样本量增长快于树模型

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
