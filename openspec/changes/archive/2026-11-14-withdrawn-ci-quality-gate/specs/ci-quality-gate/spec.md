## ADDED Requirements

### Requirement: 质量阶段顺序与失败传播

流水线 MUST 在同一固定名称 `CI` job 内按 lint → test → build 顺序执行，MUST NOT 忽略失败。

#### Scenario: 正常运行

- **WHEN** 安装、lint 和全部适用测试成功
- **THEN** 执行生产构建，所有阶段成功才返回 success

#### Scenario: 任一步失败

- **WHEN** 安装、lint、test 或 build 任一命令非零退出
- **THEN** `CI` 返回 failure，后续普通步骤不执行，不把 skipped 视作整条流水线通过

### Requirement: 合入门禁

main 的服务端规则 MUST 将 GitHub Actions 的 `CI` 设为必需状态检查，并保留既有审阅和分支保护。

#### Scenario: 首次上线

- **WHEN** CI PR 尚未全绿合入 main，或活动 PR 尚未同步工作流运行入口
- **THEN** CI 必需项 MUST 暂不启用，先完成运行入口接入，再正式启用；既有审阅和分支保护 MUST 始终保留

#### Scenario: 未成功的 PR

- **WHEN** PR 最新测试提交的 `CI` 失败、取消或未上报
- **THEN** main 合入被阻断，不因 YAML 文件存在而宣称门禁已启用

#### Scenario: 成功的 PR

- **WHEN** 最新 `CI` success 且其他既有保护均满足
- **THEN** CI 不再阻断该 PR，仍须非作者审阅

### Requirement: 触发、安全与覆盖写实

工作流 MUST 支持 main PR/push 和 merge_group，使用只读 token、钉 SHA 的 action；测试缺口 MUST 明示。

#### Scenario: 已有套件

- **WHEN** 执行 CI
- **THEN** `ruff check backend data_model infra` 对全部现有 Python 代码执行且不得以存量忽略项放行；始终运行后端与工程化套件，前端/模型用例合入后执行其统一入口，运行失败不能忽略

#### Scenario: 尚无套件

- **WHEN** main 尚无前端或模型测试配置/用例
- **THEN** 对应步骤为 skipped，不能在证据中称该线测试通过

#### Scenario: PR 来自不可信分支

- **WHEN** pull_request 触发 CI
- **THEN** 不使用 pull_request_target、不注入业务密钥、不持久保存 checkout 凭据
