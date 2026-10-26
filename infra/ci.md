# CI 使用与合入门禁

配置：[ci.yml](../.github/workflows/ci.yml)。流程是一个固定名称 `CI` 的 job：安装 → lint → test → build。任一命令失败则 job 失败，后续普通步骤跳过；没有忽略失败的开关。

## 覆盖与边界

- lint：前端 ESLint、backend/data_model/infra 的 Ruff（`ruff check` + `ruff format --check`，配置统一在仓库根 `ruff.toml`）、活 OpenSpec 规格严格校验，以及活文档链接和未归档 change 的 MODIFIED requirement 标题冲突检查。tasks 的十项格式与证据检查仍由 PR 审阅执行，不回头重排存量。
- test：工程化 unittest 和后端完整 pytest 始终运行；前端/模型步骤在对应测试文件存在时执行。用例存在但缺脚本/依赖会失败，不用 `--if-present`。
- build：Vite 生产构建和 Python 编译；不是模型训练、真实服务联调或浏览器 E2E。
- Ubuntu 24.04、Node 24、Python 3.12；前端依赖以 `frontend/package-lock.json` 为准，Python 依赖仅以 `data_model/environment.yml` 为准。CI 用 `setup-miniconda` 激活该环境，再单独确认同一文件中钉定的 Ruff；不更改各线版本、不提交数据/模型/密钥。完整模型依赖较大，CI 超时设为 60 分钟；实际耗时须以 GitHub run 验证。

文档链接检查只核仓库内**实际 Markdown 链接**及 `openspec/specs/` 活规格中反引号标出的仓库文件路径；归档 change、变更日志、历史引用段和生成数据/权重不作存在性断言。`docs/` 正文里作为示例或历史叙述的反引号路径暂不纳入硬门禁，避免把已知旧口径和计划产物误当现行链接；这不是全仓所有路径均已修好的证明。撞车检查仅按「capability + MODIFIED requirement 标题」识别跨未归档 change 的重复，ADDED 与已归档 change 不参与。

## 本地复现

在仓库根目录、已安装 conda 与 Node 24 的环境执行（前端子目录命令单独标出）：

```sh
conda env create -f data_model/environment.yml
conda activate jit-defect-prediction
npm install --global @fission-ai/openspec@1.11.0 --ignore-scripts --no-audit --no-fund
```

在 `frontend/` 执行 `npm ci --ignore-scripts --no-audit --no-fund`，然后按阶段复现：

| 阶段 | 工作目录 | 命令 |
|---|---|---|
| lint | frontend | `npm run lint` |
| lint | 根目录 | `python -m ruff check backend data_model infra` |
| lint | 根目录 | `python -m ruff format --check backend data_model infra` |
| lint | 根目录 | `openspec validate --specs --strict --no-interactive` |
| lint | 根目录 | `python infra/check_spec_references.py links` |
| lint | 根目录 | `python infra/check_spec_references.py deltas` |
| test | 根目录 | `python -m unittest discover -s infra/tests -p 'test_*.py' -v` |
| test | backend | `python -m pytest -q` |
| test（套件存在时） | frontend | `npm run test:unit` |
| test（套件存在时） | data_model | `python -m pytest -q` |
| build | frontend | `npm run build` |
| build | 根目录 | `python -m compileall -q backend/app data_model infra` |

## GitHub 配置与故障定位

YAML 本身不阻断合入。当前 main 的旧工作流还引用已删除的 requirements；本次改为唯一环境文件后，先在修复 PR 上核验安装、lint、test、build 的实际结果。若仍因模型线 lint 等失败，须交对应线修复，不能称全绿或提前启用门禁。修复 PR 全绿并经非作者审阅合入 main、活动 PR 同步 main 并触发检查后，再在 `protect_main` ruleset 中追加必需 `CI`（来源 GitHub Actions）及严格最新基线。全程保留既有审阅/禁强推/禁删除规则和无豁免设置，需要管理员权限。

不能在工作流尚未合入、旧 PR 尚无运行入口时先强制要求 CI，否则会一直显示 Expected / Waiting for status。2026-10-16 已按用户确认暂撤提前启用的 CI 必需项；工作流文件不删除，后续按上述顺序启用。

```sh
gh api repos/heapcluster/jit-defect-prediction/rulesets/23522853
gh pr checks <PR编号> --repo heapcluster/jit-defect-prediction
gh run view <run-id> --repo heapcluster/jit-defect-prediction --log-failed
```

未上报、取消、失败不放行；旧 PR 需要同步包含工作流的新基线再触发 PR 检查。手动运行不能替代 PR 的必需检查。若失败是业务代码/依赖问题，交回对应线修复，不在 CI 中静默排除。

不要试推 main、造业务故障提交或绕过保护来证明门禁；配置回读、实际 run 与 PR 合并状态一起核验。实际结果见 [ci-validation.md](ci-validation.md)。

依据：[GitHub 必需检查排错](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)。
