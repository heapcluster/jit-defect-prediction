# OpenSpec 归档核对表

> 核对基线：`main` 的 `7edcfb9`（2026-11-16）。本表记录仓库内可查到的任务和证据；飞书看板仍是负责人、排期和进度的权威。

**结论：本轮没有可正常归档的活跃 change。** 10 份 change 均有未完成任务或验收缺口。已有 29 份历史归档继续保留；其中标注 `WITHDRAWN.md` 的旧提案是**撤回**，不代表实施完成，也不应用其规格增量。

| 活跃 change | 已勾选 / 总任务 | 归档前还需完成 | 主要负责人 |
| --- | ---: | --- | --- |
| [`backend-model-load-paths`](backend-model-load-paths/tasks.md) | 8 / 11 | 复核 TabNet 权重导出；补真实 MySQL、模型 API 与跨线裁定证据。 | 吕建江 |
| [`feature-addons-sprint3`](feature-addons-sprint3/tasks.md) | 5 / 9 | 核实真实 diff、修复参考和四页联调；补可打开的通过与降级证据。 | 蒋励统稿，前后端协作 |
| [`model-training-scope-8`](model-training-scope-8/tasks.md) | 13 / 18 | 重建现行环境和报告证据，按八分类器重训并核对指标。 | 蒋励 |
| [`neon-test-baseline`](neon-test-baseline/tasks.md) | 20 / 24 | 完成现场 Scenario 判定、四份测试文档人工复核签字和 PR 审阅链接。 | neon |
| [`on-demand-commit-prediction`](on-demand-commit-prediction/tasks.md) | 3 / 5 | 用真实 Camel 仓库和权重完成 HTTP 演示、时延测量及证据归档。 | 吕建江，苏哲勋联调 |
| [`online-eight-model-selection`](online-eight-model-selection/tasks.md) | 4 / 9 | 核实八项交付清单、8/8 加载和逐模型 100 次压测，并完成非作者验收。 | 苏哲勋协调，模型与后端线交付 |
| [`public-dataset-quality`](public-dataset-quality/tasks.md) | 0 / 24 | 完成数据源核验、加载器、质量报告和范围文档；当前没有可归档的实现证据。 | 蒋励 |
| [`semantic-feature-mainline`](semantic-feature-mainline/tasks.md) | 1 / 40 | 完成语义特征、三类对比、消融和相应文献与测试证据；不得把计划当结果。 | 蒋励 |
| [`single-commit-feature-extraction`](single-commit-feature-extraction/tasks.md) | 2 / 3 | 对当前后端接入做真实 Camel 联调与时延复测，取得跨线验收证据。 | 苏哲勋、蒋励、吕建江 |
| [`test-set-eval-figures`](test-set-eval-figures/tasks.md) | 8 / 9 | 核对导出 SQL 与现行五表 schema，重跑图集页面验收。`data_model/evaluation/out/` 未入库，不能以旧七表产物代替。 | 蒋励，后端线协作 |

任务数只统计 `tasks.md` 的勾选框；**勾选不等于证据有效**。归档前必须再按当前提交核实每条已勾选项，尤其是旧报告、旧权重和已删除路径。模型清单数量与在线加载数量须分别记录；失败项保留失败结论，不能为了归档改写为通过。

## 归档操作顺序

1. 负责人在各自 `tasks.md` 补执行命令、日期、结果和可打开的证据；未执行项保持未勾选。
2. 对照 `docs/`、现行代码和 `specs/`，逐条确认 delta 的 Requirement 及 Scenario。新 capability 归档时才生成对应活规格；`MODIFIED` 标题必须与活规格相同。
3. 跑 [`../README.md`](../README.md) 中的 OpenSpec 与结构校验，并完成受影响模块的真实测试。
4. 由负责人确认验收结论并更新飞书看板，再执行 `openspec archive <change-id> --yes`；复查归档目录和活规格，最后提交 PR。

历史归档是当时的记录，旧路径和旧指标不自动成为当前证据。需要继续实施已撤回范围时，按现行 [`../specs/`](../specs/) 另开 change。
