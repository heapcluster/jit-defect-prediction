# et_semantic_v1

**极端随机树（Extra Trees） · semantic 线 · 在线交付**

用代码语义向量（768 维）预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=et_semantic_v1` 返回指标与图集 |
| 定位 | semantic 线**精确率最高**（0.4150），但当前在线推理受限（见局限） |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 768 维代码语义向量（CodeBERT embedding） |
| 超参 | `n_estimators=300`、`min_samples_leaf=2`、`seed=42` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/et_semantic_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.7564** ｜ AP 0.2863 ｜ F1 0.0726 ｜ P 0.4150 ｜ R 0.0398 ｜ Acc 0.8538

## 局限

- **在线推理当前返回 40001**（`该提交暂无预计算语义向量`）：语义向量产物未按现行 pipelines 布局生成，见 [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)
- 召回仅 0.040，F1 0.073，指标上不适合单独使用

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
