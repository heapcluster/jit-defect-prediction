# PR 自动审阅原型规格

## ADDED Requirements

### Requirement: 默认只读

PR 自动审阅原型 MUST 在 PR 更新时运行可信目标分支代码，MUST NOT 调用模型 API、提交审阅或执行 PR 头代码。

#### Scenario: 新提交触发原型

- **WHEN** PR 被打开或同步新提交
- **THEN** 工作流运行只读预审，未收到模型决策时输出跳过原因，不产生 GitHub 审阅

### Requirement: 决策校验

自动决策程序 SHALL 只接受与当前头提交一致、差异完整且格式合法的模型结论。自动批准还 MUST 要求配置的必需检查成功；请求修改 MUST 含可在变更补丁定位的证据。

#### Scenario: 可批准的离线决策

- **WHEN** 输入当前提交的 APPROVE 结论、无 findings、差异完整且 CI 成功
- **THEN** 程序提出 APPROVE；若发布开关未开，MUST NOT 提交审阅

#### Scenario: 差异缺失或结果过期

- **WHEN** 任一文件补丁缺失/截断，或模型结论的提交 SHA 与当前 PR 不同
- **THEN** 程序输出 SKIP，不得批准或请求修改

#### Scenario: 无证据的打回

- **WHEN** REQUEST_CHANGES 未附变更文件内的证据
- **THEN** 程序输出 SKIP，不得发布打回审阅
