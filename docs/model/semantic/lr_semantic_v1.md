# lr_semantic_v1

**逻辑回归 · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=lr_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**线性基线**，验证语义向量是否线性可分 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 管道 | `StandardScaler → LogisticRegression`（Pipeline） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/lr_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7551** ｜ AP 0.2708 ｜ F1 0.1449 ｜ P 0.2798 ｜ R 0.0977 ｜ Acc 0.8341

## 局限

- **F1 仅 0.145、召回 0.098**，768 维高维稀疏下线性模型几乎无法区分缺陷
- 整体弱于 expert 线同算法（0.8020），说明纯语义信号不如结构化特征

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
