# OpenSpec 使用与迁移状态

`specs/<capability>/spec.md` 是已归档能力的活规格；`changes/<change>/` 是尚待验收或归档的增量；`changes/archive/` 仅作历史证据。当前产品技术正文见 [`../docs/README.md`](../docs/README.md)。

## 新变更统一格式

- `proposal.md`：Why、What Changes、Capabilities、Impact；范围变化指向 `docs/overview.md`。
- `specs/<capability>/spec.md`：在 ADDED / MODIFIED / REMOVED 下写 `### Requirement: <稳定标题>`，每条至少一个正常及一个必要的异常/边界 `#### Scenario:`，使用 WHEN / THEN。MODIFIED 的标题须与目标活规格中的标题**完全相同**。
- `design.md`：只记技术取舍及跨模块接口，不复制 proposal。
- `tasks.md`：按 [`TASKS_TEMPLATE.md`](TASKS_TEMPLATE.md) 写文件头、连续编号、可验收任务和末尾五节「测试与验证」。证据未产生就写“未执行/待补”，不能勾选。
- `.openspec.yaml`：仅在需要自定义 schema 或生成上下文时使用；是否存在不作为格式合格判据。

命令：在仓库根目录执行 `openspec validate --specs --strict`；每个活跃 change 再执行 `openspec validate <change> --strict`。CLI 未安装时在 PR 中如实标记未执行。纯文档 PR 的 CI 仍走轻量检查；OpenSpec 规范校验由提交者和审阅者执行。

## 2026-11 文档重组后的待迁移项

原 `docs/backend/`、`docs/model/`、`docs/design/` 等目录已移除。历史归档里的路径保留作为当时记录；**活规格和活跃 change 中的旧路径不能当可点击证据**，应指向 `docs/api/`、`docs/database/`、`docs/function_point/`、`docs/web_page/` 或实际测试报告。旧版本号及“4 表/3 页/2–3 模型”等历史口径不代表现行系统。

现行基线以 `docs/overview.md` 为准：5 张表、4 个页面、四条模型线共 25 模型（在线权重的可用范围按实际交付清单核验）。本轮已订正 `db-schema`、`query-api`、`model-training`、`model-delivery`、`model-coverage`、`szz-labeling`、`commit-collection`、`feature-extraction` 八份活规格中的旧结构与路径。规范订正不等于功能验收；真实权重、数据库及页面结果仍须按对应 change 逐项取证。

活跃 change 的口径冲突与证据缺口见 [`changes/README.md`](changes/README.md)。本次重组映射的路径是**导航入口**；旧 `§` 章节号及原文里的历史验收数字不自动迁移。任何指向已删除截图、报告或脚本的证据，都需由负责人重新提供可打开的 PR/飞书链接并复核结果。
