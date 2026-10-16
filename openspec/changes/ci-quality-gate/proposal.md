## Why

当前 main 没有自动 CI，人工验证不能保证每次提交均运行检查。需要自动执行 lint → test → build，并通过服务端必需检查阻断失败 PR。

## What Changes

- 新增 `.github/workflows/ci.yml`，对指向 main 的 PR、main push、merge queue 和手动触发运行。
- 在同一 `CI` job 内顺序执行检查、测试、构建，任何非零退出立即失败。
- 补工程化静态约束测试、复现说明与证据；首次运行后为 main 增加必需状态检查，保留现有保护。
- 不做：不修改各业务线代码/依赖版本，不代修存量失败，不运行真实数据采集/训练，不部署，不按模型风险分拦截。业务系统仍只提供建议性预警，不改变其范围边界。

## Capabilities

### New Capabilities

- `ci-quality-gate`：质量流水线、失败传播和 main 合入门禁。

### Modified Capabilities

无。

## Impact

- 仅涉及 `.github/`、`infra/`、本 change 和 GitHub ruleset；不改变接口/库表/特征契约。
- 向 backend/frontend/model 三线交付 `CI` 检查及可定位日志；每条线负责修复本线失败。
- main 当前仅有后端业务测试；前端/模型测试配置与用例合入后自动接入，不将尚无套件计为测试通过。
- GitHub 服务端门禁是单独配置，不由 YAML 自动启用；启用后未上报/失败的检查均阻断合入。
