# mlp_deep_fused_v1

**多层感知机（3 隐藏层 + 早停） · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=mlp_deep_fused_v1` 返回指标与图集 |
| 定位 | fused 线**深度学习对照**，表现中游 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 结构 | 3 隐藏层 64/32/16 + 早停（`MLPClassifier`，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/mlp_deep_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8053** ｜ AP 0.3943 ｜ F1 0.3641 ｜ P 0.4438 ｜ R 0.3087 ｜ Acc 0.8449

## 局限

- 非「逐字节可复现」一类
- AUC 低于 expert 同算法（0.8053 vs 0.8254），融合未带来增益

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
