# codebert_e2e_v1

**CodeBERT（端到端） · e2e 线 · 在线交付**

直接以提交的代码文本为输入（不做人工特征工程），预测一次提交引入缺陷的概率（0–1）。

## 在项目中的作用

| 环节 | 说明 |
|---|---|
| 注册 | `feature_order.txt` 的 `[models]` 之一，后端启动时按清单加载 |
| 推理 | `/api/predict`、`/api/sync` 用它产出 `risk_score` |
| 展示 | `/api/figures?model_name=codebert_e2e_v1` 返回指标与图集 |
| 定位 | 全项目**唯一端到端模型**，用于验证「免特征工程」路线是否可行 |

## 关键信息

| 项 | 值 |
|---|---|
| 输入 | 提交代码文本（CodeBERT 编码，非 14 维结构化特征） |
| 结构 | `build_model(text_model)`，见 `pipelines/e2e/model.py` |
| 判定 | `risk_score ≥ 0.5` 高风险，`≥ 0.2` 中风险 |
| 产物 | `models/codebert_e2e_v1.pkl`，`joblib.load` 读取 |
| 依赖 | torch 2.14.1、transformers（CodeBERT 权重另行取得，不入库） |

## 性能（测试集 25,183 条）

AUC **0.7553** ｜ AP 0.2722 ｜ F1 0.1125 ｜ P 0.3155 ｜ R 0.0685 ｜ Acc 0.8447

## 局限

- **F1 仅 0.113、召回 0.069**，端到端路线在当前数据规模下明显不如结构化特征（expert 线 0.43 F1）
- 不产出 `feat_importance` 图（无 14 维可解释列），只有 5 张图
- 依赖 CodeBERT 权重与 torch，环境最重

---

指标来源 `data_model/evaluation/out/model_metrics.csv`（基线 `afdee84`）· `[AI生成]` 待人工复核
