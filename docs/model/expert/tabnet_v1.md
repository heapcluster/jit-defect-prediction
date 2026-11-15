# tabnet_v1

**TabNet（深度表格） · expert 线 · 在线交付**

用 Kamei 14 维结构化特征，预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=tabnet_v1` 返回指标与图集 |
| 定位 | expert 线 **AUC 最高**（0.8294）且 F1 最高（0.4437）的模型 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 14 维：`ns, nd, nf, entropy, la, ld, lt, fix, ndev, age, nuc, exp, rexp, sexp` |
| 结构 | `TabNetWithEarlyStop`（基于 `pytorch_tabnet.TabNetClassifier`，带早停，`seed=42`） |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/tabnet_v1.pkl`，`joblib.load` 读取 |
| 依赖 | torch 2.14.1、pytorch_tabnet 4.1.0 |

## 性能（测试集 25,183 条）

AUC **0.8294** ｜ AP 0.4535 ｜ F1 0.4437 ｜ P 0.4617 ｜ R 0.4271 ｜ Acc 0.8460

## 局限

- **依赖最重**（torch + pytorch_tabnet），反序列化环境缺失会直接失败
- 推理延迟与内存开销高于树模型；与 `mlp_deep_v1` 同属「非逐字节可复现」一类

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
