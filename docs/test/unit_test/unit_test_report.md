# 单元测试说明

> **状态：已按 `2734c1b` 实跑**（2026-11-15，本机 Windows + conda `jit-defect-prediction`）。下面每个数字都是本轮跑出来的，不是抄历史记录；跑法和原始日志都能对上。
>
> 依据：[`../../common/test-assessment-guide.md`](../../common/test-assessment-guide.md) §2；本文件对应「单元测试说明文档」交付物（测试模块、用例数量、覆盖率数值、运行命令、AI/手写比例统计）。
>
> **目录约定**：`docs/test/` 只放文档与报告，测试代码的唯一真源在仓库各端目录。

## 1 · 测试范围与代码位置

| 线 | 唯一真源 | 配置绑定 | 覆盖重点 |
|---|---|---|---|
| 后端 | `backend/tests/` | `backend/pytest.ini` 的 `testpaths = tests`、CI `--cov=app` | 鉴权 40100、参数校验 40001、风险概率 `[0,1]`、14 维特征列序、服务层与错误包络 |
| 模型线 | `data_model/tests/` | `data_model/pytest.ini` | SZZ 标签 0/1/null、时间序切分、Effort 边界、特征抽取纯函数、权重校验 |
| 前端 | `frontend/tests/` | `frontend/vite.config.js` 的 vitest 配置 | 纯函数、工具方法、请求层与组件契约 |
| 基础设施 | `infra/tests/` | CI 契约检查 | 建库脚本的纯函数解析 |

## 2 · 环境与前置（先说坑）

| 项 | 值 |
|---|---|
| 操作系统 | Windows 11（win32） |
| Python | 3.12.14，conda 环境 `jit-defect-prediction`（`D:\workspace\env\miniconda3\envs\jit-defect-prediction`） |
| pytest / pytest-cov | 9.1.1 / 7.1.0；FastAPI 0.141.1、SQLAlchemy 2.0.54 |
| Node | v24.18.0（`npm` 11.16.0） |
| MySQL | 本机 8.0，`jit_demo`（演示库）与 `jit_test`（pytest 库，`conftest` 会 drop/create 五表） |
| 被测提交 | `2734c1b` |

**一个必须说清楚的前置**：干净检出的仓库里没有 `backend/static/` 目录（该目录下的图集生成物已移出版本控制），而 `app/main.py:101` 会无条件 `StaticFiles(directory=...)` 挂载它，于是 `from app.main import create_app` 直接抛 `RuntimeError: Directory '...\backend\static' does not exist`，pytest 连用例都收集不到。本轮先手工 `New-Item -ItemType Directory backend/static/figures` 才能开跑。这条已登记为缺陷（见 [`../system_test/bug_list.md`](../system_test/bug_list.md) BUG-01），长期修法是在 `create_app()` 里加一行 `mkdir(parents=True, exist_ok=True)`，而不是靠每个人记着手工建目录。

## 3 · 执行结果（本轮实测）

| 线 | 命令 | 结果 | 耗时 |
|---|---|---|---|
| 后端 | `cd backend && python -m pytest -q` | **254 passed**，0 failed / 0 error / 0 skipped | 35.4s（JUnit 计时；含模型与 DB fixture 约 45s 墙钟） |
| 后端覆盖率 | `python -m pytest -q --cov=app --cov-branch --cov-report=term-missing --cov-report=html:../docs/test/unit_test/coverage_report/htmlcov-2734c1b` | 行覆盖 **87.2%**、分支 **76.2%**、综合 85.2% | 同上 |
| 模型线 | `cd data_model && python -m pytest -q` | **162 passed** | 43.2s |
| 前端 | `cd frontend && npm run test:unit` | **59 passed / 9 个测试文件** | 35.5s |
| 基础设施 | `python -m pytest -q infra/tests` | **8 passed** | 0.11s |
| CI 契约 | `python -m unittest discover -s .github/ci/tests -p 'test_*.py'` | **11 passed** | 0.002s |
| OpenSpec 结构 | `python openspec/check_structure.py` | 10 个进行中 change，**0 error** | 秒级 |
| 合计 | — | **494 条全部通过** | 约 2 分钟 |

四条线都是「一次跑全绿、不需要手工改配置」（除了上面那个 `backend/static` 目录），也没出现 flaky——本轮把后端连跑了 3 遍（带覆盖率一次、JUnit 一次、纯跑一次），结果一致。

## 4 · 覆盖率

| 项 | 实测 | 说明 |
|---|---|---|
| 行覆盖率 | **87.2%** | 1333 / 1528 语句覆盖 |
| 分支覆盖率 | **76.2%** | 256 / 336 分支覆盖（另有 40 个分支只走到一半，80 个完全没走） |
| 综合（HTML 首页显示值） | **85.2%** | coverage 的 line+branch 合并口径，`index.html` 页头就写这个数 |
| HTML 报告 | **已归档本 SHA**：[`coverage_report/htmlcov-2734c1b/index.html`](coverage_report/htmlcov-2734c1b/index.html) | 目录里的 `.js`/`.css`/图标是报告渲染资源，不是代码副本 |
| PDF 截图 | 待人工 | 课程要求「HTML 报告 + PDF 截图」，截图必须人工采集 |

覆盖率按模块看，短板集中在这几个文件（也是下一轮补测该下手的地方）：

| 文件 | 行覆盖 | 主要缺口 |
|---|---:|---|
| `app/api/figures.py` | 30% | 指标 CSV 读取与 404 分支未覆盖 |
| `app/api/models.py` | 38% | 线过滤与空清单分支 |
| `app/e2e_source.py` | 55% | CodeBERT 懒加载路径外包着环境判断，本机无权重即跳过 |
| `app/main.py` | 72% | lifespan 与启动同步分支 |
| `app/services/git.py` | 73% | fetch/worktree 失败分支 |

覆盖率高的：`api/predict.py`、`auth.py`、`explain.py`、`feature_source.py`、`models.py`、`schemas.py`、`timeutil.py`、`validate.py` 均 100%，`api/commits.py` 99%。

## 5 · 用例分布

后端 254 条按文件：

| 文件 | 条数 | 文件 | 条数 |
|---|---:|---|---:|
| `test_security_boundaries.py` | 50 | `test_services_git.py` | 9 |
| `test_commits_api.py` | 22 | `test_trends_api.py` | 9 |
| `test_model_registry.py` | 19 | `test_validate.py` | 9 |
| `test_sync_api.py` | 18 | `test_db.py` | 7 |
| `test_mirror.py` | 15 | `test_explain.py` | 6 |
| `test_timeutil.py` | 14 | `test_feature_source.py` | 6 |
| `test_predict_api.py` | 13 | `test_schema_sql.py` | 5 |
| `test_config.py` | 10 | `test_integration_api.py` | 5 |
| `test_online_models.py` | 10 | `test_diff.py` / `test_errors.py` / `test_health_api.py` | 4 / 4 / 4 |
| `test_services_commits.py` | 9 | `test_auth_errors.py` / `test_trends_sql.py` | 3 / 3 |

模型线 162 条里块头最大的是 `test_szz_labeling.py`（42，其中 `TestIsFixCommit` 19 条）、`test_text_source.py`（15）、`test_verify_all_weights.py`（15）、`test_feature_ablation.py`（11）、`test_model_registry_parity.py`（11）、`test_effort_budget.py`（9）。

前端 59 条：`CommitDetail.spec.js` 10、`api.spec.js` 10、`errors.spec.js` 9、`risk.spec.js` 7、`request.spec.js` 6、`RiskList.spec.js` 5、`datetime.spec.js` 5、`models.spec.js` 4、`features.spec.js` 3。

## 6 · AI / 手写用例比例统计

按文件统计来源标签（本轮用脚本扫的，不是估的）：

| 线 | 测试文件 | 含来源标签的文件 | 标签出现次数 |
|---|---:|---:|---|
| 后端 | 23 | 12 | `[AI生成]` 8、`[AI生成-人工修改]` 4 |
| 模型线 | 16 | 1 | `[AI生成]` 1 |
| 前端 | 9 | 7 | `[AI生成]` 2、`[AI生成-人工修改]` 5 |
| 基础设施 | 1 | 0 | — |

后端未标来源的 11 个文件：`test_auth_errors.py`、`test_config.py`、`test_db.py`、`test_health_api.py`、`test_integration_api.py`、`test_model_registry.py`、`test_schema_sql.py`、`test_security_boundaries.py`、`test_sync_api.py`、`test_trends_api.py`、`test_trends_sql.py`；模型线未标的 15 个；前端未标的 `api.spec.js`、`request.spec.js`。

各线「AI / 手写」条数比例仍然是**待核**——标签只到文件级，没有逐条记录，也不存在可回溯的原始提示词。按红线不能倒填，所以就停在这里：AI-R1 缺来源标注、AI-R2 缺提示词归档的扣分风险照实申报，不补「还原版」。

文件头也不符合 §2.1 要求的比例注释格式（现有的是单行 `# [AI生成]`）：

```python
# === AI 辅助说明 ===
# 本文件共 12 条测试用例
# [AI生成]：7 条（经人工审核修改后采纳）
# [AI生成-人工修改]：3 条（AI 生成骨架，人工补充核心断言）
# [手写]：2 条（核心业务断言由人工编写）
# 使用工具：通义灵码 / GitHub Copilot
# 提示词见：prompts/unit_test_predict.md
```

整改要按**实际**统计填，由各线作者在做，不在文档侧代填。

## 7 · AI 来源审核

- 核心断言（概率区间、鉴权码、14 维列序、数据一致性）须人工编写或逐条复核（AI-R4）；本轮我只跑了用例、没动断言，复核仍待各线作者。
- 模型线 `test_model_registry_parity.py` 会 import `pipelines/{expert,fused,semantic}.model`，需要 torch / lightgbm / xgboost / pytorch-tabnet 齐备，缺包会直接失败——本机环境齐备，故全绿；换机器时这是首个要确认的依赖。
- 前端覆盖率本轮没跑出来：`node_modules` 里缺 `@vitest/coverage-v8`（`package.json` 与 `package-lock.json` 里都有，属本地依赖未装全），`npm run test:unit -- --coverage` 会直接报 `MISSING DEPENDENCY`。执行 `npm ci` 即可，属待办而非产品缺陷。

## 8 · 2026-11-15 修复轮补充：分层与增量

本轮代码修复（PR #244，对应 #225/#226/#227/#228/#233/#239/#240/#241/#242）后，补充以下增量；§3/§4 的历史数字保留为 `2734c1b` 基线，不回填成新结果。

- **`backend/static` 不再需要手工建**：`create_app()` 会创建目录并从 `data_model/pipelines/*/reports/figs_by_model/` 补齐图集（#239/#240）；§2 的 `New-Item` 前置已失效。
- **后端按夹具自动分层**（`backend/pytest.ini` 注册 `unit` / `integration`）：
  - `test_<行为>` 若请求 `client` / `engine` / `integration_db` / `populated_api` 夹具 → `integration`；
  - 其余 → `unit`；直接连库、不走夹具的 `test_db.py` 在文件内声明 `pytestmark = pytest.mark.integration`；
  - 新增 `test_figures_api.py`（3 条）与 `test_online_inputs.py`（3 条），后端由 254 条增至 **261 条**。
- **分层跑法（实测）**：
  ```bash
  cd backend
  # 纯单元：把 DB 指向不可达地址也能全绿，证明不连库
  TEST_DATABASE_URL='mysql+pymysql://x:x@127.0.0.1:1/x' python -m pytest -m unit
  # → 121 passed / 140 deselected
  TEST_DATABASE_URL='mysql+pymysql://x:x@127.0.0.1:1/x' python -m pytest -m unit --cov=app --cov-report=term
  # → 行覆盖 66%（1698 语句 / 585 未覆盖）
  # 集成：连 jit_test
  python -m pytest -m integration
  # 全量
  python -m pytest -q
  # → 261 passed / 0 failed
  ```
- **前端**：移除 `loadOnlineModels` 后同步删除 2 条过时单测，`npm run test:unit` → **57 passed / 9 files**；`v-loading` 已注册 noop 指令，不再出现 Vue warn。
- 覆盖率报告仍以测试线重跑为准；本节只登记分层命令与增量条数。
