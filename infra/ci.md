# CI 使用与合入门禁

配置：[ci.yml](../.github/workflows/ci.yml)。流程是一个固定名称 `CI` 的 job：安装 → lint → test → build。任一命令失败则 job 失败，后续普通步骤跳过；没有忽略失败的开关。

## 工作流清单

| 文件 | 用途与触发 | 合入门禁 |
|---|---|---|
| [ci.yml](../.github/workflows/ci.yml) | PR、`main` push、merge queue 和手动运行时，顺序执行 lint、测试、构建 | 唯一应设为必需的检查名是 job `CI`；以 GitHub ruleset 实际配置为准 |
| [codeql.yml](../.github/workflows/codeql.yml) | `main` push、每周计划任务和手动运行时扫描 Python 与 JavaScript/TypeScript | 不作为 PR 必需检查；发现的问题在 Security 页处理 |
| [pr-auto-review-prototype.yml](../.github/workflows/pr-auto-review-prototype.yml) | 面向 `main` 的 PR 打开、更新、重开或退出草稿时，运行只读初审原型 | 不自动批准或打回，也不替代非作者人工审阅；默认 `SKIP`，详见 [infra README](README.md) |

三条工作流分别有运行时间上限；CI 与 CodeQL 的并发控制只取消同组旧运行，初审原型按 PR 编号取消过期运行。初审原型只执行目标分支的可信代码、令牌权限只读且不持久化检出凭据。超时或检查失败应保留红灯并查看日志，不通过跳过步骤掩盖问题。这些边界降低卡住和误判的风险，不能保证外部服务或业务测试永不失败。

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

YAML 本身不阻断合入；合入门禁以 GitHub `protect_main` ruleset 的实时配置为准。**2026-10-30 回读该 ruleset 时，已有 1 位批准、禁删除和禁强推规则，但没有 `required_status_checks`；CI 失败尚未形成服务端合入门禁。**仓库管理员应在 CI 检查名称已上报后，将来源 GitHub Actions 的 job `CI` 设为必需检查，再回读规则并用 PR 验证失败确实阻断合入；保留既有审阅/禁强推/禁删除规则和无豁免设置。当前工作流从 `data_model/environment.yml` 安装 Python 依赖，已不引用删除的 `requirements.txt`。

若 PR 显示 `Expected / Waiting for status`，先确认该提交触发了 `pull_request` 检查且分支已同步 `main`，再对照 ruleset 中的检查名称与来源；不要用手动运行替代 PR 的必需检查。若工作流已经报错，打开失败步骤定位业务代码、依赖或环境问题，交对应线修复，不在 CI 中静默排除。

```sh
gh api repos/heapcluster/jit-defect-prediction/rulesets/23522853
gh pr checks <PR编号> --repo heapcluster/jit-defect-prediction
gh run view <run-id> --repo heapcluster/jit-defect-prediction --log-failed
```

未上报、取消、失败不放行；旧 PR 需要同步包含工作流的新基线再触发 PR 检查。手动运行不能替代 PR 的必需检查。若失败是业务代码/依赖问题，交回对应线修复，不在 CI 中静默排除。

不要试推 main、造业务故障提交或绕过保护来证明门禁；配置回读、实际 run 与 PR 合并状态一起核验。实际结果见 [ci-validation.md](ci-validation.md)。

依据：[GitHub 必需检查排错](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)。
