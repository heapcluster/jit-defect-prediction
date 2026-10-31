# PR 自动审阅原型

> 工程化线 ｜ 起草 2026-10-23 ｜ 起草人 苏哲勋

## Why

PR 量增多后，审阅人需要重复核对差异完整性、CI 状态与上轮审阅结论。先建立可复现、失败关闭的自动审阅框架，为未来接入模型服务做准备。

## What Changes

1. 在 PR 更新时运行只读工作流，检查差异可获取性并输出预审状态。
2. 提供模型决策 JSON 的离线输入格式，以及自动批准/请求修改前的安全校验。
3. 加入离线单元测试与工程化说明。

## Capabilities

### Added Capabilities

- `pr-review-automation`：只读预审与离线模型决策约束，详见 `specs/pr-review-automation/spec.md`。

## Impact（影响与边界）

| 项 | 内容 |
|---|---|
| 影响目录 | `.github/workflows/`、`infra/`、本 change |
| 触及 `docs/design/sprint0-scope.md` 边界？ | 否；只改变仓库协作工具，不改变产品预警逻辑 |
| 不做什么 | 不调用或选择模型 API；不上传代码差异给第三方；不存凭据；不在本阶段自动提交 GitHub 审阅；不修改现有主分支门禁 |
