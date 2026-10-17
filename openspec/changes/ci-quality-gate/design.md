## Context

main 已有前端 lint/build 与后端 pytest，测试入口在其他分支上的状态不同。分支保护使用 ruleset，不使用经典 branch protection。

## Goals / Non-Goals

目标为固定名称 `CI` 的可追溯检查，按阶段先后执行并保持失败状态。非目标见 proposal，不复制业务验收内容。

## Decisions

- 单 job 而非依赖链：上游失败会令 job 失败，避免下游 skipped 被必需检查视为成功。
- Node 24、Python 3.12、Ubuntu 24.04；使用仓库 lock/requirements，缓存下载而非共享工作目录。
- 所有 action 钉完整 SHA；只读 token、不保留 checkout 凭据、不用 `pull_request_target` 或业务密钥。
- 不加 PR 路径过滤；支持 merge_group。前端/模型业务测试仅在配置或用例存在时执行，后端和工程化测试始终执行；存在但缺脚本/依赖则失败。
- 活规格严格校验与 PR 人工十项检查分开，不重排已补齐的存量 tasks。
- 构建是 Vite 生产构建和 Python 编译，不是模型训练或完整 E2E。

## Risks / Trade-offs

- 存量 lint/依赖/测试失败会使首轮 CI 变红，不忽略、不跨线代改。
- 缺失的前端/模型套件不等于已覆盖，记录缺口并由对应线交付。
- 必需检查设定后，旧 PR 必须包含 workflow 并重新触发；只运行手动 workflow 不替代 PR 检查。

## Migration Plan

从最新 main 独立提交 CI PR，观察 pull_request 运行；修复真实失败并全绿后，由非作者审阅合入 main。活动 PR 同步工作流并触发检查后，再追加 main ruleset 的 required status check `CI`，不覆盖审阅、禁强推、禁删除与豁免设置。不能在旧 PR 尚无运行入口时先启用必需检查；本次提前启用已按用户确认暂撤。失败写实，不合并未经审阅的 CI PR。

## Open Questions

前端/模型测试及后续跨线 E2E 的扩展由各线新增入口，本 change 不倒填其执行结果。
