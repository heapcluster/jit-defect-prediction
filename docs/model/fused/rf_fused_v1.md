# rf_fused_v1

**随机森林 · fused 线 · 在线交付**

用「14 维结构化 + 768 维语义」融合特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=rf_fused_v1` 返回指标与图集 |
| 定位 | fused 线**高精确率**选项（P=0.5557 全线最高） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维结构化 + 768 维语义向量 |
| 超参 | `n_estimators=300`、`min_samples_leaf=2`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/rf_fused_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8155** ｜ AP 0.3992 ｜ F1 0.2136 ｜ P 0.5557 ｜ R 0.1322 ｜ Acc 0.8600

## 局限

- 召回仅 0.132，F1 0.214，过度保守
- 精确率高但漏报多，不适合作为唯一判据

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
