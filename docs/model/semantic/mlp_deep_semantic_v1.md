# mlp_deep_semantic_v1

**多层感知机（3 隐藏层 + 早停） · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=mlp_deep_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线 **AUC 最高**（0.7644）且 F1 次高（0.1879）的模型 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 结构 | 3 隐藏层 64/32/16 + 早停（`MLPClassifier`，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/mlp_deep_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7644** ｜ AP 0.3001 ｜ F1 0.1879 ｜ P 0.3677 ｜ R 0.1262 ｜ Acc 0.8431

## 局限

- 非「逐字节可复现」一类（浮点求和顺序不保证一致）
- 即使为 semantic 线最优，F1 仅 0.188，仍不足以单独支撑缺陷判定

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
