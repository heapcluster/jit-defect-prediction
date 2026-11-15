# svm_v1

**RBF 核支持向量机 · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=svm_v1` 返回指标与图集 |
| 定位 | expert 线**核方法对照**，Accuracy 最高但 AUC 最低，用于说明「准确率会骗人」 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 管道 | `StandardScaler → SVC(RBF)`（RBF 按距离度量，必须先标准化） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险；概率经 `predict_proba` 校准 |
| 产物 | `models/svm_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7096** ｜ AP 0.4179 ｜ F1 0.4078 ｜ P 0.5464 ｜ R 0.3252 ｜ Acc 0.8641

## 局限

- **AUC 仅 0.71**，排序能力明显弱于树模型；Accuracy 0.8641 高是因为偏向多数类（负样本 85.6%）
- 样本量增大后训练/推理成本高于树模型

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
