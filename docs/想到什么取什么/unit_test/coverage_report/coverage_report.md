# 单元测试覆盖率报告

| 项 | 内容 |
|---|---|
| 被测提交 | `1d6b06c` |
| 覆盖率范围 | `backend/app/`（后端服务代码） |
| 统计工具 | pytest-cov / coverage.py 7.16.2 |
| 生成时间 | 2026-11-17 |

统计口径：行覆盖率 = 已覆盖语句 / 语句总数；分支覆盖率 = 已覆盖分支 / 分支总数；综合覆盖率为 line + branch 合并值。

## 1 总体指标

| 指标 | 数值 |
|---|---:|
| 语句总数 | 2003 |
| 已覆盖语句 | 1741 |
| 未覆盖语句 | 262 |
| **行覆盖率** | **87%** |
| 分支总数 | 476 |
| 已覆盖分支 | 366 |
| 部分覆盖分支 | 68 |
| **分支覆盖率** | **77%** |
| **综合覆盖率** | **85%** |

## 2 逐模块明细

| 文件 | 语句数 | 未覆盖 | 行覆盖率 | 分支数 | 部分覆盖 | 分支覆盖率 |
|---|---:|---:|---:|---:|---:|---:|
| `app/__init__.py` | 0 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/api/__init__.py` | 0 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/api/commits.py` | 88 | 0 | 100.0% | 28 | 1 | 96.4% |
| `app/api/figures.py` | 55 | 6 | 89.1% | 20 | 6 | 70.0% |
| `app/api/health.py` | 16 | 2 | 87.5% | 0 | 0 | 100.0% |
| `app/api/models.py` | 26 | 13 | 50.0% | 8 | 0 | 0.0% |
| `app/api/predict.py` | 15 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/api/sync.py` | 174 | 20 | 88.5% | 46 | 4 | 87.0% |
| `app/api/trends.py` | 45 | 8 | 82.2% | 14 | 2 | 57.1% |
| `app/auth.py` | 8 | 0 | 100.0% | 2 | 0 | 100.0% |
| `app/config.py` | 59 | 2 | 96.6% | 8 | 0 | 100.0% |
| `app/db.py` | 72 | 9 | 87.5% | 26 | 4 | 84.6% |
| `app/diff.py` | 39 | 2 | 94.9% | 22 | 4 | 81.8% |
| `app/e2e_source.py` | 69 | 16 | 76.8% | 10 | 2 | 60.0% |
| `app/errors.py` | 32 | 2 | 93.8% | 0 | 0 | 100.0% |
| `app/explain.py` | 6 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/feature_source.py` | 36 | 3 | 91.7% | 12 | 3 | 75.0% |
| `app/main.py` | 65 | 14 | 78.5% | 10 | 2 | 40.0% |
| `app/model_registry.py` | 236 | 21 | 91.1% | 76 | 11 | 85.5% |
| `app/models.py` | 60 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/schemas.py` | 161 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/semantic_source.py` | 83 | 36 | 56.6% | 18 | 2 | 55.6% |
| `app/services/__init__.py` | 0 | 0 | 100.0% | 0 | 0 | 100.0% |
| `app/services/commits.py` | 131 | 16 | 87.8% | 46 | 10 | 69.6% |
| `app/services/figure_store.py` | 27 | 0 | 100.0% | 10 | 0 | 100.0% |
| `app/services/fix_suggestion.py` | 50 | 14 | 72.0% | 12 | 1 | 75.0% |
| `app/services/git.py` | 99 | 24 | 75.8% | 16 | 1 | 56.2% |
| `app/services/health.py` | 36 | 10 | 72.2% | 0 | 0 | 100.0% |
| `app/services/predict.py` | 152 | 28 | 81.6% | 42 | 8 | 71.4% |
| `app/services/risk_summary.py` | 83 | 13 | 84.3% | 30 | 3 | 90.0% |
| `app/services/sync_state.py` | 10 | 0 | 100.0% | 4 | 1 | 75.0% |
| `app/services/text_inputs.py` | 41 | 3 | 92.7% | 6 | 3 | 50.0% |
| `app/timeutil.py` | 22 | 0 | 100.0% | 8 | 0 | 100.0% |
| `app/validate.py` | 7 | 0 | 100.0% | 2 | 0 | 100.0% |
| **合计** | **2003** | **262** | **87%** | **476** | **68** | **77%** |

## 3 覆盖率短板（行覆盖 < 80%）

| 文件 | 行覆盖率 | 未覆盖语句 |
|---|---:|---:|
| `app/api/models.py` | 50.0% | 13 |
| `app/semantic_source.py` | 56.6% | 36 |
| `app/services/fix_suggestion.py` | 72.0% | 14 |
| `app/services/health.py` | 72.2% | 10 |
| `app/services/git.py` | 75.8% | 24 |
| `app/e2e_source.py` | 76.8% | 16 |
| `app/main.py` | 78.5% | 14 |

## 4 附件

| 文件 | 用途 |
|---|---|
| `htmlcov-1d6b06c/index.html` | coverage.py 原始 HTML 报告，可逐文件查看未覆盖行 |
| `coverage-1d6b06c.pdf` | HTML 报告打印版，用于书面提交 |
| `coverage_report.md` | 本文件，静态表格汇总 |
