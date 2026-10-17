# ci-quality-gate — 任务清单

> 提案：[proposal.md](proposal.md) ｜ 设计决策：[design.md](design.md) ｜ 规格：[ci-quality-gate](specs/ci-quality-gate/spec.md)
> 负责人：repo 苏哲勋 ｜ 创建：2026-10-16 ｜ 状态：进行中
> 用户故事：无（工程化）
> 统一格式见 `docs/common/openspec-task-template.md`（团队已定规范，随 #67 合入）；本文件末的「测试与验证」为强制板块。

## 1. 流水线与交付

- [x] 1.1 顺序质量检查 — 交付 [ci.yml](../../../.github/workflows/ci.yml)，顺序配置 lint/test/build；首轮 lint 失败即 CI failure，后续跳过，证据见 [验证记录](../../../infra/ci-validation.md)。
- [x] 1.2 防回退验证 — 交付 [静态约束测试](../../../infra/tests/test_ci_contract.py)，8 条 unittest 通过，actionlint 无错误；结果见 [验证记录](../../../infra/ci-validation.md)。
- [x] 1.3 跨线交付 — 向 backend/frontend/model 三线交付 PR #72 的 `CI` 日志和 [复现说明](../../../infra/ci.md)，失败定位到阶段；记录在 [验证记录](../../../infra/ci-validation.md)，不代修业务代码。

## 2. GitHub 门禁

- [x] 2.1 创建独立 PR 并观察首次运行 — PR #72、首轮 run 和失败原因已归档到 [验证记录](../../../infra/ci-validation.md)，未称全绿。
- [ ] 2.2 正式启用 main 必需检查 — 提前启用已按用户确认暂撤；须 #72 全绿合入 main、活动 PR 同步工作流后，再增加 Actions `CI` 并 GET 回读，原保护不变；见 [验证记录](../../../infra/ci-validation.md)。

## 3. 测试与验证

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | CI job 名称、阶段顺序、失败不忽略、触发、安全、action SHA、已存在测试入口 |
| 测试文件 | [infra/tests/test_ci_contract.py](../../../infra/tests/test_ci_contract.py) |
| 命令 | 仓库根执行 `python -m unittest discover -s infra/tests -p 'test_*.py' -v` |
| 正向 / 边界 | 单 job + lint→test→build；禁止 continue-on-error/忽略失败，后端套件无条件执行 |
| 用例数与结果 | 8/8 passed；actionlint exit 0；见 [验证记录](../../../infra/ci-validation.md) |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 范围 | GitHub runner + lock/requirements + 现有 lint/pytest/build |
| 命令 | `gh pr checks <本 PR 编号> --repo heapcluster/jit-defect-prediction`；`gh run view <run-id> --log-failed` |
| 关键断言 | spec「正常运行」「任一步失败」「已有套件」；失败阶段非零、后续阶段不执行 |
| 用例数与结果 | 首次 PR run failure，lint 失败传播成立；业务测试/build 未执行，不称全链路通过 |
| 证据 | [验证记录](../../../infra/ci-validation.md) |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 依据 | [spec.md](specs/ci-quality-gate/spec.md) 全部 Scenario |
| 命令 / 步骤 | `gh api repos/heapcluster/jit-defect-prediction/rulesets/23522853`；核 `required_status_checks` 为 `CI`，其余保护不变；核 PR 检查和合并状态 |
| 用例数与结果 | 提前配置的 CI 必需项已暂撤，原三条保护回读不变；正式启用和成功放行待 #72 全绿合入/活动 PR 同步后验证，不造故障提交、不自审合并 |
| 证据 | [验证记录](../../../infra/ci-validation.md) |

### 4. 非功能验证

| 维度 | 是否触及 | 命令 / 证据 |
|---|---|---|
| 性能 | 是 | 检查 ci.yml 的 npm/pip 下载缓存和 30 分钟超时；首轮耗时见验证记录，不伪造提速数据 |
| 安全 | 是 | 上述 unittest 检查只读权限、无业务 secrets、禁持久凭据与 action SHA；见验证记录 |
| 可靠 | 是 | unittest + 首轮真实失败传播；中止/未上报应由必需检查阻断 |
| 易用 | 是 | `gh pr checks <PR>` 可定位阶段；复现步骤见 [infra/ci.md](../../../infra/ci.md) |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 正常完整 CI / 成功放行尚未验证 | 首轮模型线 lint 阻塞 test/build；失败传播与必需检查已验证 | repo 苏哲勋 + model 线 | 模型 lint 修复后，本 PR 合入前 |
| 正式必需门禁尚未启用 | 已撤回提前设置，避免无工作流的旧 PR 永久等待 | repo 苏哲勋 | 本 PR 全绿并合入 main、活动 PR 同步后 |
| main 无前端/模型测试入口 | 对应测试尚在其他未合入分支，未将 skipped 说成 passed | frontend / model 各线 | 对应测试 PR 合入时自动接入 |
| 模型线存量 126 项 lint | 已在首轮暴露并本地同版本复现，不跨线代改、不忽略失败 | model 蒋励 | CI PR 合入前修复；具体排期由该线确认 |
| 浏览器 E2E 与真实数据训练未执行 | 不属于本 CI 工程化范围，不等于业务验收完成 | 各业务线 | 后续里程碑 |

结论：CI 工作流已提交 PR，失败传播已实测；提前启用的 main CI 必需项已暂撤，原保护保留。仍为进行中，待业务 lint 修复、全绿合入 main 和活动 PR 同步后正式启用，不回头重排其他存量 change。
