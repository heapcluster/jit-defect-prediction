# 单元测试说明

## 1 测试范围

单元测试覆盖四条线，测试代码的真源在仓库各端目录，`tests/` 下是提交用副本。

| 线 | 代码位置 | 用例数 | 配置 |
|---|---|---:|---|
| 后端 | `backend/tests/`（28 个文件） | 287 | `pytest.ini`，`testpaths = tests`，marker 分 `unit` / `integration` |
| 模型线 | `data_model/tests/`（16 个文件） | 163 | `pytest.ini` |
| 前端 | `frontend/tests/`（10 个文件） | 65 | `vite.config.js` 的 vitest 配置 |
| 基础设施 | `infra/tests/`（1 个文件） | 8 | CI 契约检查 |
| CI 契约 | `.github/ci/tests/`（2 个文件） | 11 | unittest discover |

测的重点是后端鉴权与错误码、风险概率区间、14 维特征列序、数据采集与 SZZ 判据、时间序切分，以及前端的纯函数与组件契约。

## 2 环境与运行

跑测试的环境是 Windows 11 + conda 环境 `jit-defect-prediction`（Python 3.12.14、pytest 9.1.1、coverage 7.16.2），前端用 Node 24 + vitest。后端用例分两层，请求 `client`、`engine`、`integration_db`、`populated_api` 夹具的归 `integration`，其余归 `unit`。集成层需要本机 MySQL 的 `jit_test` 库。

```bash
# 后端全量（含覆盖率）
cd backend && python -m pytest -q --cov=app --cov-branch

# 只跑纯单元，把 DB 指向不可达地址也能全绿，说明不连库
TEST_DATABASE_URL='mysql+pymysql://x:x@127.0.0.1:1/x' python -m pytest -m unit

# 模型线
cd data_model && python -m pytest -q

# 前端
cd frontend && npm run test:unit

# 基础设施与 CI 契约
python -m pytest -q infra/tests
python -m unittest discover -s .github/ci/tests -p 'test_*.py'
```

`backend/static` 目录由 `create_app()` 自动创建，干净检出后不需要手工建。

## 3 执行结果

被测提交 `1d6b06c`，2026-11-17 实跑：

| 线 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `python -m pytest -q --cov=app --cov-branch` | 287 passed，0 failed / 0 error / 0 skipped |
| 模型线 | `python -m pytest -q` | 163 passed |
| 前端 | `npm run test:unit` | 65 passed / 10 个文件 |
| 基础设施 | `python -m pytest -q infra/tests` | 8 passed |
| CI 契约 | `python -m unittest discover ...` | 11 passed |
| 合计 | — | **534 条全部通过** |

## 4 覆盖率

| 项 | 数值 |
|---|---|
| 行覆盖率 | 1741 / 2003 = **87%** |
| 分支覆盖率 | 366 / 476 = **77%**（68 partial） |
| 综合（term TOTAL） | **85%** |
| 前端覆盖率 | 行 49.9%（319/639）/ 分支 50.8%（281/553）/ 函数 40.1%（99/247） |

覆盖率报告以 Markdown 表格为主，见 [`coverage_report/coverage_report.md`](coverage_report/coverage_report.md)（总体指标 + 逐模块明细 + 短板）。另附 coverage.py 原始 HTML（[`htmlcov-1d6b06c/index.html`](coverage_report/htmlcov-1d6b06c/index.html)）与打印版 PDF（[`coverage-1d6b06c.pdf`](coverage_report/coverage-1d6b06c.pdf)）。

按模块看还有几处偏弱：`app/api/models.py` 38%、`app/semantic_source.py` 56%、`app/services/health.py` 72%、`app/main.py` 73%、`app/services/fix_suggestion.py` 73%、`app/services/git.py` 73%。短板集中在异常分支和条件返回路径，下一轮补测优先处理。

## 5 用例分布

后端 287 条按文件：

| 文件 | 条数 | 文件 | 条数 |
|---|---:|---|---:|
| `test_security_boundaries.py` | 50 | `test_trends_api.py` | 9 |
| `test_sync_api.py` | 23 | `test_services_git.py` | 9 |
| `test_commits_api.py` | 22 | `test_validate.py` | 9 |
| `test_model_registry.py` | 19 | `test_db.py` | 7 |
| `test_mirror.py` | 15 | `test_feature_source.py` | 7 |
| `test_timeutil.py` | 14 | `test_explain.py` | 8 |
| `test_predict_api.py` | 14 | `test_diff.py` | 5 |
| `test_services_commits.py` | 14 | `test_integration_api.py` | 5 |
| `test_config.py` | 10 | `test_schema_sql.py` | 5 |
| `test_online_models.py` | 10 | `test_risk_summary.py` | 5 |
| `test_errors.py` | 4 | `test_health_api.py` | 4 |
| `test_auth_errors.py` | 7 | `test_figures_api.py` | 3 |
| `test_fix_suggestion.py` | 3 | `test_online_inputs.py` | 3 |
| `test_trends_sql.py` | 3 | | |

模型线 163 条以 `test_szz_labeling.py`（42）最多，其余为 `test_split_dataset.py`（17）、`test_extract_features_pure.py`（15）、`test_text_source.py`（15）、`test_verify_all_weights.py`（15）、`test_feature_ablation.py`（11）、`test_model_registry_parity.py`（11）等。

前端 65 条分布：`CommitDetail.spec.js` 12、`api.spec.js` 10、`errors.spec.js` 9、`risk.spec.js` 7、`request.spec.js` 6、`syncProgress.spec.js` 6、`RiskList.spec.js` 5、`datetime.spec.js` 5、`features.spec.js` 3、`models.spec.js` 2。

## 6 用例设计方法

用例按等价类划分和边界值分析设计，不做随机凑数。

**等价类划分**——把每个输入域切成有效类和无效类，各取代表值：

| 输入 | 有效类 | 无效类 |
|---|---|---|
| `commit_hash` | 40 位十六进制（小写 / 大写 / 混合大小写） | `None`、空串、39 位、41 位、非十六进制字符（`g`/`z`）、含标点 |
| 分页 `size` | 1 ~ 100 | 0、负数、101 及以上 |
| `X-API-Key` | 与配置值精确匹配 | 缺失、空串、错误值 |
| 模型名 | 注册表内已交付模型 | 未注册、大小写不符、空串 |
| 空结果集 | 有数据 | 空库（`jit_test` 清空） |

**边界值分析**——取边界及其紧邻值：

| 字段 | 取值 |
|---|---|
| `commit_hash` 长度 | 39 / **40** / 41 |
| 分页 `size` | 0 / 1 / 100 / 101 |
| 关键字 `q` 长度 | 64 / 65 |
| 前端风险阈值 | 0.1999 / **0.2** / **0.5** |
| 并发用户数 | 10 / 20 |

**参数化**：27 个后端测试文件中有 7 个使用 `@pytest.mark.parametrize`，典型为 `test_security_boundaries.py`（50 条鉴权与参数用例）和 `test_validate.py` 的非法输入矩阵（`None`、`""`、`a*39`、`a*41`、`g*40`、`z*40`、末尾标点）。

**结构**：用例统一按 Arrange–Act–Assert 三段组织——先准备输入与夹具，再执行被测操作，最后对业务语义断言。

**执行时间**：纯单元层（`-m unit`）约 30 秒，全量含集成层约 46 秒，均在指南要求的 1 分钟以内。

## 7 AI / 手写用例比例

每个测试文件头都有考核说明 §2.1 格式的来源比例注释。按文件级标签汇总：

| 标签 | 文件数 | 用例数 |
|---|---:|---:|
| `[AI生成]` | 11 | 102 |
| `[AI生成-人工修改]` | 42 | 411 |
| `[手写]` | 4 | 21 |

标签由 AI 依据代码特征建议，作者确认后采纳；生成这批用例的提示词按模块归档在 [`prompts/`](prompts/)，共 4 份。

## 8 核心断言复核

涉及鉴权码、错误码、风险概率区间、14 维特征列序、DSN 拼装、SZZ 标签这 6 类业务口径的断言，逐项与产品代码比对过，7 项全部一致：

| 断言口径 | 比对结果 | 证据 |
|---|---|---|
| 鉴权码 40100 → HTTP 401 | 一致 | `errors.HTTP_BY_CODE[40100] == 401` |
| 统一错误码集合 | 一致 | 实际 `{0, 40001, 40100, 40400, 50000}` |
| 14 维特征数量 | 一致 | `config.FEATURE_COLUMNS` 共 14 项 |
| 14 维特征列序 | 一致 | 与 `feature_order.txt` 逐项相同 |
| DSN 拼装格式 | 一致 | `mysql+pymysql://…?charset=…` |
| 风险概率区间 | 一致 | `model_registry.py` 含边界裁剪 |
| SZZ 三态文案 | 一致 | 页面含「引入缺陷 / 非缺陷 / 无标记」 |

覆盖的测试文件共 33 个（断言里出现上述 6 类口径之一的），其余文件只做纯函数或辅助断言，未涉及核心业务判断。

**审核记录**：2026-11-17 对 `1d6b06c` 复核，7 项全部通过，未修改任何断言。
