# 单元测试代码（交付副本）

课程交付目录树要求 `unit_test/tests/` 存放测试代码。**仓库内代码不移动**——`backend/pytest.ini` 的 `testpaths = tests`、CI 的 `--cov=app`、vitest 扫描路径都绑定各线目录，移动会破坏一键运行与覆盖率。本目录是仓库现行版本的**只读快照**。

## 1 · 当前同步登记

| 项 | 值 |
|---|---|
| 同步日期 | 2026-11-13 |
| 仓库提交 SHA | `bd39d95`（工作副本，含未提交改动） |
| 副本内容 | 43 个 `.py` + 10 个 `.js`，含 `conftest.py` / `setup.js`；已排除 `__pycache__` 与 `.pyc` |
| 子目录 | `backend/`、`data_model/`、`frontend/`、`infra/` |
| 参与 CI | **否**；复跑一律在仓库内原目录执行 |

> 实测证据（249 / 162 / 59 passed、行覆盖 85%）来自 `afdee84`，与本副本 SHA 不同；最终交付须按同一 SHA 重新同步并复跑，见 [`../../README.md`](../../README.md) §6、§9。

| 线 | 仓库内实际位置 | 运行命令 |
|---|---|---|
| 后端 | `backend/tests/`（`test_*.py` + `conftest.py`） | `cd backend && python -m pytest -q` |
| 模型线 | `data_model/tests/` | `cd data_model && python -m pytest -q` |
| 前端 | `frontend/tests/`（`*.spec.js` + `setup.js`） | `cd frontend && npm run test:unit` |
| 基础设施 | `infra/tests/` | `python -m pytest -q infra/tests` |

## 2 · 上传前重新同步

交付包需要一份实体副本，但仓库代码在开发期持续变更，手工拷贝必然过期。上传飞书前执行：

```powershell
$sha = git rev-parse --short HEAD
foreach ($line in @('backend','data_model','frontend','infra')) {
  $dst = "docs/test/unit_test/tests/$line"
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Copy-Item -Path "$line/tests/*" -Destination $dst -Recurse -Force
}
Get-ChildItem -Recurse -File docs/test/unit_test/tests -Filter *.pyc | Remove-Item -Force
```

同步后在本文件登记 SHA 与日期，并在 [`../../README.md`](../../README.md) §6 的「产物与提交对照」中核对四类 SHA 一致。副本不参与仓库内 CI，**不在此手工编辑**。

## 3 · 副本的合规缺口

- 文件头来源注释多为单个 `[AI生成]` / `[AI生成-人工修改]` 标签，不符合指南 §2.1 的「用例来源比例」格式；整改须在**仓库内原文件**完成再重新同步，见 [`../README.md`](../README.md) §5。
- 单元测试的 AI 提示词未归档，见 [`../prompts/README.md`](../prompts/README.md)。
- 覆盖率 HTML / PDF 报告未归档，见 [`../coverage_report/README.md`](../coverage_report/README.md)。
