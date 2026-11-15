# et_v1

**极端随机树（Extra Trees） · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=et_v1` 返回指标与图集 |
| 定位 | expert 线**高精确率**选项（P=0.5212），适合宁可少报的场景 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 超参 | `n_estimators=300`、`min_samples_leaf=2`、`seed=42`（分裂阈值完全随机，方差低于随机森林） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/et_v1.pkl`，`joblib.load` 读取 |
| 依赖 | scikit-learn 1.9.1 |

## 性能（测试集 25,183 条）

AUC **0.8223** ｜ AP 0.4500 ｜ F1 0.3955 ｜ P 0.5212 ｜ R 0.3186 ｜ Acc 0.8599

## 局限

- 召回偏低（0.32），偏向保守判断
- 仅用结构化特征；fused 线 `et_fused_v1` 精确率相近但 F1 更低（0.1427）

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
