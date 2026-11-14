# ci-quality-gate Specification

## Purpose

用一个稳定的 `CI` 检查报告当前提交的基础运行结果；检查范围由变更文件选择，纯文档 PR 不执行不相关的业务测试。

## Requirements

### Requirement: 单一 CI 检查与失败传播

工作流 SHALL 保留名称为 `CI` 的单一检查；被选中的安装、lint、测试和构建步骤失败时 SHALL 使该检查失败，MUST NOT 用忽略退出码或 `continue-on-error` 伪装成功。实际步骤见 `.github/workflows/ci.yml`。

#### Scenario: 代码变更通过

- **WHEN** PR 改动需要运行的代码目录，且被选中的步骤均成功
- **THEN** `CI` 返回成功，并保留每一步的执行日志

#### Scenario: 被选中步骤失败

- **WHEN** 被选中的测试或构建命令以非零状态退出
- **THEN** `CI` 返回失败，不能报告为可合并的绿色检查

### Requirement: 按变更范围选择检查

工作流 SHALL 使用 `.github/ci/ci_scope.py` 识别变更范围；仅改文档的 PR SHALL 运行轻量检查并给出成功或失败结论，代码与 CI 配置变更 SHALL 运行对应测试。选择器的回归用例见 `.github/ci/tests/`。

#### Scenario: 纯文档 PR

- **WHEN** PR 只修改文档且未触及代码或工作流配置
- **THEN** `CI` 执行轻量路径，不因无关的业务测试或环境准备阻断该 PR

#### Scenario: CI 配置变更

- **WHEN** PR 修改 `.github/workflows/ci.yml` 或 `.github/ci/`
- **THEN** 选择器不得将其误判为纯文档，相关自检须执行
