# 活跃 change 与撤回记录

`changes/<name>/` 是尚待实施或验收的增量，`specs/` 是当前活规格。目录仍在活跃区不等于功能已经完成；任务勾选也必须有可复核证据。格式见 [`../README.md`](../README.md)、[`../TASKS_TEMPLATE.md`](../TASKS_TEMPLATE.md) 和 [`../config.yaml`](../config.yaml)。产品现状从 [`../../docs/README.md`](../../docs/README.md) 进入。

## 当前活跃 change（10 份）

| change | 当前核对重点 |
|---|---|
| `backend-model-load-paths` | 验证模型目录和跨平台加载，补实机证据 |
| `feature-addons-sprint3` | 提交级归因、真实 diff 与修复参考；不得把新增行称为文件级 SHAP |
| `model-training-scope-8` | 三线各八分类器；旧环境文档与指标报告证据待重取 |
| `neon-test-baseline` | 测试记录与签字证据；未完成项保持未勾选 |
| `on-demand-commit-prediction` | 单提交现算与详情查询；按当前模型选择行为验收 |
| `online-eight-model-selection` | 八项清单存在，但 8/8 加载与逐模型性能需当前证据 |
| `public-dataset-quality` | 公开数据集仅作离线记录，不写已删除的 `commit_label` 表 |
| `semantic-feature-mainline` | 语义特征的实验、统计与文献证据待补；不改当前 expert 交付清单 |
| `single-commit-feature-extraction` | 单提交 14 维特征现算及异常场景 |
| `test-set-eval-figures` | 测试集指标、图集与五表数据口径 |

## 2026-11-14 撤回的旧提案（15 份）

旧提案的目录移至 `archive/2026-11-14-withdrawn-<name>/`，每份保留原文件并附 `WITHDRAWN.md`。这些提案**未作为已完成变更应用到活规格**，历史任务勾选不代表当前验收。原先旧四表、三模型、三页面、`runtime_setting`、PR 预测、旧自动评审等要求与当前产品形态冲突；若需要重新实施，应按现行口径另开 change。已有更早的归档保持历史原貌。

## 审核与归档

1. 在仓库根目录运行 `openspec validate --specs --strict`、`openspec validate --changes --strict`、`python openspec/check_structure.py`。CLI 语法通过不等于功能验收通过。
2. 逐条核对 Requirement、现行代码、文档、测试结果和证据路径。旧证据文件若已删除，必须重新取证或明确撤回任务勾选。
3. 只有增量已实施、对应活规格可正确合入且测试证据可复现时才正常归档。范围取消或被新设计取代的 change 留撤回记录，**不得套用旧 delta 覆盖活规格**。
4. 任务分工和进度以飞书看板为准；仓库 `todo/` 是临时拆解与历史线索。旧任务要求见 [`../../todo/sober-2-OpenSpec归档.md`](../../todo/sober-2-OpenSpec归档.md)。
