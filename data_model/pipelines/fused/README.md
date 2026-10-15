# 融合 pipeline 包 · 产出归属

> 负责人：蒋励 ｜ 线名 `fused` ｜ 状态：**⬜ 计划态（脚本未落地）**
> 方案与口径：`docs/model/pipelines/fused.md`（权威，本文不重复其内容）

## 1. 这个包是干什么的

承载**融合**这一条 pipeline 的训练与产出：专家 14 维左连接语义 768 维 = 782 维样本集，
喂给与另两条线完全相同的 8 个分类器，检验「专家度量 + 预训练语义」混合是否优于任何单边。

## 2. 目录结构与产出归属（计划）

```
data_model/pipelines/fused/
├── __init__.py     线名与产出路径常量
├── README.md       本文件
├── data/           融合样本集（本线私有）
├── models/         {model}_fused_v1.pkl（仅评估，不进交付链）
└── reports/        model_metrics_fused.md / model_matrix_fused.md /
                    feature_ablation_fused.md
```

| 产物 | 路径 | 归属 | 入库？ |
|---|---|---|---|
| 融合样本集 | `data/dataset_fused_v2.csv`（782 维，左连接） | **仅本线** | ❌ |
| 模型文件 | `models/{model}_fused_v1.pkl` | **仅本线** | ❌ |
| 指标 / 矩阵 / 消融 | `reports/model_metrics_fused.md`、`model_matrix_fused.md`、`feature_ablation_fused.md` | **仅本线** | ✅ |
| 三线对比汇总 | `reports/three_way_comparison.md`（历史沿用名） | 三线共一份，由 `14_compare_settings.py` 统一产出 | ✅ |

## 3. 约定

1. **报告名一律带 `_fused` 后缀**，不得落到 expert 线的旧名上 —— 四线同名即互相覆盖。
2. **左表 / 右表 / 切分下标都是共享产物**（专家样本集、语义向量、`split_szz_*.csv`），
   放 `data_model/data/`；本线只做连接与训练，不重新提特征、不重新切分。
3. **前 14 列与契约二逐字一致**，语义 768 列追加在后；缺失向量显式标注、不填 0。
4. **同切分下标**：与 expert / semantic 两线共用同一份切分文件，重新切分 = 打回重切（Gate G3）。

## 4. 变更日志

| 日期 | 变更 |
|---|---|
| 2026-10-14 | 建包（计划态）：定产出归属与路径常量，脚本待 `semantic-feature-mainline` change 落地 |
