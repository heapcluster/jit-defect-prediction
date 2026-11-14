# 撤回说明

状态：**历史 CI 实施记录，旧 delta 不再应用到当前活规格**。原 change 要求每次提交都运行完整 lint/test/build，并引用已删除的 `infra/ci_scope.py` 与旧测试路径；当前工作流已改成目录范围选择，纯文档 PR 走轻量检查。

当前 CI 契约见 `openspec/specs/ci-quality-gate/spec.md`，实际实现见 `.github/workflows/ci.yml`、`.github/ci/ci_scope.py` 和 `.github/ci/tests/`。本次保留旧 proposal、tasks 和证据为历史，不把当时的运行结果当作当前 CI 验收。
