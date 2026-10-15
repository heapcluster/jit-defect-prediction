# 端到端 pipeline 包 · 产出归属

> 负责人：蒋励 ｜ 线名 `e2e` ｜ 状态：**⬜ 计划态 · 尚未立项**
> 方案与口径：`docs/model/pipelines/end-to-end.md`（权威，本文不重复其内容）

## 1. 这个包是干什么的

承载**端到端**这一条 pipeline 的训练与产出：不冻结 backbone，直接在 commit 变更文本上
fine-tune CodeBERT / GraphCodeBERT，特征提取与分类联合优化。它是四类对比里的「一段式」组，
与另三条「两段式」pipeline 形态不同，结论必须单独报。

## 2. 目录结构与产出归属（计划）

```
data_model/pipelines/e2e/
├── __init__.py     线名与产出路径常量
├── README.md       本文件
├── data/           端到端数据集（本线私有）
├── models/         codebert_e2e_v1.pkl（仅评估，不进交付链）
└── reports/        end_to_end.md
```

| 产物 | 路径 | 归属 | 入库？ |
|---|---|---|---|
| 端到端数据集 | `data/e2e_dataset_v2.csv` | **仅本线** | ❌ |
| 模型文件 | `models/codebert_e2e_v1.pkl` | **仅本线** | ❌ |
| 评估报告 | `reports/end_to_end.md` | **仅本线** | ✅ |
| 对比结论 | 作为第四类**另附**于 `reports/three_way_comparison.md` | 不并进前三类同一张表 | ✅ |

## 3. 约定

1. **产物名一律带 `e2e` 线名**，不得落到 expert 线的旧名上 —— 四线同名即互相覆盖。
2. **共享上游产物不按线分**：变更文本（复用 `10_semantic_text.py` 产物）、标签、切分下标
   在 `data_model/data/`；本线**不吃**特征向量，也不重新切分。
3. **未立项不写码**：脚本（`17_*`）落地前必须已有 openspec change，并同步更新模型线方案中
   端到端的形态说明（D10 口径）。
4. **不得静默切换交付模型**：若端到端更优，另开「模型切换」提案走契约三变更流程。

## 4. 变更日志

| 日期 | 变更 |
|---|---|
| 2026-10-14 | 建包（计划态 · 未立项）：定产出归属与路径常量 |
