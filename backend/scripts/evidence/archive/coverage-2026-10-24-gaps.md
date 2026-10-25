# 覆盖率补测证据 2026-10-24（Sprint 2 报告 §6 第 5、7 项）

- 目的：关掉 `docs/common/test-report-sprint2.md` §6 里标为「低成本」的两条缺口 —— 第 5 项（`app/db.py` 的 `get_engine()` 懒建分支 + `app/db.py`/`app/ingest.py` 的 CLI `main()` 与 `__main__` 守卫）与第 7 项（`app/feature_source.py:17` 抽取脚本不可加载 → `RuntimeError`）。
- 口径与前六次基线一致：**行覆盖**（`branch_coverage: false`）、`--cov=app`、计数取自 junitxml 与 coverage JSON，不凭终端回显。
- 基线提交：main `edfe74f`。前后两次的 `backend/app`、`backend/tests`、`pytest.ini` 逐字同源（`git diff --stat edfe74f <前一次 head> -- backend/app backend/tests pytest.ini` 为空），故两次数字可直接比。
- 本文件只记已发生的验证；**不倒填** `coverage-2026-10-24.md`（那份文件 §6 明写「再另出文件，不在本文件倒填」）。

## 1. 环境

| 项 | 值 |
|---|---|
| 解释器 | conda 环境 `jit-defect-prediction` 的 `python`（`sys.executable`，子进程用例里另有存在性断言） |
| 版本 | Python 3.12.15、pytest 9.1.1、SQLAlchemy 2.0.54、FastAPI 0.141.1、ruff 0.16.8（与 `data_model/environment.yml` 钉的 ruff 同版本） |
| cwd | `backend`（命令）／仓库根（ruff、门禁） |
| 覆盖率产物 | `.coverage` / `cov.json` / `junit.xml` 只落本机临时目录，不入库（`.gitignore` 已覆盖） |

## 2. 前后对比

| 时点 | 用例条数 | Stmts | Miss | TOTAL |
|---|---|---|---|---|
| 补测前（main `edfe74f`） | 149 | 699 | 55 | **92.13%** |
| 补测后（+8 条） | **157** | 699 | **34** | **95.14%** |

Stmts 不变（699）：本次只加测试，`backend/app` 一行未动。

逐模块缺口收敛（coverage JSON 的 `missing_lines`）：

| 模块 | 补测前 miss | 补测后 miss |
|---|---|---|
| `app/db.py` | `22,23,24,25,57,58,59,60,61,62,64,65,66,67,71`（15 行） | `71`（1 行） |
| `app/ingest.py` | `109,110,111,112,114,115,119`（7 行） | `119`（1 行） |
| `app/feature_source.py` | `17`（1 行） | 无 |

## 3. 新增 8 条用例与各自钉住什么

| # | 用例 | 钉住的行为 | 覆盖行 |
|---|---|---|---|
| 1 | `test_db.py::test_get_engine_lazily_builds_from_database_url` | 未预配置时按 `DATABASE_URL` 懒建 engine、绑到 `SessionLocal`、第二次调用命中缓存不新建，且懒建这条路真能 `init_db()` 建四张表并过 `_assert_indexes` | `db.py:22,24,25` |
| 2 | `test_db.py::test_get_engine_without_database_url_raises_50000` | `DATABASE_URL` 为空 → `AppError(50000, "internal error")`（fail closed，消息是固定文案、不含配置细节） | `db.py:22-23` |
| 3 | `test_db.py::test_db_cli_covers_usage_config_error_and_success` | CLI 三条出口：无参 rc=2 且 stderr 是用法行；配置错 rc=1 且 stderr 指路 `DATABASE_URL`、**不回显** `internal error`；正常 rc=0 且打印四张表、库文件真的落盘 | `db.py:57-67` |
| 4-5 | `test_db.py::test_module_guard_exits_with_usage[app.db / app.ingest]` | 用 `sys.executable -m <module>` 起**真子进程**，断言退出码 2 + stderr 含「用法：」——即 `__main__` 守卫确实把 `main(sys.argv)` 的返回值变成了进程退出码 | 守卫的**行为**（见 §4） |
| 6 | `test_ingest.py::test_ingest_cli_covers_usage_and_success` | CLI 参数不足 rc=2、种类非法 rc=2、正常路径经 `get_engine()` 走 `ingest()` 并真的落一行（rc=0 + 「灌入完成（commits）：1 行」+ 查库 1 行） | `ingest.py:109-115` |
| 7-8 | `test_feature_source.py::test_extractor_raises_when_script_unimportable[spec_none / loader_none]` | `spec is None` 与 `spec.loader is None` 两个分支都抛固定文案 `RuntimeError("feature extractor unavailable")`；`_extractor` 带 `lru_cache`，用 autouse 夹具在每条用例前后 `cache_clear()`，避免上一条的结果被下一条继承 | `feature_source.py:16-17` |

不引入外部依赖：8 条全部只靠 `tmp_path` / `monkeypatch` / `capsys` 与一个 `python -m` 子进程，不需要真模型权重、不需要 MySQL、不需要网络。

## 4. 仍未覆盖的两行（如实登记，不是遗漏）

`app/db.py:71` 与 `app/ingest.py:119` 都是 `raise SystemExit(main(sys.argv))`，只在 `python -m <module>` 的**子进程**里执行；本次没有开 coverage 的子进程测量（`COVERAGE_PROCESS_START` + `sitecustomize`），所以这两行在 JSON 里仍是 miss。

它们的行为**已被断言**：上表 4-5 条用真子进程跑出 rc=2 与用法行，等价于验证了守卫把 `main()` 的返回值透传成退出码。要把这两行也变成 hit，需要给 CI 加子进程覆盖率采集（改 `.github/workflows/ci.yml`，属 infra 线），不在本 PR 范围。

## 5. 命令与真实输出

```bash
# ① 补测前基线（cwd=backend）
python -m pytest -q --cov=app --cov-report=json:<tmp>/cov_before.json --junitxml=<tmp>/cov_before.xml
#    → junitxml: tests=149 failures=0 errors=0 skipped=0
#    → coverage JSON totals: num_statements=699 missing_lines=55 percent_covered=92.13

# ② 补测后（cwd=backend，同命令换输出文件名）
python -m pytest -q --cov=app --cov-report=json:<tmp>/cov_after.json --junitxml=<tmp>/cov_after.xml
#    → junitxml: tests=157 failures=0 errors=0 skipped=0 time=12.783
#    → coverage JSON totals: num_statements=699 missing_lines=34 percent_covered=95.14

# ③ 定向复跑三份测试文件（cwd=backend）
python -m pytest tests/test_db.py tests/test_ingest.py tests/test_feature_source.py -q --junitxml=<tmp>/t3.xml
#    → tests=13 failures=0 errors=0 skipped=0 time=2.594

# ④ lint（cwd=仓库根）
python -m ruff check backend/tests/test_db.py backend/tests/test_ingest.py backend/tests/test_feature_source.py --output-format concise
#    → All checks passed!
python -m ruff check backend data_model infra --output-format concise
#    → infra\pr_auto_review.py:47:13: TRY004 …（Found 1 error）＝ main 继承来的错误，见 Issue #126，与本 PR 无关
```

`<tmp>` 为本机临时目录（个人绝对路径按 `docs/repo/collaboration.md` §0 第 3 条不复述）。

## 6. 本 PR 不做什么

- 不改 `docs/common/test-report-sprint2.md`：§0 头条数字、§2 逐文件条数、§3 基线表第 7 行、§4 用例链、§6 第 5/7 项翻状态，都属**台账**，按 §0 第 5 条「代码与台账不同时动」另开一个 docs PR（本 PR 合入后立刻提，数字以本文件为准）。
- 不动 §6 第 6 项（`app/errors.py` 的 `ok()` 无调用方 + 兜底处理器）：那条报告里已判为「死代码信号，建议删或补调用，需另开 change」，不是加一条夹具能了结的。
- 不动 `app/` 任何一行：本次是纯补测，改实现会同时改动 Stmts 分母，前后就不可比了。
