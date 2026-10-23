# ci-quality-gate 验证记录

日期：2026-10-16。基线：`59ad7ed8c6caf35e257a7cf66395c13357beb83a`。本记录区分本地静态测试、真实 Actions 执行和服务端规则，不将未执行写成通过。

| 检查 | 结果 | 证据 / 复现 |
|---|---|---|
| 工程化 8 条 unittest | 8/8 passed，exit 0 | 根目录 `python -X utf8 -B -m unittest discover -s infra/tests -p 'test_*.py' -v`；Windows 本地静态约束测试 |
| actionlint | 1.7.12，exit 0，无诊断 | 官方 release 的 Windows amd64 zip 与 checksums 校验一致；`actionlint -shellcheck= -pyflakes= .github/workflows/ci.yml`，未运行额外 shellcheck/pyflakes |
| OpenSpec 新 change | valid，exit 0 | `openspec validate ci-quality-gate --strict --no-interactive` |
| 活规格 | 11 passed / 0 failed，exit 0 | `openspec validate --specs --strict --no-interactive`；不检查/重排存量 change |
| GitHub PR 首次运行 | failure，Lint Python exit 1 | [PR #72](https://github.com/heapcluster/jit-defect-prediction/pull/72)；[run 38861835485](https://github.com/heapcluster/jit-defect-prediction/actions/runs/38861835485)，head `0f1be2295d23ed6cf7b60e88439a1fd4774f9ace` |
| 必需状态检查 | 已按用户确认暂撤，待正确顺序重新启用 | [ruleset 23522853](https://github.com/heapcluster/jit-defect-prediction/rules/23522853) GET 回读仅剩原三条保护，active、bypass=[]；启用/撤回经过见下节 |

## 2026-10-16 门禁启用顺序订正

首次在 14:35 启用 required `CI` 并回读，但 #72 未合入，main 与 #67 均无工作流，导致旧 PR 只有 Expected / Waiting for status 而无 run。经用户确认，14:44 已只撤回新增的 required_status_checks；GET 回读保留 deletion、non_fast_forward、pull_request，active、无豁免，原 1 位审阅要求及旧审阅作废规则不变。

#67 当前仍是 CHANGES_REQUESTED；撤回 CI 必需项不等于撤销审阅修改意见。工作流仍在 #72，不删除、不绕过业务失败。重新启用的前提是 #72 全绿并经非作者审阅合入 main，活动 PR 同步后能真实上报 CI。

## 首轮真实 CI 与根因

- runner：Ubuntu 24.04、Node 24、Python 3.12.15；安装 npm/Python/OpenSpec 和前端 lint 均成功。
- `Lint Python` 报 127 项；其中模型线原有 126 项，新建工程化测试的 I001 1 项。本 change 已修复自己的 I001；未改 backend/frontend/data_model 的文件。
- 同版本 Ruff 本地复现：`uv run --no-project --python 3.12 --with ruff==0.16.8 ruff check backend data_model --output-format concise` → exit 1，126 项；`ruff check infra` → exit 0。主要为 UP031（104），其余有 F541、F401、I001 等；只证明触发规则，不推断每项均为功能缺陷。
- 存量分布：`02_szz_labeling.py` 2、`03_extract_features.py` 2、`04_build_dataset.py` 5、`05_split_dataset.py` 19、`06_train_model.py` 42、`07_predict_all.py` 13、`08_model_matrix.py` 25、`09_calibration_threshold.py` 18，均在 `data_model/`。
- 失败后活规格、全部测试和构建步骤均 skipped，整个 `CI` 为 failure，没有把后续跳过变成绿灯。这是失败传播的实际证据，不是测试/build 通过证据。
- 本地 8 条静态约束、actionlint、新 change 与 11 份活规格校验通过；它们不代替后端业务测试或 GitHub 全链路成功。
- 最新提交的 CI 结果以 [PR checks](https://github.com/heapcluster/jit-defect-prediction/pull/72/checks) 为准；再次运行情况在 PR 留记录，避免仅为记录 run id 反复触发新 run。

## Scenario 对照

| spec Scenario | 结果 / 证据 |
|---|---|
| 正常运行 | 尚未完成：模型线 lint 阻塞 test/build，不称全绿 |
| 首次上线 | 已暂撤提前启用的 CI 必需项，保留原三项保护；待工作流就位后再启用 |
| 任一步失败 | 首轮 run 的 Lint Python failure，后续 skipped，job failure |
| 未成功的 PR | 提前启用时已回读 CI 规则且 PR BLOCKED；当前已暂撤，不把历史状态冒充现行 CI 门禁，重新启用后须复核 |
| 成功的 PR | 待业务 lint 修复后复核；仍要求非作者审阅，不自行合并 |
| 已有套件 | 静态约束 8/8；首轮业务测试因 lint 失败未执行 |
| 尚无套件 | main 无前端/模型用例，已记录缺口；首轮所有测试因更早失败而 skipped |
| PR 来自不可信分支 | 静态约束检查只读 token、无 secrets/pull_request_target、action 钉 SHA |

## 已知缺口

main 尚无前端和模型测试配置/用例，不将对应 skipped 当成测试通过。本地验证不代表 Linux runner 全链路通过；模型线需自行处理上述 126 项 lint 后再测后续阶段，未擅自加忽略项。CI 必需门禁当前暂撤，须工作流全绿并合入 main、活动 PR 同步后再启用。没有执行真实训练、浏览器 E2E 或自行合并。
