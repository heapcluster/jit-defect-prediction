# openspec 规格中 data_model 旧路径引用修订

> Sprint 2 收尾 ｜ 起草 2026-10-16 ｜ 起草人 蒋励（模型线负责人）
> 触发：周报-20261009「本周计划」row=20（openspec/specs 与 archive 中旧路径修订）
> 关联：`refactor/model-package-structure`（PR #71，data_model 四线分包迁移）

## Why

`data_model/` 已按「每条模型线独立成包」重构（PR #71）：01–05 共享数据流水线迁至
`preparation/`，训练链路由 `pipelines/expert/` 接管，根目录 06–09 / 16 已删除，
报告按归属迁入 `preparation/reports/` 与 `pipelines/expert/reports/`。

但 openspec 规格与三个进行中的 change 仍引用**旧路径**（`data_model/06_train_model.py`、
`data_model/reports/`、`07_predict_all.py` 等）。规格与代码不一致是课程判定的一票否决
缺陷，本 change 把这些引用修订到新口径，**只改路径引用，不改任何规格语义**（阈值、判定
条件、交付边界逐字不动）。

## What Changes

- 修订 5 个能力规格中的路径引用（MODIFIED delta，逐字替换路径片段）：
  - `commit-collection`：`data_model/reports/` → `data_model/preparation/reports/`
  - `labeled-dataset`：同上
  - `feature-extraction`：同上
  - `model-training`：`data_model/reports/` → `data_model/pipelines/expert/reports/`
  - `model-coverage`：登记报告路径同上；交付清单 `models/feature_order.txt` →
    `data_model/pipelines/expert/models/feature_order.txt`；`07_predict_all.py` →
    `python -m pipelines.expert.predict`
- 同步修订三个进行中 change 的路径引用（散文与任务项）：
  `semantic-feature-mainline`、`public-dataset-quality`、`feature-addons-sprint3`
- `openspec/changes/archive/` **不动**：archive 是历史快照（记录当时的真实路径与
  交付状态），改写历史留痕比保留旧引用危害更大。归档文档随其 change 冻结。

## Impact

- Affected specs: `commit-collection`、`labeled-dataset`、`feature-extraction`、
  `model-training`、`model-coverage`
- Affected code: 无（纯文档/规格路径修订）
- 冻结件（`feature-columns.md` 契约二 v1.2、`api-spec.md` 契约三）不在本 change 范围
