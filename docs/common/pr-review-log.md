# PR 审阅留痕入口

> 课程 §4 要求「PR 合并前至少一位非作者成员审阅，审阅意见保留在平台」。本页只登记**审阅入口与要点**，完整讨论、行内评论与结论以 GitHub PR 页面为准；状态不在此复制。
>
> 现有流程：仓库不在本地保留审阅意见副本，逐条意见以 PR Review / Comment 形式留在 GitHub；本表用于让评审人一眼找到「哪次改动被谁以什么结论审过」。

| PR | 标题 | 审阅人 | 结论 | 要点与跟进 | 日期 |
|---|---|---|---|---|---|
| [#216](https://github.com/heapcluster/jit-defect-prediction/pull/216) | feat: 25 模型在线预测全接通 + 两 bug 修复 + 单测 AI 标注 | neon（jolly326） | APPROVE，squash 合入（`afdee84`） | 核对懒加载、按线取特征、`ModelUnavailable→40001`、详情 `model_name` 透传、同步进度全局化与测试隔离；跟进缺陷 [#217](https://github.com/heapcluster/jit-defect-prediction/issues/217)（语义表默认路径）、[#218](https://github.com/heapcluster/jit-defect-prediction/issues/218)（e2e 文本表缺失）、[#219](https://github.com/heapcluster/jit-defect-prediction/issues/219)（契约/部署未同步） | 2026-11-12 |
| [#215](https://github.com/heapcluster/jit-defect-prediction/pull/215) | feat: DS-1 容器化插件化 + DS-2 缺陷定位/修复参考 + 三线单测补齐 | sober-hub（历史审阅） | 已合入（2026-11-09） | 本行仅登记入口；审阅意见见 PR 页面，本轮未复评 | 2026-11-09 |
| [#214](https://github.com/heapcluster/jit-defect-prediction/pull/214) | docs(common): 统一四类测试交付记录 | 团队成员（历史审阅） | 已合入（2026-11-08） | 本行仅登记入口，本轮未复评 | 2026-11-08 |

## 审阅纪律

- 合入前必须由**非作者**审阅；不得为强行合入临时关闭分支保护。
- 审阅结论与发现的问题逐条落在 PR，缺陷另建 Issue 并在 PR 描述或评论中互链。
- 本表新增行时只填「入口 + 要点」，不要把完整意见复制成第二份真源。
