# tabnet_semantic_v1

**TabNet（深度表格） · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=tabnet_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线 **F1 最高**（0.2041）的模型 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 结构 | `TabNetWithEarlyStop`（基于 `pytorch_tabnet.TabNetClassifier`，带早停，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/tabnet_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | torch 2.14.1、pytorch_tabnet 4.1.0 |

## 性能（测试集 25,183 条）

AUC **0.7631** ｜ AP 0.2937 ｜ F1 0.2041 ｜ P 0.3387 ｜ R 0.1461 ｜ Acc 0.8362

## 局限

- 依赖最重（torch + pytorch_tabnet），反序列化环境缺失会失败
- 语义线整体上限低，F1 0.204 仍远低于 expert 线 0.44

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
