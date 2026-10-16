# ci-quality-gate 验证记录

日期：2026-10-16。基线：`59ad7ed8c6caf35e257a7cf66395c13357beb83a`。本记录区分本地静态测试、真实 Actions 执行和服务端规则，不将未执行写成通过。

| 检查 | 结果 | 证据 / 复现 |
|---|---|---|
| 工程化 8 条 unittest | 8/8 passed，exit 0 | 根目录 `python -X utf8 -B -m unittest discover -s infra/tests -p 'test_*.py' -v`；Windows 本地静态约束测试 |
| actionlint | 1.7.12，exit 0，无诊断 | 官方 release 的 Windows amd64 zip 与 checksums 校验一致；`actionlint -shellcheck= -pyflakes= .github/workflows/ci.yml`，未运行额外 shellcheck/pyflakes |
| OpenSpec 新 change | valid，exit 0 | `openspec validate ci-quality-gate --strict --no-interactive` |
| 活规格 | 11 passed / 0 failed，exit 0 | `openspec validate --specs --strict --no-interactive`；不检查/重排存量 change |
| GitHub PR 首次运行 | 待提交 | 待记录 PR/run URL、head、失败阶段或成功结果 |
| 必需状态检查 | 待配置 | ruleset `23522853` 当前 active、无豁免；尚无 required_status_checks |

## 已知缺口

main 尚无前端和模型测试配置/用例，不将对应 skipped 当成测试通过。本地验证不代表 Linux runner 全链路通过；不代修其他线的存量失败。没有执行真实训练、浏览器 E2E 或自行合并。
