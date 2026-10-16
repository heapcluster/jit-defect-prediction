# CI 使用与合入门禁

配置：[ci.yml](../.github/workflows/ci.yml)。流程是一个固定名称 `CI` 的 job：安装 → lint → test → build。任一命令失败则 job 失败，后续普通步骤跳过；没有忽略失败的开关。

## 覆盖与边界

- lint：前端 ESLint、backend/data_model/infra 的 Ruff、活 OpenSpec 规格严格校验。tasks 的十项格式与证据检查仍由 PR 审阅执行，不回头重排存量。
- test：工程化 unittest 和后端完整 pytest 始终运行。main 目前没有前端/模型测试套件，其步骤按文件存在性标 skipped；用例/配置合入即执行 `npm run test:unit` / `python -m pytest -q`。有用例却缺脚本/依赖会失败，不用 `--if-present`。
- build：Vite 生产构建和 Python 编译；不是模型训练、真实服务联调或浏览器 E2E。
- Ubuntu 24.04、Node 24、Python 3.12；依赖以仓库 lock 和 requirements 为准。不更改各线版本、不提交数据/模型/密钥。

## 本地复现

在仓库根目录、Python 3.12 与 Node 24 环境执行（前端子目录命令单独标出）：

```sh
python -m pip install -r backend/requirements.txt -r data_model/requirements.txt
npm install --global @fission-ai/openspec@1.11.0 --ignore-scripts --no-audit --no-fund
```

在 `frontend/` 执行 `npm ci --ignore-scripts --no-audit --no-fund`，然后按阶段复现：

| 阶段 | 工作目录 | 命令 |
|---|---|---|
| lint | frontend | `npm run lint` |
| lint | 根目录 | `python -m ruff check backend data_model infra` |
| lint | 根目录 | `openspec validate --specs --strict --no-interactive` |
| test | 根目录 | `python -m unittest discover -s infra/tests -p 'test_*.py' -v` |
| test | backend | `python -m pytest -q` |
| test（套件存在时） | frontend | `npm run test:unit` |
| test（套件存在时） | data_model | `python -m pytest -q` |
| build | frontend | `npm run build` |
| build | 根目录 | `python -m compileall -q backend/app data_model infra` |

## GitHub 配置与故障定位

YAML 本身不阻断合入。启用顺序必须是：先修复实际 CI 失败 → CI PR 全绿并经非作者审阅合入 main → 各活动 PR 同步含工作流的 main 并触发 PR 检查 → 再在 `protect_main` ruleset 中追加必需 `CI`（来源 GitHub Actions）及严格最新基线。全程保留既有审阅/禁强推/禁删除规则和无豁免设置，需要管理员权限。

不能在工作流尚未合入、旧 PR 尚无运行入口时先强制要求 CI，否则会一直显示 Expected / Waiting for status。2026-10-16 已按用户确认暂撤提前启用的 CI 必需项；工作流文件不删除，后续按上述顺序启用。

```sh
gh api repos/heapcluster/jit-defect-prediction/rulesets/23522853
gh pr checks <PR编号> --repo heapcluster/jit-defect-prediction
gh run view <run-id> --repo heapcluster/jit-defect-prediction --log-failed
```

未上报、取消、失败不放行；旧 PR 需要同步包含工作流的新基线再触发 PR 检查。手动运行不能替代 PR 的必需检查。若失败是业务代码/依赖问题，交回对应线修复，不在 CI 中静默排除。

不要试推 main、造业务故障提交或绕过保护来证明门禁；配置回读、实际 run 与 PR 合并状态一起核验。实际结果见 [ci-validation.md](ci-validation.md)。

依据：[GitHub 必需检查排错](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)。
