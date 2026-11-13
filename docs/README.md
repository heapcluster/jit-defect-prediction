# 技术文档导航

本目录记录当前系统的技术设计与接口约定。课程原始要求见 [`common/project-requirements.md`](common/project-requirements.md)；任务负责人和进度以飞书看板为准，仓库 `todo/` 仅作临时任务拆解。

| 问题 | 唯一正文 |
|---|---|
| 系统范围、四页面和端到端数据流 | [`overview.md`](overview.md) |
| 接口路径、参数、响应和错误 | [`api/`](api/) 中与路径同名的文件；总览见 `overview.md` 页面 ↔ 接口表 |
| 五张表的字段与约束 | [`database/`](database/) 中与表同名的文件 |
| 四项业务功能的流程与跨层职责 | [`function_point/`](function_point/) |
| 页面交互与展示 | [`web_page/`](web_page/) |
| 课程项目需求 | [`common/project-requirements.md`](common/project-requirements.md) |
| 测试考核要求及证据规则 | [`common/test-assessment-guide.md`](common/test-assessment-guide.md) |
| 四类测试交付物（单元 / 集成 / 系统 / 验收） | [`test/README.md`](test/README.md) |
| 固定数据源、SZZ 自检和特征链路 | [`common/data-pipeline.md`](common/data-pipeline.md) |
| 本机运行与联调启动顺序 | [`common/local-runbook.md`](common/local-runbook.md) |
| 集成测试端点清单、四类场景与文档/代码偏差 | [`test/integration_test/endpoint_inventory.md`](test/integration_test/endpoint_inventory.md) |
| 测试执行边界与未执行项 | [`test/system_test/execution_records/neon-test-execution.md`](test/system_test/execution_records/neon-test-execution.md) |
| 集成接口测试报告（35 条实测） | [`test/integration_test/report.md`](test/integration_test/report.md) |
| 系统测试运行证据（截图 / 执行记录） | [`test/system_test/execution_records/system-test-run.md`](test/system_test/execution_records/system-test-run.md) |
| 模型交付的 14 维列序 | `data_model/pipelines/expert/models/feature_order.txt`；库内字段见 `database/commit_feature.md` |

缺陷状态与 PR 审阅意见分别以 GitHub Issues 和 PR 页面为唯一真源，本仓库存放的文档只写技术口径与交付物要求，不保存这两类动态记录的副本。

`docs/backend/`、`docs/model/`、`docs/design/`、`docs/frontend/`、`docs/repo/` 是 2026-11 文档重组前的历史路径，不再作为当前引用目标。引用具体字段时直达 `api/` 或 `database/` 的对应文件，不用旧契约版本号代替现行定义。OpenSpec 的变更提案在归档前只是增量，不覆盖本目录的现行设计；迁移状态见 [`../openspec/README.md`](../openspec/README.md)。
