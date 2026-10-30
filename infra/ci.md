# CI：应用运行与核心回归

> 配置：`.github/workflows/ci.yml`。本文件是现行工作流说明；历史首跑记录见 `infra/ci-validation.md`，不能当作本次简化后的通过证据。

## 合入门禁

仓库只保留一条 GitHub Actions 工作流、一个 job。工作流显示名称是「应用运行与核心回归」，job 的必需检查标识保持 `CI`，让既有 PR 不必为改名全部重跑。它在 PR、`main` 推送、merge queue 和手动触发时运行；任一命令失败，检查失败。合入仍须按仓库规则由非作者审阅，CI 不自动审批。

| 阶段 | 执行内容 | 防止的问题 |
|---|---|---|
| 环境 | 从 `data_model/environment.yml` 建 Python 环境，`frontend/package-lock.json` 安装前端依赖；准备一次性 MySQL 测试库 | 依赖或数据库初始化缺失 |
| 后端 | `backend/` 下 `python -m pytest -q` | 接口、鉴权、数据库、同步、推理回归 |
| 前端 | `frontend/` 下 `npm run test:unit` | 页面逻辑与 API 适配回归 |
| 模型 | `data_model/` 下 `python -m pytest -q` | 特征与模型逻辑回归；干净检出没有模型权重时，跳过项仍需交付时另验 |
| 构建 | `frontend/` 下 `npm run build`；根目录编译 Python 源码 | 前端构建失败、Python 语法错误 |

CI 通过只说明这些可自动运行的检查在该提交通过，不能保证没有任何 Bug，也不能替代真实权重、浏览器联调、系统/验收或性能测试。模型文件不入库，因此真实权重加载须按 `docs/common/test-plan.md` 单独取证。

## 按需人工检查

格式、OpenSpec 结构、文档链接、MODIFIED 冲突和安全扫描不再作为每个 PR 的自动门禁。变更契约时应在评审中运行 `openspec validate --specs --strict --no-interactive`，修改文档链接时运行 `python infra/check_spec_references.py links`，有并行 change 时运行 `python infra/check_spec_references.py deltas`。Python/前端风格检查可分别运行 `python -m ruff check backend data_model infra` 和 `npm run lint`；涉及安全风险时另做安全审查。发现真实运行或契约缺陷仍须修复。

只读 PR 自动审阅原型的脚本保留在 `infra/pr_auto_review.py`，但其自动触发工作流已移除；CodeQL 定时扫描工作流也已移除。如需恢复安全扫描，应另行明确触发方式与责任人。

## 合入检查

GitHub ruleset 的必需检查依据 **job 名称**。本次保持 `CI`（来源 GitHub Actions）不变，只改工作流显示名称。合入前回读 `protect_main` ruleset，确认仍要求 1 位非作者批准、禁止强推和删除，无 bypass；PR 上 `CI` 全绿后再合入。既有 PR 不会因名称迁移出现永久等待。

本地复现与具体依赖准备见 `docs/common/local-runbook.md`。历史 CI 故障与证据见 `infra/ci-validation.md`。
