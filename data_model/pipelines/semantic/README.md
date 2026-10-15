# 仅语义 pipeline 包 · 产出归属

> 负责人：蒋励 ｜ 线名 `semantic` ｜ 状态：**⬜ 计划态（脚本未落地）**
> 方案与口径：`docs/model/pipelines/semantic-only.md`（权威，本文不重复其内容）

## 1. 这个包是干什么的

承载**仅语义**这一条 pipeline 的训练与产出：冻结的 CodeBERT / GraphCodeBERT 把变更文本
编码为 768 维向量（`feature_version = v2`），喂给与基线相同的 8 个分类器，检验
「预训练语义特征优于专家度量」的课程主线假设。

## 2. 目录结构与产出归属（计划）

```
data_model/pipelines/semantic/
├── __init__.py     线名与产出路径常量
├── README.md       本文件
├── data/           变更文本 / 语义向量 / 样本集（本线私有）
├── models/         {model}_semantic_v1.pkl（仅评估，不进交付链）
└── reports/        model_metrics_semantic.md / model_matrix_semantic.md /
                    feature_ablation_semantic.md
```

| 产物 | 路径 | 归属 | 入库？ |
|---|---|---|---|
| 变更文本 | `data/semantic_text_v2.csv` | **仅本线**（端到端线可复用同一份） | ❌ |
| 语义向量 | `data/semantic_codebert_v2.csv`（`sem_0…sem_767`） | **仅本线**（融合线的右表） | ❌ |
| 样本集 | `data/dataset_semantic_v2.csv` | **仅本线** | ❌ |
| 模型文件 | `models/{model}_semantic_v1.pkl` | **仅本线** | ❌ |
| 指标 / 矩阵 / 消融 | `reports/model_metrics_semantic.md`、`model_matrix_semantic.md`、`feature_ablation_semantic.md` | **仅本线** | ✅ |
| 三线对比汇总 | `reports/three_way_comparison.md`（历史沿用名） | 三线共一份，由 `14_compare_settings.py` 统一产出 | ✅ |

## 3. 约定

1. **报告名一律带 `_semantic` 后缀**，不得落到 expert 线的旧名（`model_metrics.md` 等）上 —— 四线同名即互相覆盖。
2. **共享上游产物不按线分**：仓库副本、提交清单、标签、切分下标在 `data_model/data/`，四线共用。
3. **训练实现不复制**：8 模型框架复用 `06_train_model.py` 的 `model_registry` 插件化机制，不新造模型类；本包只做驱动与产出归属。
4. **v2 不入库、不进交付链**；契约二既有 14 项列名与顺序一字不动。

## 4. 变更日志

| 日期 | 变更 |
|---|---|
| 2026-10-14 | 建包（计划态）：定产出归属与路径常量，脚本待 `semantic-feature-mainline` change 落地 |
