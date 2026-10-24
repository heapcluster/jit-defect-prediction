# 单元测试报告 · Sprint 2（快照 2026-10-24）

> 课程《项目要求》Sprint 2（10/23–11/13，见 `repo/sprints.md` §1）的交付物「单元测试报告」。
> 结构与口径沿用 `common/test-report-sprint1.md` 与 `common/test-plan.md` §5；evidence 索引按 `test-plan.md` §6 收在本文件 §8，不另建第三份清单。
> **Sprint 2 未结题**：本文件是第一版快照，基线 main `0773a49`（2026-10-24 合入 #85 后的 main）。结题（11/13）前按 §8 末尾的规矩更新一次，**不在本文件的旧数字上倒填**。
> 统稿：吕建江（后端线，本轮牵头）｜ 供稿：蒋励（模型线用例）、刘帅华（前端线用例）、苏哲勋（CI 门禁）

## 0. 一句话结论

三线单测在本机与 CI 上**全绿**：后端 **145** 条、模型 **103** 条（1 条按设计 skip）、前端 **10** 条，0 failed / 0 error；后端行覆盖 **92.13%**（699 stmts / 55 miss），A、B 两条解释器路径**逐模块差异 0 处**；CI 的 lint→test→build 共 16 步在 main `0773a49` 全部 success（[run 40057502145](https://github.com/heapcluster/jit-defect-prediction/actions/runs/40057502145)）。

**仍缺的不是单测，是单测以上三层**：集成（T-IT-01~03）、系统（T-ST-01~05）、非功能（T-NF-01~04）都还没有 Sprint 2 口径下的正式执行记录，其中性能与安全两份旧证据已因 #97 改接口而**不可再引**（§8）。差距逐条见 §7。

## 1. 执行环境（如实记录，含「没跑」的部分）

| 项 | 值 |
|---|---|
| 被测树 | 分支 `docs/backend/sprint2-unittest-report` @ `0773a49`；本分支只新增本文件，`backend/`、`data_model/`、`frontend/` 与 main 逐字一致（核对命令见 §3.4） |
| 操作系统 | Windows 11（10.0.26200），本机实测 |
| 解释器 **A** | 仓库根 `.venv`（不入库、各人自建），Python **3.12.7** |
| 解释器 **B** | conda 环境 `jit-defect-prediction`（按 `data_model/environment.yml` 建，#83 之后唯一权威清单），Python **3.12.15** |
| Python 侧依赖 | pytest 9.1.1 / coverage 7.16.2 / pytest-cov 7.1.0 / fastapi 0.141.1 / SQLAlchemy 2.0.54（A、B 版本一致） |
| 前端侧 | Node **v24.15.0** / npm **11.12.1**；`npm ci` 实装 **223 packages**（28s，走本机代理 127.0.0.1:7897）；vitest 5.0.5 / vite 8.3.0 |
| 静态检查 | ruff **0.16.8**（`ruff check backend data_model infra` → All checks passed）、eslint 10.12.0（`npm run lint` → 0 problem） |
| 数据库 | SQLite（后端夹具 `backend/tests/conftest.py`，按 `backend/api-spec.md` §5 variant 口径）。**MySQL 未参与本报告任何数字**，原因见 §6 与 §7 |
| 模型权重 | 后端用夹具模型（决策树 / 线性 Pipeline，`conftest.py` 现造），模型线用合成小样本；`.pkl` 被 `.gitignore` 排除，故干净 clone 有 1 条按设计 skip（§2.2） |
| CI | GitHub Actions `ubuntu-24.04`，工作流 `.github/workflows/ci.yml`（#72 落地、#92 修安装与 lint 阻断）；main `0773a49` 的 run **success**，16 步全绿，03:15:17Z→03:18:09Z |
| 测量时间 | 2026-10-24 12:45–12:50（+08:00） |
| **计数口径** | 一律不取终端回显。本机 shell 会吞掉 pytest 末行汇总，故条数取自 `--junitxml` 的 `testsuite@tests/failures/errors/skipped`，覆盖率取自 `--cov-report=json` 的 `totals` 与逐文件 `summary`/`missing_lines`，前端取自 vitest 自身汇总行。原始产物只落本机临时目录，不入库 |

## 2. 执行结果

### 2.1 三线汇总

| 层 | 命令（cwd） | 用例数 | 通过 | 失败 | 错误 | 跳过 | 耗时 |
|---|---|---|---|---|---|---|---|
| 单元 · 后端 | `cd backend && python -m pytest tests/ -q` | **145** | 145 | 0 | 0 | 0 | A 5.641s / B 6.321s |
| 单元 · 模型 | `cd data_model && python -m pytest tests/ -q` | **103** | 102 | 0 | 0 | **1**（按设计） | 10.458s |
| 单元 · 前端 | `cd frontend && npm run test:unit` | **10** | 10 | 0 | 0 | 0 | 277ms（2 文件） |
| 静态检查 | `ruff check backend data_model infra`；`cd frontend && npm run lint` | — | 通过 | — | — | — | ruff 0 problem / eslint 0 problem |
| 构建 | `cd frontend && npm run build`；`python -m compileall -q backend/app data_model infra` | — | 通过 | — | — | — | vite 673ms，2248 modules；有 chunk >500kB 警告（§2.5）。compileall 本机 rc=0（A 解释器，与 CI 第 16 步同命令） |
| **集成** | — | **0** | — | — | — | — | T-IT-01~03 未正式执行；`test_integration_api.py` 6 条是**套件内 SQLite 级**联调，不等价（§2.2 注） |
| **系统** | — | **0** | — | — | — | — | 仅 `repo/demo-script-sprint1.md` 手工脚本，Sprint 3 收口 |
| **非功能** | — | **0** | — | — | — | — | 性能/安全两份旧证据已失效，需重跑（§8） |

warnings：后端 1 条（`fastapi/testclient.py` 的 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`，非本线代码）；模型线若干条 sklearn `FutureWarning`（`SVC(probability=True)` 在 1.9 弃用、1.11 移除，来自三线 `model.py` 的既有口径：`expert/model.py:143`、`fused/model.py:62`、`semantic/model.py:72`，本轮未通过改配置或加依赖消除）。两者都不影响判定，也**没有**被静默过滤掉。

### 2.2 后端 145 条按文件（junitxml 计数）

| 文件 | 条数 | 首次入 main | 现在覆盖什么 |
|---|---|---|---|
| `tests/test_auth_errors.py` | 3 | #30 `44ca43f` | 缺令牌 → 401/40100、错令牌 → 401/40100、成功响应仍是 `{code:0,message:"ok",data}` 包络（T-BE-04；令牌空白/大小写/超长/前缀等变体在 `test_security_boundaries.py`） |
| `tests/test_commits_api.py` | 13 | #30 `44ca43f` | 列表分页与 `risk_score` 降序、`size` 越界/上限边界、`min_risk` 空结果集非错误、详情返回 14 特征 + `explanation`、提交存在但无预测 → `risk_score`/`model_name` 为 null、未知哈希 40400、哈希格式非法 40001、默认模型取版本序最新而非最近写入、时间区间闭区间语义 4 条（#62）（T-BE-01/02） |
| `tests/test_db.py` | 3 | #79 `62f6a18` | 建表后索引自检 `_assert_indexes()` 正例 + 反例（关闭 Issue #73 的一半） |
| `tests/test_ingest.py` | 2 | #30 `44ca43f` | `commits` 灌库重复执行幂等（同键不产生第二行）、缺必需键时整批回滚 |
| `tests/test_integration_api.py` | 6 | #99 `065c83a` | 独立 SQLite engine 上「建表 → `ingest()` 四类 CSV 各灌两遍验幂等 → 预测后查询、重复预测只留一行 → 周/月聚合与闭区间对得上灌入数据 → 缺预测/缺特征仍守契约形状 → 空库查询不是错误 → 鉴权失败与模型加载失败都不泄露内部信息」。这是**套件内**集成：夹具模型 + 合成 CSV + SQLite，不含 MySQL、真实权重与前端，故不能顶替 T-IT-01~03 |
| `tests/test_mirror.py` | 8 | #30 `44ca43f` | 导出 `openapi.json` 与契约三逐字段比对（规格「Swagger 实现镜像」） |
| `tests/test_model_registry.py` | 14 | #47 `4e72bf8` | `joblib.load` 口径、特征数自检、SHAP 解释键名 ∈ 14 特征、线性 Pipeline 加性残差归零；#96 交付清单加载 2 条、#99 导入路径与失败汇总 7 条（T-BE-06 / T-MO-02 / T-MO-03） |
| `tests/test_predict_api.py` | 12 | #30 `44ca43f` | 在线预测正向、`model_name` 回显、幂等（同键只留一行）、#97 新提交现算 14 维特征后在线预测 3 条（T-BE-03） |
| `tests/test_schema_sql.py` | 25 | #100 `f5ca61d` | `infra/schema.sql` 静态校验：四表列名/类型/主键/索引与契约一一致、幂等（`IF NOT EXISTS`）、禁止语句（DROP/TRUNCATE/DELETE 等 11 条参数化）、漂移负例 8 条 |
| `tests/test_security_boundaries.py` | 50 | #71 `501dc06` | 鉴权边界 **12** 条（四接口一律需令牌、令牌须逐字相等、错误提示不透露哪一位错）、查询参数边界 **14** 条（`page`/`size`/`min_risk`/时间非法 → 40001，边界合法值不误判）、详情/预测/趋势边界 **19** 条（哈希长度与非十六进制、缺字段、模型不在清单、粒度枚举、时间格式）、信息泄露断言 **5** 条（响应体不含 Traceback / SELECT / sqlalchemy / `.py` / 路径 / site-packages；50000 文案通用化）。#101 再 +2：`G`×40 大写非十六进制同样拒收、归一化后库内没有的哈希仍 40400，并把原「钉住错误行为」的一条改写为「归一化后命中同一提交」（T-BE-05 / T-NF-02） |
| `tests/test_trends_api.py` | 9 | #30 `44ca43f` | 周聚合、月粒度按自然月分桶、粒度枚举非法 → 40001、空区间非错误、`end` 纯日期含当天/带时间分量不变、紧凑 basic 格式拒收、周下钻周一至周日保住周日（#79 补月粒度 3 条 + 周下钻 1 条，关闭 Issue #73 的一半） |
| **合计** | **145** | | |

> 分组条数是本轮按「源文件里 `def test_` 所在小节 × junitxml 收集到的用例名」实算的，不是照抄旧报告。顺带查出一处旧口径错误：`test-report-sprint1.md` §2.1 把 `test_security_boundaries.py` 的 48 条拆成 12/19/16/4，**四项相加是 51、对不上 48**；按同一算法回推当时的正确拆分应为 12/14/17/5（=48），#101 的 +2 全落在「详情/预测/趋势边界」→ 19。Sprint 1 报告是历史文件，按「历史记录不改」保留原文，订正记在本行。

### 2.3 模型线 103 条按文件

| 文件 | 条数 | 首次入 main |
|---|---|---|
| `tests/test_szz_labeling.py`（5 个 class：IsFixCommit 19 / MergeRanges 7 / ParseOldRanges 6 / CamelSelfcheckReport 7 / BlameCacheKey 3） | 42 | #71 `501dc06` |
| `tests/test_split_dataset.py`（ValidateSplit 6 / SplitIndex 4 / SortKey 4 / ParseTs 3） | 17 | #71 `501dc06` |
| `tests/test_model_registry_parity.py` | 10 | #71 `501dc06` |
| `tests/test_effort_budget.py` | 9 | #71 `501dc06` |
| `tests/test_feature_contract.py` | 8（**1 条 skip**） | #71 `501dc06` |
| `tests/test_embedding_cache.py` | 6 | #71 `501dc06` |
| `tests/test_official_entry_import.py` | 4 | #71 `501dc06` |
| `tests/test_fused_report_coverage.py` | 3 | #86 `3a9b7b0` |
| `tests/test_single_commit_features.py` | 3 | #95 `8fdaf23` |
| `tests/test_camel_source.py` | 1 | #68 `11993e2` |
| **合计** | **103** | |

唯一 skip：`test_feature_contract.py::test_manifest_models_exist_on_disk` —— 断言交付清单里声明的 `.pkl` 在磁盘上真实存在，而 `*.pkl` / `*.joblib` 被 `.gitignore` 排除（硬红线三：不提交模型文件），干净 clone 必然 skip。**这不是漏测**，有权重的机器上该条会实跑；CI 上同样是 skip 而非 fail。

Sprint 1 快照（`test-report-sprint1.md` §2）时模型线只有 `test_feature_contract.py` **8** 条，本轮 103 条中的 95 条来自 #71/#86/#95/#68 四个 PR。模型线的**主验收口径仍是复现一致性（±0）**（`test-plan.md` §5），单测是配套而非替代。

### 2.4 前端 10 条

| 文件 | 条数 | 断言什么 | 对应编号 |
|---|---|---|---|
| `tests/request.spec.js` | 6（2 条 `it` + 1 组 `it.each` 展开 4 条） | HTTP 200 成功包络只回 `data`；400/401/404/500 四档保留业务码 40001/40100/40400/50000 并映射到固定文案；500 档把服务端细节（用例里是 `private server path`）替换成「服务异常，请稍后重试」= **不回显**；无业务包络的网络错误按原错误传递 | T-FE-03 |
| `tests/risk.spec.js` | 4 | 阈值 ≥0.5 高 / ≥0.3 中 / 其余常规，含边界值归上一档（0.5 是高不是中） | T-NF-04（阈值单一来源） |

**这两份是 main 上前端的全部单测。** Sprint 1 报告 §6 写的 `frontend/src/__tests__/contract.test.js`（声称覆盖 T-FE-01~03）**从未进 main**：它只存在于未合入的 PR #70/#71 分支提交 `8cf3c78`；#71 最终合入 main 的 squash 提交 `501dc06` 只带进了 `backend/tests/test_security_boundaries.py` 与 `data_model/tests/`，`git show --stat 501dc06 | grep frontend` 只有 `docs/frontend/README.md`。因此：

- **T-FE-01（加载中 / 空数据 / 失败三态）当前覆盖 0 条**；
- **T-FE-02（页面字段 → `api-spec.md` 逐字段映射）当前覆盖 0 条**；
- T-FE-03 由 `request.spec.js` 实覆盖（比 Sprint 1 报告的「🔶 待组件测试」更强，可改判 ✅ 接口层）。

这属 `test-plan.md` §4.1 的状态列需要订正 + 前端线补两条用例，不是后端线能代办的；已在本报告登记，不在本 PR 里改 `test-plan.md`（那是蒋励统稿的公共文档，且改状态列属另一件事）。

### 2.5 构建与静态检查的已知告警（不阻断，但不藏）

`npm run build` 成功，产物 `dist/index.html` 0.40 kB、`index-*.css` 363.09 kB、`index-*.js` **2,194.19 kB（gzip 720.04 kB）**，vite 报 chunk 超过 500 kB 的告警（echarts + element-plus 全量打进一个 chunk）。这不影响单测结论，属前端线的打包优化项（`build.chunkSizeWarningLimit` / 动态 `import()` 代码分割），登记在此备查。

## 3. 覆盖率（后端 `--cov=app`）

### 3.1 本次实测：92.13%

| 模块 | Stmts | Miss | Cover | 未覆盖行 |
|---|---|---|---|---|
| `app/api/commits.py` | 86 | 0 | **100%** | — |
| `app/api/predict.py` | 79 | 14 | 82% | 50, 77-80, 83-84, 111, 113-114, 118-121 |
| `app/api/trends.py` | 36 | 0 | **100%** | — |
| `app/auth.py` | 8 | 0 | **100%** | — |
| `app/config.py` | 12 | 0 | **100%** | — |
| `app/db.py` | 48 | 15 | 69% | 22-25, 57-62, 64-67, 71 |
| `app/errors.py` | 32 | 3 | 91% | 33, 58-59 |
| `app/feature_source.py` | 19 | 1 | 95% | 17 |
| `app/ingest.py` | 84 | 7 | 92% | 109-112, 114-115, 119 |
| `app/main.py` | 22 | 0 | **100%** | — |
| `app/model_registry.py` | 158 | 15 | 91% | 56, 63-64, 69-70, 123-127, 191, 211-213, 241 |
| `app/models.py` | 56 | 0 | **100%** | — |
| `app/schemas.py` | 59 | 0 | **100%** | — |
| **TOTAL** | **699** | **55** | **92.13%** | — |

（`app/__init__.py`、`app/api/__init__.py` 为 0 stmts，计入 JSON 但不影响 TOTAL。）

- **A 与 B 逐模块比对差异 0 处**（对比两份 coverage JSON 每个文件的 `num_statements`、`missing_lines` 整数与行号列表）。Python 3.12.7 与 3.12.15 之间没有差异，`coverage-2026-10-22.md` §5 留的「B 未复测」口子已在 10-24 那次补上，本次再次确认。
- 口径：**行覆盖**（两份 JSON 的 `meta.branch_coverage` 均为 `false`），与此前各次测量一致，可直接纵向比。
- 目标核对：`test-plan.md` §5「后端行覆盖 Sprint 2 ≥60%」→ **92.13%，达标（余量 32.13 个百分点）**；「Sprint 3 ≥75%」→ 已提前超过，但**不作为 Sprint 3 免测理由**，Sprint 3 仍需按当时 main 复测。
- 统计范围只有 `--cov=app`：**不含** `backend/scripts/`（压测 / 安全 / 灌库脚本，其产出由 §8 索引的 `perf-*.md` / `security-*.md` 验证）与 `backend/tests/`。

### 3.2 六次基线对照（覆盖率为什么从 84% 到 92%）

| # | 基线 | 触发 PR | 测试条数 | Stmts | Miss | TOTAL | 出处 |
|---|---|---|---|---|---|---|---|
| 1 | `59ad7ed` | 首测（2026-10-16） | 39 | 595 | 97 | 84% | `coverage-2026-10-16.md` |
| 2 | `0cad776` | #62 时间区间语义 | 45 | 600 | 95 | 84% | 同上补记 |
| 3 | `501dc06` | #71 四线独立成包 | 93 | 600 | 91 | 85% | `coverage-2026-10-17.md` |
| 4 | `e46624b` | #75/#79/#78/#81 | 100 | 600 | 80 | **87%** | `coverage-2026-10-22.md` |
| 5 | `065c83a` | #94–#100 + #99 | 143 | 698 | 55 | **92.12%** | `coverage-2026-10-24.md` |
| 6 | **`0773a49`** | **#82/#85/#101（本次）** | **145** | **699** | **55** | **92.13%** | 本文件 |

> 用户与看板关心的「87% → 92%」= 第 4 行到第 6 行；「87 条 → 145 条」= §4 的另一条链。**两个 87 不是一回事**（一个是覆盖率百分数、一个是 Sprint 1 报告里的用例条数），别在同一句话里混着写。

- **Stmts 595 → 699（+104）**：主要来自 #97 的 `app/feature_source.py`（+19，单条提交特征抽取入口）、`app/api/predict.py` 54→79（+25，现算特征 + 落库 + `IntegrityError` 回落）、#96/#99 的 `app/model_registry.py` 108→158（+50，`_delivery_models()` 清单解析 + `sys.path` 插入 + 失败汇总）、`app/api/commits.py` 77→86（+9，详情兜底改按该提交已有模型取版本序最新 + #101 的 `_check_hash` 归一化）、`app/config.py` 11→12（+1，`SOURCE_REPO`）。
- **Miss 97 → 55（−42）**，三段实质性关闭：
  - `app/ingest.py` 35 → **7**（−28）：#99 的 `test_integration_api.py` 真实调用 `ingest()` 灌四类 CSV 各两遍，三条灌库路径（原 36-44 / 48-60 / 64-72）全部命中；剩下 7 行是 CLI `main()` 与 `__main__` 守卫。
  - `app/db.py` 28 → **15**（−13）：#79 的索引自检正/反例命中 `_assert_indexes()` 本体（原 43-53）。
  - `app/api/trends.py` 1 → **0**、`app/api/commits.py` 8 → **0**：月粒度 `_period()` 分支（#79）与详情兜底/归一化分支（#99/#101）。
  - 反向增量：`app/api/predict.py` 7 → **14**（+7，#97 新增的 `session.flush()` 并发回落与 `SOURCE_REPO` 抽取失败分支，夹具触发不到）。
- **本次（143 → 145）Miss 一行未减**：#101 改的 `_check_hash` 归一化路径本来就在覆盖区内（`commits.py` 86 stmts / 0 miss），新增 2 条用例是**把已修行为钉住**（防回归），不是补覆盖率。这一点要写清，否则「加了 2 条测试覆盖率没动」会被读成测试无效。

### 3.3 覆盖率与用例数不是同一件事（本轮的口径提醒）

第 4→5 行是「用例 +43、覆盖率 +5.12pp」，第 5→6 行是「用例 +2、覆盖率 +0.01pp」。原因是覆盖率的分母（Stmts）同时在涨：**#97/#96/#99 一边加代码一边加测试**，所以 84%→92% 这 8 个点里，有相当部分是「新增代码自带测试」而非「补旧账」。旧账的关闭集中在 `ingest.py`（−28 miss）与 `db.py`（−13 miss）两处，其余模块的 miss 基本原地未动，逐行清单见 §6。

### 3.4 复现步骤

```bash
# ── 环境（二选一，结论要写清用的哪条）─────────────────────────────
# A：仓库根 .venv（不入库），期望 Python 3.12.7
.venv/Scripts/python.exe -c "import sys; print(sys.version.split()[0])"
# B：conda（#83 之后唯一装环境路径）
conda env create -f data_model/environment.yml     # 已建过则跳过
conda activate jit-defect-prediction
python -c "import sys; print(sys.executable)"      # 必须落在 .../envs/jit-defect-prediction/ 下
python -c "import fastapi, uvicorn, sqlalchemy, dotenv, pytest, pytest_cov; print('后端依赖 ok')"

# ── 三线单测 ────────────────────────────────────────────────────
cd backend   && python -m pytest tests/ -q                       # 期望 145 passed
cd data_model && python -m pytest tests/ -q                      # 期望 102 passed, 1 skipped
cd frontend  && npm ci && npm run test:unit                      # 期望 Test Files 2 passed / Tests 10 passed

# ── 覆盖率（终端汇总行在部分 shell 会被吞，取文件为准）─────────────
cd backend
python -m pytest tests/ -q --cov=app --cov-report=term-missing \
       --cov-report=json:<tmp>/cov.json --junitxml=<tmp>/junit.xml
#   junit.xml → testsuite@tests=145 failures=0 errors=0 skipped=0
#   cov.json  → totals.num_statements=699, totals.missing_lines=55, percent_covered=92.13

# ── 被测树与基线的等价性核对（cwd=仓库根，不依赖 remote 名）────────
git merge-base --is-ancestor 0773a49 HEAD && echo "含基线 0773a49"
git diff --name-only 0773a49 HEAD       # 期望：只有 docs/common/test-report-sprint2.md
```

> 覆盖率产物 `.coverage` / `htmlcov/`、前端 `node_modules` / `dist` 均在 `.gitignore` 内，不入库；`cov.json` / `junit.xml` 只落本机临时目录。

## 4. 用例数怎么从 87 涨到 145（本次要讲清的那件事）

Sprint 1 报告 §2 写的后端 **87** 条，是「当时 main 上的 39 条 + 本 PR 新增的 48 条安全/边界用例」的**分支内口径**；那 48 条要到 #71（`501dc06`）才随 squash 合入 main，而 main 在同期又先合入了 #62 的 6 条时间区间用例（39→45）。所以 main 上的真实链条是：

| 步 | 基线 | 变化 | 条数 | 来源 |
|---|---|---|---|---|
| 0 | `59ad7ed` | — | **39** | #30 六文件（auth/commits/ingest/mirror/predict/trends）+ #47 `test_model_registry.py` |
| 1 | `0cad776` | +6 | **45** | #62 时间区间闭区间语义用例 |
| 2 | — | （+48，在分支上） | *87* | **Sprint 1 报告里的那个 87**：45 条 main + 48 条安全/边界，尚未合入 |
| 3 | `501dc06` | +48 | **93** | #71 把 `test_security_boundaries.py`（48 条）带进 main |
| 4 | `e46624b` | +7 | **100** | #79：`test_trends_api.py` 月粒度 3 + 周下钻保周日 1、`test_db.py` 索引自检 3（关闭 Issue #73） |
| 5 | `065c83a` | +43 | **143** | #100 `test_schema_sql.py` 25 + #96/#99 `test_model_registry.py` 9 + #99 `test_integration_api.py` 6 + #97 `test_predict_api.py` 3 |
| 6 | **`0773a49`** | **+2** | **145** | #101：`test_security_boundaries.py` 新增 1 个函数（归一化后仍 40400）+ 1 个参数（`G`×40），并把原「钉住错误行为」的 `test_detail_uppercase_hash_passes_validation_but_not_found` 改写成 `test_detail_uppercase_hash_is_normalized_to_the_stored_commit`（D-09 修复） |

**87 → 145 的净增 58 条**里：安全/边界 50（#71 48 + #101 2）、`schema.sql` 静态校验 25（#100）、模型注册表 14（#47 起，#96/#99 各加）、套件内联调 6（#99）、索引自检 3（#79）、月粒度/周下钻 4（#79）、时间区间 6（#62）、在线预测现算特征 3（#97）。注意第 2 行的 *87* 是斜体：**它不是任何一个 main 基线上的数字**，引用时必须说明它是 Sprint 1 的分支内口径，否则会被人拿 `git log` 对不上。

模型线同期 8 → **103**（+95，见 §2.3），前端 0 → **10**（#81 4 条 + #94 6 条）。

## 5. 用例编号对照（`test-plan.md` §4.1 最小集 → 实现）

| 编号 | 方案里的期望 | 现状 | 实现位置 |
|---|---|---|---|
| T-BE-01 | 列表正常分页、按 `risk_score` 降序 | ✅ | `test_commits_api.py` |
| T-BE-02 | 空结果集 200 且 `items==[]`、`total==0` | ✅ | `test_commits_api.py` |
| T-BE-03 | 在线预测返回 `risk_score` + `explanation[]`，`model_name` 同名 | ✅ | `test_predict_api.py`（含 #97 现算特征 3 条） |
| T-BE-04 | 缺 `X-API-Key` → 401/40100，不回显内部信息 | ✅ | `test_auth_errors.py` |
| T-BE-05 | 畸形参数五类 + 边界合法值不误判 | ✅ | `test_security_boundaries.py`（50 条） |
| T-BE-06 | 模型注册表按 `joblib.load` 加载 + 特征数自检 | ✅ | `test_model_registry.py` |
| T-MO-01 | 14 项特征键名与 `feature-columns.md` 逐字一致（四处来源同一份有序清单） | ✅ | `data_model/tests/test_feature_contract.py` |
| T-MO-02 | 交付模型加载 + 特征数一致 | ✅ | `test_model_registry.py` |
| T-MO-03 | `explanation` 键名 ∈ 14 特征 | ✅ | `test_model_registry.py::_explain_of` |
| T-FE-01 | 三态（加载中 / 空数据 / 失败） | ❌ **0 条** | 声称覆盖它的 `contract.test.js` 未进 main（§2.4） |
| T-FE-02 | 页面字段 → `api-spec.md` 逐字段映射 | ❌ **0 条** | 同上 |
| T-FE-03 | 错误码 → 文案分发，50000 不回显堆栈 | ✅（接口层） | `tests/request.spec.js` 的 `it.each` 四档 |
| T-IT-01~03 | 真实库 + 真实模型 + 前端三页面一条链路 | ❌ 未执行 | `test_integration_api.py` 只是套件内 SQLite 级，**不能顶替** |
| T-ST-01~05 | 端到端主链路 + 异常输入 + 模型切换 + 回归 | ❌ 未执行 | 仅手工脚本 `repo/demo-script-sprint1.md` |
| T-NF-01 | `POST /api/predict` ×100 的 p50/p95/p99，p95<500ms | ❌ 证据已失效 | 旧 `perf-real-2026-09-20.md` 是 #97 之前的接口，不可再引（§8） |
| T-NF-02 | 缺令牌 + 畸形参数两组，不回显堆栈/SQL/路径 | 🔶 单测层 ✅、服务层证据已失效 | 单测：`test_security_boundaries.py` 的 5 条信息泄露断言；服务层需重跑 `scripts/security_cases.py` 并截图 |
| T-NF-03 | 空数据 / 断连重试 | ❌ 未执行 | 待 `design/non-functional.md` D2 章节定佐证口径 |
| T-NF-04 | 阈值只在 `frontend/pages.md` 一处定义 | ✅ | `tests/risk.spec.js` 4 条 |

**方案里没有编号、但 main 上已存在的 44 条**：`test_schema_sql.py` 25、`test_mirror.py` 8、`test_integration_api.py` 6、`test_db.py` 3、`test_ingest.py` 2。其中 `test_mirror.py` 对应规格「Swagger 实现镜像」Requirement、`test_schema_sql.py` 对应 `db-schema` 规格、`test_integration_api.py` 是 #99 的套件内联调、`test_db.py`/`test_ingest.py` 是 #30 起就有的建表与灌库用例。`test-plan.md` §3.2 要求「每条用例有 `T-` 编号并挂回 User Story」，这 44 条目前无编号 —— 需蒋励在 §4.1 补 T-BE-07~ 行，属方案侧欠账，不在本 PR 代改。

## 6. 未覆盖缺口（只登记，本报告不承诺修复）

与 `coverage-2026-10-24.md` §4 逐行一致（本次 miss 行号未变），共 55 行、7 组：

| # | 位置 | 未覆盖内容 | 为什么没覆盖 | 关闭它需要什么 |
|---|---|---|---|---|
| 1 | `app/api/predict.py:111,113-114,118-121` | `prediction` 写入的并发双插 `IntegrityError` 回落 | SQLite 触发不到唯一索引竞争 | 可起 MySQL 的并发夹具（缺授权，见下） |
| 2 | `app/api/predict.py:77-80,83-84`、`50` | #97 现算特征后 `flush()` 并发回落仍取不到 → 50000；已配 `SOURCE_REPO` 但单条抽取抛 `ValueError` → 40400 | 同上 + 需要真实 `data_model` 抽取链与真仓库 | 真实 Camel 仓库 + MySQL |
| 3 | `app/model_registry.py:63-64,69-70` | 清单 `[models]` 段非法文件名/重复名拒收、`[feature_order]` 段格式不合法拒收 | 现有负例改的是列名（`1. ns`→`1. wrong`，仍能被正则解析），走的是「列序与契约不符」分支 | 补 2 条纯夹具用例即可（**低成本，建议 Sprint 2 内做**） |
| 4 | `app/model_registry.py:56`、`123-127`、`191,211-213,241` | 清单空行/注释行 `continue`；XGBoost `get_booster().num_features()` 及其异常；`_first_row()` 收 list 形态 `shap_values`、解释器不可用降级 `[]`、`_background_for()` 命中 `_jit_background` | 夹具是 sklearn 决策树/线性 Pipeline，不构造这些形态 | 需要真实权重（森林返回三维数组、模型带背景数据） |
| 5 | `app/db.py:22-25,57-71`、`app/ingest.py:109-119` | `get_engine()` 懒建分支（含 `DATABASE_URL` 为空 → 50000）；两个模块的 CLI `main()` 与 `__main__` 守卫 | conftest 直接 `configure_engine`；测试不调命令行 | CLI 可用 `subprocess` 或 `monkeypatch sys.argv` 覆盖（低成本） |
| 6 | `app/errors.py:33,58-59` | `ok()` 辅助函数；全局未捕获异常 → 50000 兜底处理器 | `ok()` 当前无调用方；兜底需抛出非 `AppError` 的未处理异常 | `ok()` 无调用方本身是死代码信号，建议删或补调用（需另开 change） |
| 7 | `app/feature_source.py:17` | 抽取脚本 `spec is None or spec.loader is None` → `RuntimeError` | 需要 `data_model/preparation/03_extract_features.py` 缺失或不可加载 | 可用 monkeypatch 造不可加载模块（低成本） |

**MySQL 缺授权这件事必须写在报告里**：本机 `jit` 账号只有 `GRANT ALL PRIVILEGES ON jit_defect.*` 与全局 `USAGE`，**无 `CREATE DATABASE`**；而 `jit_defect` 里已有四表与 2/2/2/4 行演示占位数据，不是隔离空库，无法证明「从空库建四表 + 索引自检 + 灌库幂等 + 并发双插」。缺口 1、2 与 §7 的集成层执行都卡在这里，需苏哲勋用 root 建两个隔离空库（如 `jit_it` / `jit_perf`）并授权。

## 7. 与 `test-plan.md` §7 退出准则的差距（Sprint 3 验收前必须清零）

| # | 退出准则 | Sprint 1 快照 | **本次（Sprint 2 快照）** | 还差什么 |
|---|---|---|---|---|
| 1 | 四层用例全部执行，失败项有 Issue 且状态明确 | 单元 2/3 层已跑 | **单元 3/3 层已跑**（后端 145 + 模型 103 + 前端 10）；集成/系统/非功能仍 0 | 缺 3 层。集成层的第一块拼图是 §6 的 MySQL 隔离库 |
| 2 | 每核心功能 1 正向 + ≥1 异常通过证据 | 后端已覆盖；前端已写未跑 | 后端 ✅、模型 ✅、前端 🔶（T-FE-03/T-NF-04 ✅，**T-FE-01/02 为 0**） | 前端补三态与字段映射两组用例（刘帅华） |
| 3 | ≥1 条端到端集成/系统测试通过并留录屏 | 无 | 仍无正式记录；`test_integration_api.py` 6 条只是套件内 SQLite 级 | 三端联调实测记录（建库 → 4× ingest → 起服务看 `lr_v1/rf_v1/xgb_v1` 全加载 → 四接口各一发 → 同哈希 POST 两次只留一行），需 CSV 与库 |
| 4 | ≥2 项非功能出验证证据 | 方案在、证据未出 | 性能与安全两份旧证据**已失效**（#97 改了 `POST /api/predict` 的实现：现在会现算 14 维特征），必须重跑 | p50/p95/p99 压测 + 缺令牌/畸形参数两张截图；⚠ 见下方风险 |
| 5 | 缺陷处置记录可导出、五项齐全 | 已建索引（11 项） | `repo/defect-records.md` 现存 D-01~D-12，**两处需订正**：D-09 仍留在 §2「处理中」且写着「change/PR 待复审合入」、用例数写 132，而 #101 已以 `c011463` 合入 main（应迁入 §1、条数改 145）；D-10 的「未过 lint/build 实跑」半条已被本轮关闭（`npm ci` + lint 0 problem + build 成功 + 10 条单测通过），剩「无联调记录」半条仍成立 | 两条订正属公共文档，需蒋励/苏哲勋确认后另开 PR |
| 6 | CI 门禁跑通、单测随 PR 自动执行 | `.github/workflows` 为空 | ✅ **已达成**：#72 落地 + #92 修阻断，main `0773a49` run success，16 步全绿（含 `Test backend` / `Test frontend` / `Test data model` 三步与 `pull_request`+`push`+`merge_group` 三个触发） | 无。CI 内的具体条数本报告未逐条核对（日志需另取），条数一律以本机 junitxml 为准 |

**⚠ 准则 4 的已知风险（先说在前面，别等重跑时才发现）**：`backend/scripts/evidence/on-demand-commit-2026-10-23.md` 记录了一次函数级探测 —— 用本机已有权重、14 维全零向量对 `rf_v1` 连打 5 次，推理+解释耗时 **608.1 / 605.8 / 691.9 / 947.5 / 854.3 ms，全部超过 500ms**。那次探测不含 HTTP、数据库与真实输入，**不是正式 p95**，但它意味着「三模型交付清单」与「p95<500ms」这两个已冻结口径可能直接冲突。重跑 T-NF-01 有两种结局：达标（说明 SHAP 解释在真实链路上被摊薄/缓存），或不达标（则必须走契约变更或性能优化，不能把合成测试通过解释为非功能达标）。本文件不预判结论。

## 8. evidence 索引（`test-plan.md` §6：索引登记在本报告，不另建清单）

后端 evidence 全在 `backend/scripts/evidence/`，按「还能不能引」分三类：

| 文件 | 证明什么 | Sprint 2 可引性 |
|---|---|---|
| `coverage-2026-10-16.md` | 首测 39 条 / 595 stmts / 97 miss / 84%（main `59ad7ed`）+ #62 后 45 条补记 | ✅ 历史基线，只用于纵向比 |
| `coverage-2026-10-17.md` | #71 后 93 条 / 600 / 91 / 85%（`501dc06`） | ✅ 历史基线 |
| `coverage-2026-10-22.md` | #75/#79/#78/#81 后 100 条 / 600 / 80 / 87%（`e46624b`） | ✅ 历史基线 |
| `coverage-2026-10-24.md` | #94–#100/#99 后 143 条 / 698 / 55 / 92.12%（`065c83a`），A/B 双路径逐模块差异 0 | ✅ 历史基线 |
| **本文件** | **145 条 / 699 / 55 / 92.13%（`0773a49`）**，含模型 103、前端 10、CI 16 步 | ✅ **Sprint 2 现行口径** |
| `integration-time-range-2026-10-16.md` | 真起 uvicorn + 真发 HTTP（不用 TestClient）验时间区间闭区间语义，11/11 符合预期 | ✅ 可引（接口实现未变） |
| `predict-real-models-2026-10-16.md` | 真交付三权重（md5 逐一对上交付包）+ 真服务，`POST /api/predict` 15/15 符合预期，启动日志 `loaded models: ['lr_v1','rf_v1','xgb_v1']` | 🔶 结论仍可引，但**接口已被 #97 扩展**（新提交现算特征），需在本轮三端联调里重出一份 |
| `delivery-model-allowlist-2026-10-23.md` | `MODEL_DIR` 指向含 8 个 `.pkl` 的目录时注册表只载入交付清单三个；定向回归 16 passed | ✅ 可引 |
| `on-demand-commit-2026-10-23.md` | #97 合成联调（临时 Git 仓库 + 夹具模型）103 passed；**并记录 `rf_v1` 函数级探测 605–947ms 超 500ms** | ✅ 可引，且是 §7 准则 4 风险的原始出处 |
| `perf-placeholder-2026-09-19.md` | 占位模型 `tree_placeholder_v0` 下 p50 31.2ms / p95 33.8ms | ❌ **不可再引**：占位模型，且早于 #97 |
| `perf-real-2026-09-20.md` | 真 `xgb_v1.pkl` 下 p50 12.6ms / p95 21.6ms / p99 67ms | ❌ **不可再引**：测的是 #97 之前的 `POST /api/predict`（不现算特征）。Sprint 3 的 T-NF-01 必须重跑并另出 `perf-2026-11-*.md` |
| `security-2026-09-19.md`、`security-2026-09-20.md` | S1 缺令牌 / S2 错令牌 / S3 `size=101` / S4 `granularity=day` / S5 39 位哈希 等全 PASS | ❌ **不可再引**：早于 #96/#97/#99/#100/#101 五次改动，且无截图。需重跑 `scripts/security_cases.py` + 两张截图（缺令牌一张、畸形参数一张，须同时可见 HTTP 状态、`code`、以及响应体不含堆栈/SQL/路径） |

**更新规矩（沿用四份覆盖率文件自定的口径）**：Sprint 2 结题（11/13）前若再有 PR 合入带来测试数或覆盖率变化，**另出 `coverage-<日期>.md` 并更新本文件 §2/§3 的表与基线行号，不在旧文件里倒填数字**；本文件 §0 的「一句话结论」与 §3.2 的末行必须同步改，否则看板会引到过期数。

## 9. 本轮（2026-10-24）测试侧改动清单

- 新增本文件 `docs/common/test-report-sprint2.md`（Sprint 2 单元测试报告，合并此前四份散档的覆盖率证据口径）。
- 在 main `0773a49` 上重测三线单测与后端覆盖率（A/B 双解释器 + CI run 交叉核对），得到 145 / 103(1 skip) / 10 与 92.13%。
- 本机首次实装 `frontend/node_modules`（`npm ci` 223 packages）并实跑 `test:unit` / `lint` / `build`，关闭 Sprint 1 报告 §4 阻塞项 1 与 D-10 的「未过 lint/build 实跑」半条；**未改动 `frontend/` 任何入库文件**（`node_modules`、`dist` 均在 `.gitignore` 内）。
- 查清并登记：Sprint 1 报告声称的 `frontend/src/__tests__/contract.test.js` 从未进 main（只在未合入的 `8cf3c78`），故 T-FE-01/02 现为 0 覆盖。
- 查清并登记：Sprint 1 报告 §2.1 对 `test_security_boundaries.py` 的分组拆分（12/19/16/4）四项相加为 51、与该文件当时的 48 条不符；本轮按源码小节实算得 12/14/19/5（=50），并回推出当时应为 12/14/17/5（=48）。
- 查清并登记：`repo/defect-records.md` 的 D-09 行状态与用例数已过期（#101 已合入），D-10 半条已关闭。
- 未做（按 §7 逐条待办）：集成/系统/非功能三层执行、MySQL 隔离库、`test-plan.md` §4.1 的 T- 编号补行、`docs/design/non-functional.md` D2 章节。
