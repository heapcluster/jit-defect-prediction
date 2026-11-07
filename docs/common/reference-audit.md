# 文档引用核查记录（2026-11-07）

本页记录 S-3 的路径核查，不替代各目录的权威正文。核查范围为 Git 跟踪的当前 `docs/`、活跃 OpenSpec、代码注释与提示、临时 `todo/`；`openspec/changes/archive/` 保留当时引用，按历史材料处理。运行时生成的覆盖率、截图和模型报告未视为仓库内文件。

## 已修复

| 原引用 | 当前入口 | 处理 |
|---|---|---|
| `docs/backend/api-spec.md` | [`../api/README.md`](../api/README.md) 与各接口页 | 活跃规格与代码提示改到现行接口页；旧章节号不沿用 |
| `docs/model/feature-columns.md`、`docs/design/data-fields.md` | [`../database/commit_feature.md`](../database/commit_feature.md)、[`../database/commit.md`](../database/commit.md) | 特征和提交字段改到对应表页；离线标签 CSV 与在线字段明确区分 |
| `docs/model/data-pipeline.md` | [`data-pipeline.md`](data-pipeline.md) | 固定数据源、打标判据和统计口径按现行章节重接；历史外沿数字标明来源 |
| `docs/frontend/pages.md`、`docs/pages.md` | [`../web_page/README.md`](../web_page/README.md) 与页面页 | 前端注释改到当前页面入口，不再引用旧章节号 |
| `docs/backend/mysql-setup.md`、`docs/model_performance.md` | [`local-runbook.md`](local-runbook.md)、[`../function_point/model_performance.md`](../function_point/model_performance.md) | 建库错误提示和数据导入说明改到可打开的入口 |
| `docs/repo/defect-records.md`、`docs/frontend/integration-log.md` | [`defect-records.md`](defect-records.md)、[`integration-log.md`](integration-log.md) | 当前引用改到新位置 |

## 仍待负责人补充的内容

| 缺口 | 负责人 / 下一步 |
|---|---|
| 原模型线规划中关于性能选型、`svm` 概率口径的详细论证未完整迁入新文档 | 模型负责人在现行模型文档补实测、依赖版本与取舍；代码实现及测试继续作为当前可核对依据，不能把 [`../overview.md`](../overview.md) 说成已有这些细节 |
| 原研究文献与扩展实验方案未恢复 | 模型负责人按 [`research-notes.md`](research-notes.md) 补来源、数据和复现命令 |
| 旧联调截图、历史报告和本机生成的测试产物不在仓库 | 各执行负责人提供本次真实证据；[`integration-log.md`](integration-log.md) 只登记实际执行结果，不沿用旧通过结论 |

`docs/api/README.md`、`docs/web_page/README.md`、`docs/common/integration-log.md`、`docs/common/defect-records.md`、`docs/common/research-notes.md` 中提及已删除路径，是明确标注“旧路径已移除”的历史说明，**不是可点击的当前链接**。归档 OpenSpec 也保留原始提案时的路径，不作为当前实施指南。

## 复核方式

1. 打开 [`../README.md`](../README.md) 的各入口，再逐个检查本页“已修复”目标是否存在。
2. 扫描当前非归档文件中的 `docs/...md` 引用；除了上段列出的历史说明，不应有缺失路径。
3. 检查 `docs/` 中相对 Markdown 链接能否解析到文件或目录。路径可用不等于测试通过；测试结果另看对应报告与 CI 产物。
