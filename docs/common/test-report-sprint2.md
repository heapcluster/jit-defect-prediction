# 单元测试报告 · Sprint 2（快照 2026-10-25）

> 课程《项目要求》Sprint 2（10/23–11/13，见 `repo/sprints.md` §1）的交付物「单元测试报告」。
> 结构与口径沿用 `common/test-report-sprint1.md` 与 `common/test-plan.md` §5；evidence 索引按 `test-plan.md` §6 收在本文件 §8，不另建第三份清单。
> **Sprint 2 未结题**：本文件是**滚动快照**，现行基线 main **`e48c5b2`**（2026-10-24 23:47 合入 #117 后的 main）；第一版快照的基线是 `0773a49`，其数字保留在 §3.2 对照表第 6 行与五份旧 `coverage-*.md` 里，**不倒填、不覆盖**。结题（11/13）前按 §8 末尾的规矩继续更新。
> 统稿：吕建江（后端线，本轮牵头）｜ 供稿：蒋励（模型线用例）、刘帅华（前端线用例）、苏哲勋（CI 门禁）

## 0. 一句话结论

三线单测在本机与 CI 上**全绿**：后端 **159** 条、模型 **154** 条（1 条按设计 skip）、前端 **19** 条（6 文件），0 failed / 0 error；后端行覆盖 **95.71%**（699 stmts / **30** miss），A、B 两条解释器路径**逐模块差异 0 处**；CI 的 lint→test→build 共 **17** 步在 main `e48c5b2` 全部 success（[run 40108570584](https://github.com/heapcluster/jit-defect-prediction/actions/runs/40108570584)）。本次复测明细另出 `backend/scripts/evidence/coverage-2026-10-25.md`；上一版快照的数字（145 / 103 / 10 / 92.13%，基线 `0773a49`）留在 §3.2 第 6 行与 §4 链条第 6 步，不改写。

**仍缺的不是单测，是单测以上三层的「系统层」**：集成与非功能两层的正式执行记录已随 PR #107 合入 main `3cecd2e`（`integration-2026-10-24.md`、`perf-2026-10-24.md`、`security-2026-10-24.md`，三份文件合计**三张实拍截图**：集成 1 张 `integration-shot-predict.png`（无头 Edge 真发 `POST /api/predict`）+ 安全 2 张 `security-shot1-missing-token.png` / `security-shot2-bad-params.png`（Swagger UI 页面同源 `fetch`）；`design/non-functional.md` §5 D2 验证章节），性能与安全两份旧证据随之**正式作废**（§8）；系统层 T-ST-01~05 的**后端半边已执行**（演示库 `backend/demo.db`、43 项断言全过，按 Issue #130 裁定 A/A，执行记录在 PR #141 待合入），**页面半边与全链路录屏仍缺**；MySQL 侧复跑仍缺（Issue #121 授权未到）。差距逐条见 §7。

## 1. 执行环境（如实记录，含「没跑」的部分）

| 项 | 值 |
|---|---|
| 被测树 | 分支 `docs/common/test-report-sprint2-refresh` @ **`e48c5b2`**；本分支只改本文件 + 新增 `backend/scripts/evidence/coverage-2026-10-25.md`，`backend/app`、`backend/tests`、`backend/pytest.ini`、`data_model/`、`frontend/` 与 main 逐字一致（核对命令见 §3.4） |
| 操作系统 | Windows 11（10.0.26200），本机实测 |
| 解释器 **A** | 仓库根 `.venv`（不入库、各人自建），Python **3.12.7** |
| 解释器 **B** | conda 环境 `jit-defect-prediction`（按 `data_model/environment.yml` 建，#83 之后唯一权威清单），Python **3.12.15** |
| Python 侧依赖 | pytest 9.1.1 / coverage 7.16.2 / pytest-cov 7.1.0 / fastapi 0.141.1 / SQLAlchemy 2.0.54（A、B 版本一致；2026-10-25 复测时再次逐项 `import` 核对相同） |
| 前端侧 | Node **v24.15.0** / npm **11.12.1**；`npm ci` 实装 **273 packages**（39s，走本机代理）；vitest 5.0.5 / vite 8.3.0 |
| 静态检查 | ruff **0.16.8**（`ruff check backend data_model infra` → All checks passed）、eslint 10.12.0（`npm run lint` → 0 problem） |
| 数据库 | SQLite（后端夹具 `backend/tests/conftest.py`，按 `backend/api-spec.md` §5 variant 口径）。**MySQL 未参与本报告任何数字**，原因见 §6 与 §7 |
| 模型权重 | 后端用夹具模型（决策树 / 线性 Pipeline，`conftest.py` 现造），模型线用合成小样本；`.pkl` 被 `.gitignore` 排除，故干净 clone 有 1 条按设计 skip（§2.2） |
| CI | GitHub Actions `ubuntu-24.04`，工作流 `.github/workflows/ci.yml`（#72 落地、#92 修安装与 lint 阻断、#115 加规格撞车门禁）；main `e48c5b2` 的 run **success**，**17** 步全绿，15:47:25Z→15:50:36Z。中间 main 曾因 `infra/pr_auto_review.py` 的 ruff `TRY004` 红过一段（Issue #126，非本线代码），由 #129 `d2fd6eb` 修掉后转绿，本行记的是修好之后的绿 |
| 测量时间 | 首版 2026-10-24 12:45–12:50；**本次复测 2026-10-25 00:02–00:06**（+08:00） |
| **计数口径** | 一律不取终端回显。本机 shell 会吞掉 pytest 末行汇总，故条数取自 `--junitxml` 的 `testsuite@tests/failures/errors/skipped`，覆盖率取自 `--cov-report=json` 的 `totals` 与逐文件 `summary`/`missing_lines`，前端取自 vitest 自身汇总行。原始产物只落本机临时目录，不入库 |

## 2. 执行结果

### 2.1 三线汇总

| 层 | 命令（cwd） | 用例数 | 通过 | 失败 | 错误 | 跳过 | 耗时 |
|---|---|---|---|---|---|---|---|
| 单元 · 后端 | `cd backend && python -m pytest tests/ -q` | **159** | 159 | 0 | 0 | 0 | A 11.374s / B 11.507s（计时只作 A/B 相对参考，见下注） |
| 单元 · 模型 | `cd data_model && python -m pytest tests/ -q` | **154** | 153 | 0 | 0 | **1**（按设计） | 15.878s |
| 单元 · 前端 | `cd frontend && npm run test:unit` | **19** | 19 | 0 | 0 | 0 | 1.90s（6 文件，vitest 自报 Duration） |
| 静态检查 | `ruff check backend data_model infra`；`cd frontend && npm run lint` | — | 通过 | — | — | — | ruff 0 problem / eslint 0 problem |
| 构建 | `cd frontend && npm run build`；`python -m compileall -q backend/app data_model infra` | — | 通过 | — | — | — | vite **849ms**，**2250** modules；有 chunk >500kB 警告（§2.5）。compileall 本机 rc=0（A 解释器，与 CI 第 **17** 步同命令） |
| **集成** | — | **0**（自动化用例） | — | — | — | — | 正式执行记录**已合入**：`integration-2026-10-24.md`（main `3cecd2e`：全量库 + 真权重 + 真服务一条链）。`test_integration_api.py` 6 条仍只是**套件内 SQLite 级**，不等价、不顶替 T-IT-01~03（§2.2 注）；MySQL 侧仍缺（§6） |
| **系统** | — | **0**（自动化用例） | — | — | — | — | T-ST-01~05 的**后端半边已执行**：演示库 `backend/demo.db`（Issue #130 裁定 A）+ **43 项断言全过、退出码 0**，记录在 PR #141（待合入）。页面半边（刘帅华）与三线同场录屏仍缺；`repo/demo-script-sprint1.md` 是手工脚本，不等价 |
| **非功能** | — | **0**（自动化用例） | — | — | — | — | 重跑**已合入**：`perf-2026-10-24.md`（含 §4.1 补记：rf 收敛后按登记口径 n=100 复测 p95 **86.6ms** 达标）、`perf-rf-converged-2026-10-24.md`（#124，n=30 口径 p95 127.7ms）、`security-2026-10-24.md` + **两张**实拍截图（缺令牌 / 畸形参数）、`design/non-functional.md` §5。两份旧压测与两份旧安全证据已标「历史，不作为现行口径」（§8） |

warnings：后端 **A 路径 1 条 / B 路径 5 条** —— 两条路径都有 `fastapi/testclient.py` 的 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`（非本线代码）；B（conda，按 `environment.yml` 装）另多 4 条 matplotlib 的 `PyparsingDeprecationWarning`（`oneOf` / `parseString` / `resetCache` / `enablePackrat`），触发点是 `tests/test_integration_api.py::test_predict_then_query_and_repeat_keeps_one_row` 的 shap → matplotlib 导入链，A 的 `.venv` 未装 matplotlib 故不出现。模型线若干条 sklearn `FutureWarning`（`SVC(probability=True)` 在 1.9 弃用、1.11 移除，来自三线 `model.py` 的既有口径）与一条 lightgbm 的 `UserWarning: X does not have valid feature names`（`test_model_registry_parity.py` 的 lgbm 参数化用例，#88 起）。本轮未通过改配置或加依赖消除任何一条。全部是第三方库告警，不影响判定，也**没有**被静默过滤掉。

**后端计时为什么从 5.6/6.3s 涨到 11.4/11.5s**：#128 新增的 2 条 `python -m <module>` 守卫用例各起**真子进程**（另 2 条 CLI 用例走 `monkeypatch sys.argv` + `capsys`，是进程内的，不额外计时；`coverage-2026-10-24-gaps.md` §5 ② 记同批 157 条时 `time=12.783s`，与本次同量级），是新增用例的固有成本。另需如实登记：本次测量时本机同时有模型线夜跑（CUDA 编码）在跑，计时含少量资源竞争，**故计时只作 A/B 相对参考、不与上一版纵比**；条数与覆盖率是确定性结果，不受负载影响。

### 2.2 后端 159 条按文件（junitxml 计数）

| 文件 | 条数 | 首次入 main | 现在覆盖什么 |
|---|---|---|---|
| `tests/test_auth_errors.py` | 3 | #30 `44ca43f` | 缺令牌 → 401/40100、错令牌 → 401/40100、成功响应仍是 `{code:0,message:"ok",data}` 包络（T-BE-04；令牌空白/大小写/超长/前缀等变体在 `test_security_boundaries.py`） |
| `tests/test_commits_api.py` | 13 | #30 `44ca43f` | 列表分页与 `risk_score` 降序、`size` 越界/上限边界、`min_risk` 空结果集非错误、详情返回 14 特征 + `explanation`、提交存在但无预测 → `risk_score`/`model_name` 为 null、未知哈希 40400、哈希格式非法 40001、默认模型取版本序最新而非最近写入、时间区间闭区间语义 4 条（#62）（T-BE-01/02） |
| `tests/test_db.py` | **8** | #79 `62f6a18`；#128 `4a8cf25` +5 | 建表后索引自检 `_assert_indexes()` 正例 + 反例（关闭 Issue #73 的一半）；#128 再补 5 条：`get_engine()` 按 `DATABASE_URL` 懒建 + 第二次命中缓存、`DATABASE_URL` 为空 → `AppError(50000)` fail closed、CLI 三条出口（无参 rc=2 且 stderr 是用法行 / 配置错 rc=1 且不回显内部信息 / 正常 rc=0 且库文件真落盘）、`python -m app.db` 与 `python -m app.ingest` 真子进程守卫 rc=2 + 用法行（2 条参数化） |
| `tests/test_feature_source.py` | **2** | #128 `4a8cf25`（新文件） | 抽取脚本不可加载的两个分支（`spec is None` / `spec.loader is None`）都抛固定文案 `RuntimeError("feature extractor unavailable")`；`_extractor` 带 `lru_cache`，用 autouse 夹具逐条 `cache_clear()` 防串味 |
| `tests/test_ingest.py` | **3** | #30 `44ca43f`；#128 `4a8cf25` +1 | `commits` 灌库重复执行幂等（同键不产生第二行）、缺必需键时整批回滚；#128 再补 CLI `main()`：参数不足 rc=2、种类非法 rc=2、正常路径经 `get_engine()` 走 `ingest()` 真落一行 |
| `tests/test_integration_api.py` | 6 | #99 `065c83a` | 独立 SQLite engine 上「建表 → `ingest()` 四类 CSV 各灌两遍验幂等 → 预测后查询、重复预测只留一行 → 周/月聚合与闭区间对得上灌入数据 → 缺预测/缺特征仍守契约形状 → 空库查询不是错误 → 鉴权失败与模型加载失败都不泄露内部信息」。这是**套件内**集成：夹具模型 + 合成 CSV + SQLite，不含 MySQL、真实权重与前端，故不能顶替 T-IT-01~03 |
| `tests/test_mirror.py` | 8 | #30 `44ca43f` | 导出 `openapi.json` 与契约三逐字段比对（规格「Swagger 实现镜像」） |
| `tests/test_model_registry.py` | **16** | #47 `4e72bf8`；#124 `4d658cf` +2 | `joblib.load` 口径、特征数自检、SHAP 解释键名 ∈ 14 特征、线性 Pipeline 加性残差归零；#96 交付清单加载 2 条、#99 导入路径与失败汇总 7 条；#124 再补两条清单负例：`[models]` 段非法文件名或重复条目 → 拒收、`[feature_order]` 段缺序号 → 拒收（关掉 §6 原第 3 组缺口）（T-BE-06 / T-MO-02 / T-MO-03） |
| `tests/test_predict_api.py` | 12 | #30 `44ca43f` | 在线预测正向、`model_name` 回显、幂等（同键只留一行）、#97 新提交现算 14 维特征后在线预测 3 条（T-BE-03） |
| `tests/test_schema_sql.py` | 25 | #100 `f5ca61d` | `infra/schema.sql` 静态校验：四表列名/类型/主键/索引与契约一一致、幂等（`IF NOT EXISTS`）、禁止语句（DROP/TRUNCATE/DELETE 等 11 条参数化）、漂移负例 8 条 |
| `tests/test_security_boundaries.py` | 50 | #71 `501dc06` | 鉴权边界 **12** 条（四接口一律需令牌、令牌须逐字相等、错误提示不透露哪一位错）、查询参数边界 **14** 条（`page`/`size`/`min_risk`/时间非法 → 40001，边界合法值不误判）、详情/预测/趋势边界 **19** 条（哈希长度与非十六进制、缺字段、模型不在清单、粒度枚举、时间格式）、信息泄露断言 **5** 条（响应体不含 Traceback / SELECT / sqlalchemy / `.py` / 路径 / site-packages；50000 文案通用化）。#101 再 +2：`G`×40 大写非十六进制同样拒收、归一化后库内没有的哈希仍 40400，并把原「钉住错误行为」的一条改写为「归一化后命中同一提交」（T-BE-05 / T-NF-02） |
| `tests/test_security_cases_script.py` | **4** | #113 `655b487`（新文件） | 安全脚本 `--mask-url` 的**可选实测**语义：打开时 50000 掩码行 PASS 且 rc=0；404 使该行 FAIL 且 rc=1；空库同样 FAIL 且 rc=1；不加 `--mask-url` 时该行记「未测」且 rc=0（即掩码项不再恒判通过、也不再因缺服务而误判失败） |
| `tests/test_trends_api.py` | 9 | #30 `44ca43f` | 周聚合、月粒度按自然月分桶、粒度枚举非法 → 40001、空区间非错误、`end` 纯日期含当天/带时间分量不变、紧凑 basic 格式拒收、周下钻周一至周日保住周日（#79 补月粒度 3 条 + 周下钻 1 条，关闭 Issue #73 的一半） |
| **合计** | **159** | | |

> 分组条数是本轮按「源文件里 `def test_` 所在小节 × junitxml 收集到的用例名」实算的，不是照抄旧报告。顺带查出一处旧口径错误：`test-report-sprint1.md` §2.1 把 `test_security_boundaries.py` 的 48 条拆成 12/19/16/4，**四项相加是 51、对不上 48**；按同一算法回推当时的正确拆分应为 12/14/17/5（=48），#101 的 +2 全落在「详情/预测/趋势边界」→ 19。Sprint 1 报告是历史文件，按「历史记录不改」保留原文，订正记在本行。

### 2.3 模型线 154 条按文件（供稿：蒋励；条数由本轮 junitxml 实测，逐文件按 classname 归组）

| 文件 | 条数 | 首次入 main |
|---|---|---|
| `tests/test_szz_labeling.py`（5 个 class：IsFixCommit 19 / MergeRanges 7 / ParseOldRanges 6 / CamelSelfcheckReport 7 / BlameCacheKey 3） | 42 | #71 `501dc06` |
| `tests/test_split_dataset.py`（ValidateSplit 6 / SplitIndex 4 / SortKey 4 / ParseTs 3） | 17 | #71 `501dc06` |
| `tests/test_verify_all_weights.py` | **15** | #88 `5e9b6d1` |
| `tests/test_text_source.py` | **15** | #106 `bd4f2d0` |
| `tests/test_feature_ablation.py` | **11** | #110 `380dd0d` |
| `tests/test_model_registry_parity.py` | 10 | #71 `501dc06` |
| `tests/test_effort_budget.py` | 9 | #71 `501dc06` |
| `tests/test_feature_contract.py` | 8（**1 条 skip**） | #71 `501dc06` |
| `tests/test_embedding_cache.py` | 6 | #71 `501dc06` |
| `tests/test_effort_scope_and_narrative.py` | **5** | #88 `5e9b6d1` |
| `tests/test_official_entry_import.py` | 4 | #71 `501dc06` |
| `tests/test_fused_report_coverage.py` | 3 | #86 `3a9b7b0` |
| `tests/test_single_commit_features.py` | 3 | #95 `8fdaf23` |
| `tests/test_from_saved_isolation.py` | **3** | #88 `5e9b6d1` |
| `tests/test_e2e_effort_curve.py` | **2** | #88 `5e9b6d1` |
| `tests/test_camel_source.py` | 1 | #68 `11993e2` |
| **合计** | **154** | |

本轮新增的 6 个文件（51 条）各自钉住什么，按源码 docstring 原文归纳（**判定口径归模型线**，本报告只登记条数与出处）：`test_verify_all_weights.py` —— 权重清单能往返、md5 漂移必被拦、`__main__` 类路径必判失败（起因是 2026-10-24 一次真实的 `tabnet_v1.pkl` 类路径分叉）；`test_text_source.py` —— 三类文本来源的判定边界、占位串必须非空（空串会被 `read_csv` 读成 NaN 再被 `dropna` 静默丢掉）、两个构建器共用一份实现；`test_feature_ablation.py` —— 留一法符号约定（删有用特征 AUC 下降、`delta_auc` 为负）、置换重要性给正下降量、名次与分歧判定是纯函数；`test_effort_scope_and_narrative.py` —— 预算感知评审下限按口径走（LOC 是「行」、nf 是「文件」）、报告结论段必须由本轮结果算出而非硬编码；`test_from_saved_isolation.py` —— `--from-saved` 的图表不得落进权威 `reports/figs/`；`test_e2e_effort_curve.py` —— `cumulative_curve` 必须存在且与 fused 线逐点同口径。

唯一 skip：`test_feature_contract.py::test_manifest_models_exist_on_disk` —— 断言交付清单里声明的 `.pkl` 在磁盘上真实存在，而 `*.pkl` / `*.joblib` 被 `.gitignore` 排除（硬红线三：不提交模型文件），干净 clone 必然 skip。**这不是漏测**，有权重的机器上该条会实跑；CI 上同样是 skip 而非 fail。

Sprint 1 快照（`test-report-sprint1.md` §2）时模型线只有 `test_feature_contract.py` **8** 条；上一版快照的 103 条里 95 条来自 #71/#86/#95/#68；本次 154 条里再多的 **51** 条来自 #88（25 = 15+5+3+2）、#106（15）、#110（11）。模型线的**主验收口径仍是复现一致性（±0）**（`test-plan.md` §5），单测是配套而非替代。

### 2.4 前端 19 条（6 文件；供稿：刘帅华，条数取 vitest 自报汇总，与 CI run 40108570584 逐字相同）

| 文件 | 条数 | 断言什么 | 对应编号 |
|---|---|---|---|
| `tests/request.spec.js` | 6（2 条 `it` + 1 组 `it.each` 展开 4 条） | HTTP 200 成功包络只回 `data`；400/401/404/500 四档保留业务码 40001/40100/40400/50000 并映射到固定文案；500 档把服务端细节（用例里是 `private server path`）替换成「服务异常，请稍后重试」= **不回显**；无业务包络的网络错误按原错误传递 | T-FE-03 |
| `tests/risk.spec.js` | 4 | 阈值 ≥0.5 高 / ≥0.3 中 / 其余常规，含边界值归上一档（0.5 是高不是中） | T-NF-04（阈值单一来源） |
| `tests/CommitDetail.spec.js` | **4** | 详情页「重新预测」入口（#90 的功能）：未预测提交点击后刷新 `risk_score`/`model_name`/`explanation`；predict 非 2xx 时**不刷新** detail 而按业务错误提示；40400 → `errorCode` 与文案「该提交不存在」；`explanation` 为空数组 → 显示「该模型未提供特征解释」 | T-FE-03 / T-BE-03（页面侧） |
| `tests/RiskList.spec.js` | **3** | 列表页三态里的两态：空数据显示空态文案（**不是错误**）；50000 → 「服务异常，请稍后重试」；40100 → 「登录已失效，请重新登录」 | T-FE-01（部分） |
| `tests/features.spec.js` | **1** | `FEATURE_FIELDS` 恰为 14 项，且顺序与 `feature_order.txt` 的 `[feature_order]` 段逐字一致 | T-FE-02 |
| `tests/models.spec.js` | **1** | 前端 `MODELS` 与 `feature_order.txt` 的 `[models]` 段一致（交付清单单一来源） | T-FE-02 / 规格 `model-coverage` R6 |

**这六份是 main 上前端的全部单测**（本机 `npm ci` 273 packages 后 `npm run test:unit` 实跑：`Test Files 6 passed (6)` / `Tests 19 passed (19)`，与 CI run 40108570584 的 vitest 汇总行逐字相同）。上一版快照时只有前两份共 10 条；另外四份由 **#90 `bd0b697`**（2026-10-24 19:33 合入，**晚于**上一版基线 `0773a49`）带进 main，故上一版的「前端 10 条」在其基线上并没有错，只是过期。Sprint 1 报告 §6 写的 `frontend/src/__tests__/contract.test.js`（声称覆盖 T-FE-01~03）**仍未进 main**：它只存在于未合入的 PR #70/#71 分支提交 `8cf3c78`；#71 最终合入 main 的 squash 提交 `501dc06` 只带进了 `backend/tests/test_security_boundaries.py` 与 `data_model/tests/`，`git show --stat 501dc06 | grep frontend` 只有 `docs/frontend/README.md`。当前状态：

- **T-FE-01（加载中 / 空数据 / 失败三态）：🔶 部分覆盖（3 条）** —— `RiskList.spec.js` 断言了「空数据显示空态文案」与「失败两档固定文案（50000 / 40100）」，**「加载中」态没有独立断言**；页面三态的实拍截图已随 #117 入库（`docs/frontend/evidence/tf-fe-01-screenshots.md`，9 张）。
- **T-FE-02（页面字段 → 契约逐字段映射）：✅ 已有断言（2 条）** —— `features.spec.js` 把 `FEATURE_FIELDS` 与 `feature_order.txt` 的 `[feature_order]` 段逐字比（恰 14 项且同序），`models.spec.js` 把前端 `MODELS` 与 `[models]` 段比。两处对齐的都是**冻结的单一来源**（`feature_order.txt`），比「对齐 `api-spec.md` 的抄本」更强。
- **T-FE-03**：仍由 `request.spec.js` 的 `it.each` 四档实覆盖（✅ 接口层），`CommitDetail.spec.js` 再补了页面侧的 40400 / 非 2xx / 空解释三档。

`test-plan.md` §4.1 的状态列要不要按上面翻（T-FE-01 ❌→🔶、T-FE-02 ❌→✅）由蒋励裁定；本报告只登记实测证据与出处，不代改方案文档（那属另一件事）。

### 2.5 构建与静态检查的已知告警（不阻断，但不藏）

`npm run build` 成功（**849ms**、**2250** modules transformed），产物 `dist/index.html` 0.40 kB、`index-*.css` **363.18 kB（gzip 48.61 kB）**、`index-*.js` **2,195.75 kB（gzip 720.55 kB）**，vite 报 chunk 超过 500 kB 的告警（echarts + element-plus 全量打进一个 chunk）。上一版记的是 673ms / 2248 modules / 2,194.19 kB，差异来自 #90 详情页新增的重新预测入口。这不影响单测结论，属前端线的打包优化项（`build.chunkSizeWarningLimit` / 动态 `import()` 代码分割），登记在此备查。

## 3. 覆盖率（后端 `--cov=app`）

### 3.1 本次实测：95.71%（基线 `e48c5b2`；明细与命令见 `backend/scripts/evidence/coverage-2026-10-25.md`）

| 模块 | Stmts | Miss | Cover | 未覆盖行 |
|---|---|---|---|---|
| `app/api/commits.py` | 86 | 0 | **100%** | — |
| `app/api/predict.py` | 79 | 14 | 82.28% | 50, 77-80, 83-84, 111, 113-114, 118-121 |
| `app/api/trends.py` | 36 | 0 | **100%** | — |
| `app/auth.py` | 8 | 0 | **100%** | — |
| `app/config.py` | 12 | 0 | **100%** | — |
| `app/db.py` | 48 | **1** | 97.92% | 71 |
| `app/errors.py` | 32 | 3 | 90.62% | 33, 58-59 |
| `app/feature_source.py` | 19 | **0** | **100%** | — |
| `app/ingest.py` | 84 | **1** | 98.81% | 119 |
| `app/main.py` | 22 | 0 | **100%** | — |
| `app/model_registry.py` | 158 | **11** | 93.04% | 56, 123-127, 191, 211-213, 241 |
| `app/models.py` | 56 | 0 | **100%** | — |
| `app/schemas.py` | 59 | 0 | **100%** | — |
| **TOTAL** | **699** | **30** | **95.71%** | — |

（上一版基线 `0773a49` 的同表是 55 miss / 92.13%，其中 `db.py` 15、`ingest.py` 7、`feature_source.py` 1、`model_registry.py` 15；那份表原样留在 `coverage-2026-10-24.md` §2 与 `coverage-2026-10-24-gaps.md` §2，不倒填。）

（`app/__init__.py`、`app/api/__init__.py` 为 0 stmts，计入 JSON 但不影响 TOTAL。）

- **A 与 B 逐模块比对差异 0 处**（对比两份 coverage JSON 每个文件的 `num_statements`、`missing_lines` 整数与行号列表）。Python 3.12.7 与 3.12.15 之间没有差异，`coverage-2026-10-22.md` §5 留的「B 未复测」口子已在 10-24 那次补上，本次（2026-10-25）是第三次确认。`percent_covered` 原值 **95.7082**，本报告一律写 95.71%。
- 口径：**行覆盖**（两份 JSON 的 `meta.branch_coverage` 均为 `false`），与此前各次测量一致，可直接纵向比。
- 目标核对：`test-plan.md` §5「后端行覆盖 Sprint 2 ≥60%」→ **95.71%，达标（余量 35.71 个百分点）**；「Sprint 3 ≥75%」→ 已提前超过，但**不作为 Sprint 3 免测理由**，Sprint 3 仍需按当时 main 复测。
- 统计范围只有 `--cov=app`：**不含** `backend/scripts/`（压测 / 安全 / 灌库脚本，其产出由 §8 索引的 `perf-*.md` / `security-*.md` 验证）与 `backend/tests/`。

### 3.2 七次基线对照（覆盖率为什么从 84% 到 96%）

| # | 基线 | 触发 PR | 测试条数 | Stmts | Miss | TOTAL | 出处 |
|---|---|---|---|---|---|---|---|
| 1 | `59ad7ed` | 首测（2026-10-16） | 39 | 595 | 97 | 84% | `coverage-2026-10-16.md` |
| 2 | `0cad776` | #62 时间区间语义 | 45 | 600 | 95 | 84% | 同上补记 |
| 3 | `501dc06` | #71 四线独立成包 | 93 | 600 | 91 | 85% | `coverage-2026-10-17.md` |
| 4 | `e46624b` | #75/#79/#78/#81 | 100 | 600 | 80 | **87%** | `coverage-2026-10-22.md` |
| 5 | `065c83a` | #94–#100 + #99 | 143 | 698 | 55 | **92.12%** | `coverage-2026-10-24.md` |
| 6 | `0773a49` | #82/#85/#101 | 145 | 699 | 55 | 92.13% | 本文件上一版快照 |
| 7 | **`e48c5b2`** | **#113/#128/#124（本次）** | **159** | **699** | **30** | **95.71%** | `coverage-2026-10-25.md` |

> 用户与看板关心的「87% → 96%」= 第 4 行到第 7 行；「87 条 → 159 条」= §4 的另一条链。**两个 87 不是一回事**（一个是覆盖率百分数、一个是 Sprint 1 报告里的用例条数），别在同一句话里混着写。
> 第 6→7 行之间还有一次**中间测量**：#128 补测后 157 条 / 34 miss / **95.14%**（基线 `edfe74f`，见 `coverage-2026-10-24-gaps.md`）。它测在 #128 分支上、不是 main 基线，故不单列一行，只在这里留指针，免得有人拿 157 对不上 159。

- **Stmts 595 → 699（+104）**：主要来自 #97 的 `app/feature_source.py`（+19，单条提交特征抽取入口）、`app/api/predict.py` 54→79（+25，现算特征 + 落库 + `IntegrityError` 回落）、#96/#99 的 `app/model_registry.py` 108→158（+50，`_delivery_models()` 清单解析 + `sys.path` 插入 + 失败汇总）、`app/api/commits.py` 77→86（+9，详情兜底改按该提交已有模型取版本序最新 + #101 的 `_check_hash` 归一化）、`app/config.py` 11→12（+1，`SOURCE_REPO`）。
- **Miss 97 → 55（−42）**，三段实质性关闭：
  - `app/ingest.py` 35 → **7**（−28）：#99 的 `test_integration_api.py` 真实调用 `ingest()` 灌四类 CSV 各两遍，三条灌库路径（原 36-44 / 48-60 / 64-72）全部命中；剩下 7 行是 CLI `main()` 与 `__main__` 守卫。
  - `app/db.py` 28 → **15**（−13）：#79 的索引自检正/反例命中 `_assert_indexes()` 本体（原 43-53）。
  - `app/api/trends.py` 1 → **0**、`app/api/commits.py` 8 → **0**：月粒度 `_period()` 分支（#79）与详情兜底/归一化分支（#99/#101）。
  - 反向增量：`app/api/predict.py` 7 → **14**（+7，#97 新增的 `session.flush()` 并发回落与 `SOURCE_REPO` 抽取失败分支，夹具触发不到）。
- **第 5→6 行（143 → 145）Miss 一行未减**：#101 改的 `_check_hash` 归一化路径本来就在覆盖区内（`commits.py` 86 stmts / 0 miss），新增 2 条用例是**把已修行为钉住**（防回归），不是补覆盖率。这一点要写清，否则「加了 2 条测试覆盖率没动」会被读成测试无效。
- **本次（第 6→7 行，145 → 159）Miss 55 → 30（−25），且 Stmts 一点没涨（699）**：这批 PR 只加测试、`backend/app` 一行未动，所以 3.58 个百分点**全是补旧账**。拆开看：#128 关掉 `db.py` 15→1、`ingest.py` 7→1、`feature_source.py` 1→0（−21）；#124 的两条清单负例关掉 `model_registry.py` 的 63-64 与 69-70（−4）。`predict.py` 的 14 行与 `errors.py` 的 3 行原地未动，原因见 §6。

### 3.3 覆盖率与用例数不是同一件事（本轮的口径提醒）

第 4→5 行是「用例 +43、覆盖率 +5.12pp」，第 5→6 行是「用例 +2、覆盖率 +0.01pp」，第 6→7 行是「用例 +14、覆盖率 +3.58pp」。前两跳的分母（Stmts）同时在涨：**#97/#96/#99 一边加代码一边加测试**，所以 84%→92% 这 8 个点里，有相当部分是「新增代码自带测试」而非「补旧账」；**第三跳（92.13%→95.71%）分母不动，是纯补旧账**，性质与前两跳不同，引用时别混为一谈。旧账的关闭先集中在 `ingest.py`（−28 miss，#99）与 `db.py`（−13 miss，#79），本轮再把 `db.py`/`ingest.py`/`feature_source.py`/`model_registry.py` 四处的剩余缺口清到 13 行，逐行清单见 §6。

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
cd backend   && python -m pytest tests/ -q                       # 期望 159 passed
cd data_model && python -m pytest tests/ -q                      # 期望 153 passed, 1 skipped
cd frontend  && npm ci && npm run test:unit                      # 期望 Test Files 6 passed / Tests 19 passed

# ── 覆盖率（终端汇总行在部分 shell 会被吞，取文件为准）─────────────
cd backend
python -m pytest tests/ -q --cov=app --cov-report=term-missing \
       --cov-report=json:<tmp>/cov.json --junitxml=<tmp>/junit.xml
#   junit.xml → testsuite@tests=159 failures=0 errors=0 skipped=0
#   cov.json  → totals.num_statements=699, totals.missing_lines=30, percent_covered=95.7082

# ── 被测树与基线的等价性核对（cwd=仓库根，不依赖 remote 名）────────
git merge-base --is-ancestor e48c5b2 HEAD && echo "含基线 e48c5b2"
git diff --name-only e48c5b2 HEAD       # 期望：只有 docs/common/test-report-sprint2.md
                                        #       与 backend/scripts/evidence/coverage-2026-10-25.md
git diff --name-only e48c5b2 HEAD -- backend/app backend/tests backend/pytest.ini   # 期望：空
```

> 覆盖率产物 `.coverage` / `htmlcov/`、前端 `node_modules` / `dist` 均在 `.gitignore` 内，不入库；`cov.json` / `junit.xml` 只落本机临时目录。

## 4. 用例数怎么从 87 涨到 159（本次要讲清的那件事）

Sprint 1 报告 §2 写的后端 **87** 条，是「当时 main 上的 39 条 + 本 PR 新增的 48 条安全/边界用例」的**分支内口径**；那 48 条要到 #71（`501dc06`）才随 squash 合入 main，而 main 在同期又先合入了 #62 的 6 条时间区间用例（39→45）。所以 main 上的真实链条是：

| 步 | 基线 | 变化 | 条数 | 来源 |
|---|---|---|---|---|
| 0 | `59ad7ed` | — | **39** | #30 六文件（auth/commits/ingest/mirror/predict/trends）+ #47 `test_model_registry.py` |
| 1 | `0cad776` | +6 | **45** | #62 时间区间闭区间语义用例 |
| 2 | — | （+48，在分支上） | *87* | **Sprint 1 报告里的那个 87**：45 条 main + 48 条安全/边界，尚未合入 |
| 3 | `501dc06` | +48 | **93** | #71 把 `test_security_boundaries.py`（48 条）带进 main |
| 4 | `e46624b` | +7 | **100** | #79：`test_trends_api.py` 月粒度 3 + 周下钻保周日 1、`test_db.py` 索引自检 3（关闭 Issue #73） |
| 5 | `065c83a` | +43 | **143** | #100 `test_schema_sql.py` 25 + #96/#99 `test_model_registry.py` 9 + #99 `test_integration_api.py` 6 + #97 `test_predict_api.py` 3 |
| 6 | `0773a49` | +2 | **145** | #101：`test_security_boundaries.py` 新增 1 个函数（归一化后仍 40400）+ 1 个参数（`G`×40），并把原「钉住错误行为」的 `test_detail_uppercase_hash_passes_validation_but_not_found` 改写成 `test_detail_uppercase_hash_is_normalized_to_the_stored_commit`（D-09 修复） |
| 6.5 | `edfe74f` | +4 | **149** | #113 `655b487`：新文件 `test_security_cases_script.py` 4 条，把安全脚本 50000 掩码行从「恒判通过」改成 `--mask-url` 可选实测（不加就记「未测」且 rc=0，加了就必须真过） |
| 7 | **`e48c5b2`** | **+10** | **159** | #128 `4a8cf25` **+8**（`test_db.py` 3→8、`test_ingest.py` 2→3、新文件 `test_feature_source.py` 2）+ #124 `4d658cf` **+2**（`test_model_registry.py` 14→16，清单 `[models]`/`[feature_order]` 两段负例） |

**87 → 159 的净增 72 条**，逐 PR 对得上：#62 时间区间 6 + #79 索引自检/月粒度/周下钻 7 + #94–#100/#99 共 43（`schema.sql` 静态校验 25、模型注册表 9、套件内联调 6、在线预测现算特征 3）+ #101 归一化 2 + #113 安全脚本 4 + #128 懒建/CLI/守卫/抽取器 8 + #124 清单负例 2 = **72**。按文件看 159 条的构成就是 §2.2 那张表（合计行逐字对得上 junitxml 的 `tests=159`）。注意第 2 行的 *87* 是斜体：**它不是任何一个 main 基线上的数字**，引用时必须说明它是 Sprint 1 的分支内口径（39 条 main + 48 条尚未合入的安全/边界），否则会被人拿 `git log` 对不上。

模型线同期 8 → **154**（+146：#71/#86/#95/#68 的 95 条 + #88/#106/#110 的 51 条，见 §2.3），前端 0 → **19**（#81 4 条 + #94 6 条 + #90 9 条，见 §2.4）。

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
| T-FE-01 | 三态（加载中 / 空数据 / 失败） | 🔶 **3 条**：空数据空态 + 失败两档固定文案（50000 / 40100）；**「加载中」态无独立断言** | `frontend/tests/RiskList.spec.js`（#90 `bd0b697`）；页面三态实拍 9 张见 `docs/frontend/evidence/tf-fe-01-screenshots.md`（#117 `e48c5b2`）。声称覆盖它的 `contract.test.js` 仍未进 main（§2.4） |
| T-FE-02 | 页面字段 → `api-spec.md` 逐字段映射 | ✅ **2 条**，且对齐的是冻结单一来源而非抄本 | `frontend/tests/features.spec.js`（`FEATURE_FIELDS` 恰 14 项且与 `feature_order.txt` 的 `[feature_order]` 段同序）+ `tests/models.spec.js`（前端 `MODELS` 与 `[models]` 段一致），均 #90 带入。**状态列要不要由 ❌ 翻 ✅ 请蒋励在 `test-plan.md` §4.1 裁定**，本报告只登记证据 |
| T-FE-03 | 错误码 → 文案分发，50000 不回显堆栈 | ✅（接口层） | `tests/request.spec.js` 的 `it.each` 四档 |
| T-IT-01~03 | 真实库 + 真实模型 + 前端三页面一条链路 | 🔶 两侧各自都对真后端跑通，**但没在同一条链上同场跑过** | 后端侧：`integration-2026-10-24.md`（main `3cecd2e`）全量库（84,461 提交 / 83,943×3）+ 真权重 + 真服务一条链全绿。前端侧：`docs/frontend/integration-log.md`（API-01/02/03 + 鉴权，真后端非 mock，库是 §0 联调基线的 `dev.db` 种子 3/3/3）+ #117 的 9 张三态截图。**缺的是「全量库 + 真权重 + 三页面同场」这一条**，需演示排期；MySQL 侧仍缺（§6） |
| T-ST-01~05 | 端到端主链路 + 异常输入 + 模型切换 + 回归 | 🔶 **后端半边已执行**（43 项断言全过、退出码 0）；页面半边与录屏未执行 | 按 Issue #130 裁定 A/A：演示库 = `backend/demo.db`（与联调库 `dev.db` 并列，各管各的），T-ST-04 判据 = 清单内 3 个 200 / 清单外 5 个 `40001` 属规格 `model-coverage` R6 预期。执行记录 `backend/scripts/evidence/system-layer-backend-2026-10-24.md` 在 **PR #141（待合入）**，合入后可点开；页面半边（三态文案、下拉 8 项与 `[models]` 同步）属前端线，录屏需三线同场 |
| T-NF-01 | `POST /api/predict` ×100 的 p50/p95/p99，p95<500ms | ✅ **全部达标**（#124 `4d658cf` 与权重重打包 #131 `5980e0a` 均已合入 main） | `perf-2026-10-24.md`：默认路径 p95 冷 11.3 / 预热 11.9ms ✅；lr 9.0 ✅ / xgb 15.5 ✅；rf **收敛前 713.8 ❌**（D-14 起点，数字保留不改写）→ 裁定 ③ 收敛后按同一登记口径（`perf_loop.py --n 100`、单模型 `MODEL_DIR`、同 seed 库）复测 **p95 86.6 ✅**，见该文件 **§4.1 补记**；另有 `perf-rf-converged-2026-10-24.md`（#124 自带，预热 5 + 连续 30 次口径 → p50 95.0 / p95 **127.7** / p99 130.6ms，同样达标）。收敛权重 md5 `ca80c58656263c13079aa65ca0112b47`、长度 12,715,033 B 与 main 的 `manifest.txt` 逐字相同（本机重训复现），并已随 #131 重打包分发（旧包内是 292,996,489 B 的收敛前权重）；收包方自检口径见 `data_model/pipelines/expert/README.md`「权重投放与联调自检」 |
| T-NF-02 | 缺令牌 + 畸形参数两组，不回显堆栈/SQL/路径 | ✅ | 单测层 `test_security_boundaries.py` 50 条 + 服务层 `security-2026-10-24.md` 与两张截图（main `3cecd2e`） |
| T-NF-03 | 空数据 / 断连重试 | ❌ 未执行 | 待 `design/non-functional.md` D2 章节定佐证口径 |
| T-NF-04 | 阈值只在 `frontend/pages.md` 一处定义 | ✅ | `tests/risk.spec.js` 4 条 |

**方案里没有编号、但 main 上已存在的 56 条**：`test_schema_sql.py` 25、`test_mirror.py` 8、`test_integration_api.py` 6、`test_db.py` 8、`test_security_cases_script.py` 4、`test_ingest.py` 3、`test_feature_source.py` 2（合计 56，上一版是 44，差在 #128 的 +8 与 #113 的 +4）。其中 `test_mirror.py` 对应规格「Swagger 实现镜像」Requirement、`test_schema_sql.py` 对应 `db-schema` 规格、`test_integration_api.py` 是 #99 的套件内联调、`test_db.py`/`test_ingest.py` 是 #30 起就有的建表与灌库用例（#128 补了懒建与 CLI）、`test_security_cases_script.py`/`test_feature_source.py` 分别是 #113 的安全脚本守门与 #128 的抽取器分支。`test-plan.md` §3.2 要求「每条用例有 `T-` 编号并挂回 User Story」，这 56 条目前无编号 —— 需蒋励在 §4.1 补 T-BE-07~ 行，属方案侧欠账，不在本 PR 代改。

## 6. 未覆盖缺口（只登记，本报告不承诺修复）

与 `coverage-2026-10-25.md` §5 逐行一致，共 **30 行、5 组**（上一版是 55 行、7 组；组号沿用上一版编号以便纵向追，已关闭的三组见表下）：

| # | 位置 | 未覆盖内容 | 为什么没覆盖 | 关闭它需要什么 |
|---|---|---|---|---|
| 1 | `app/api/predict.py:111,113-114,118-121` | `prediction` 写入的并发双插 `IntegrityError` 回落 | SQLite 触发不到唯一索引竞争 | 可起 MySQL 的并发夹具（缺授权，见下） |
| 2 | `app/api/predict.py:77-80,83-84`、`50` | #97 现算特征后 `flush()` 并发回落仍取不到 → 50000；已配 `SOURCE_REPO` 但单条抽取抛 `ValueError` → 40400 | 同上 + 需要真实 `data_model` 抽取链与真仓库 | 真实 Camel 仓库 + MySQL |
| 4 | `app/model_registry.py:56`、`123-127`、`191,211-213,241` | 清单空行/注释行 `continue`；XGBoost `get_booster().num_features()` 及其异常；`_first_row()` 收 list 形态 `shap_values`、解释器不可用降级 `[]`、`_background_for()` 命中 `_jit_background` | 夹具是 sklearn 决策树/线性 Pipeline，不构造这些形态 | 需要真实权重（森林返回三维数组、模型带背景数据）。**注**：交付权重已在本机（#131 重打包的收敛版），补这组用例的成本已从「拿不到权重」降为「写夹具」，建议 Sprint 2 内做 |
| 6 | `app/errors.py:33,58-59` | `ok()` 辅助函数；全局未捕获异常 → 50000 兜底处理器 | `ok()` 当前无调用方；兜底需抛出非 `AppError` 的未处理异常 | `ok()` 无调用方本身是死代码信号，建议删或补调用（需另开 change） |
| 5′ | `app/db.py:71`、`app/ingest.py:119` | 两行 `raise SystemExit(main(sys.argv))` | 只在 `python -m <module>` 的**子进程**里执行；本次没开子进程覆盖率采集（`COVERAGE_PROCESS_START` + `sitecustomize`） | 给 CI 加子进程覆盖率采集（属 infra 线，苏哲勋）。**行为已被断言**：#128 的守卫用例真起子进程验 rc=2 + stderr 用法行，所以这两行是「行未 hit、行为已测」，不是漏测 |

**本轮关闭的三组（原第 3、5、7 组，共 −25 行）**：原第 3 组（`model_registry.py:63-64,69-70`，清单两段非法格式拒收）由 **#124** 的 2 条负例关闭；原第 5 组的主体（`db.py:22-25,57-67` 懒建与 CLI、`ingest.py:109-115` CLI）由 **#128** 关闭，只剩上表 5′ 的两行守卫；原第 7 组（`feature_source.py:17`）由 **#128** 的 2 条参数化用例关闭。55 − 25 = **30**，与 §3.1 的 TOTAL 逐字对得上。

**MySQL 缺授权这件事必须写在报告里**：本机 `jit` 账号只有 `GRANT ALL PRIVILEGES ON jit_defect.*` 与全局 `USAGE`，**无 `CREATE DATABASE`**；而 `jit_defect` 里已有四表与 2/2/2/4 行演示占位数据，不是隔离空库，无法证明「从空库建四表 + 索引自检 + 灌库幂等 + 并发双插」。缺口 1、2 与 §7 的集成层执行都卡在这里，需苏哲勋用 root 建两个隔离空库（如 `jit_it` / `jit_perf`）并授权。

## 7. 与 `test-plan.md` §7 退出准则的差距（Sprint 3 验收前必须清零）

| # | 退出准则 | Sprint 1 快照 | **本次（Sprint 2 快照）** | 还差什么 |
|---|---|---|---|---|
| 1 | 四层用例全部执行，失败项有 Issue 且状态明确 | 单元 2/3 层已跑 | **单元 3/3 层已跑**（后端 **159** + 模型 **154**（1 skip）+ 前端 **19**，0 failed / 0 error）；**集成层与非功能层的正式执行记录已合入**（§2.1 末三行）；系统层只跑了后端半边 | 系统层的页面半边 + 全链路录屏；MySQL 隔离库（Issue #121 授权未到，§6 第 1、2 组缺口也卡在这） |
| 2 | 每核心功能 1 正向 + ≥1 异常通过证据 | 后端已覆盖；前端已写未跑 | 后端 ✅、模型 ✅、前端 🔶（T-FE-02/T-FE-03/T-NF-04 ✅，**T-FE-01 只覆盖空态与失败两档、「加载中」态无断言**） | 前端补「加载中」态断言（刘帅华）；`test-plan.md` §4.1 的状态列由蒋励按 §2.4/§5 的实测证据裁定是否翻 |
| 3 | ≥1 条端到端集成/系统测试通过并留录屏 | 无 | **集成层已合入**（#107 → main `3cecd2e`）：`integration-2026-10-24.md` 全量链（SQLite：空库建四表 → 4×ingest 两遍验幂等 → 起服务三模型全加载 → 四接口各一发 → 同哈希 POST 两次只留一行 → 链内压测），02 独立重跑交叉校验逐行一致已补记；`test_integration_api.py` 6 条仍只是套件内 SQLite 级；系统层 T-ST-01~05 的**后端半边已执行**（演示库 `demo.db` + 43 项断言，PR #141） | **录屏仍缺**（需前端 + 后端 + 模型三线同场，组长排期）；系统层页面半边待前端线；MySQL 侧待隔离库授权 |
| 4 | ≥2 项非功能出验证证据 | 方案在、证据未出 | ✅ **已达成**（两项都有正式执行记录并已合入 main）。**性能**：`perf-2026-10-24.md` —— 默认路径 p95 冷 11.3 / 预热 11.9ms 达标，lr 9.0 / xgb 15.5 达标，rf_v1 收敛前 713.8ms 未达标 → **D-14 裁定 ③「优化 rf 在线推理」** → #124 落地后按同一登记口径复测 **p95 86.6ms 达标**（该文件 §4.1 补记）；另有 `perf-rf-converged-2026-10-24.md`（#124，n=30 口径 p95 127.7ms）。**安全**：`security-2026-10-24.md` 脚本用例 **6/6 PASS**（S1 缺令牌 / S2 错令牌 / S3 `size=101` / S4 `granularity=day` / S5 39 位哈希 / 泄露扫描无命中，50000 掩码行本轮为实测而非引用）+ 两张实拍截图（#113 后 50000 掩码行改为 `--mask-url` 可选实测，脚本不再恒判通过）。**D2 章节**：`design/non-functional.md` §5。前置条件也已清：#124 `4d658cf`（rf 收敛 + `manifest.txt` md5 重建）与 #131 `5980e0a`（重打权重包，包内 rf 由 292,996,489 B 的收敛前权重换成 12,715,033 B 的收敛版）均已合入，收包方按 `data_model/pipelines/expert/README.md`「权重投放与联调自检」以 **md5** 对齐权重（不以文件名对齐） | 无，本行清零。**前瞻风险**：change `online-eight-model-selection`（PR #134）若放行八模型在线切换，`et_v1` 的稳态 SHAP 实测约 1.78s 会再次破 500ms 靶子（我在 #134 提的实测意见），届时本行需按新清单复测；`lgbm_v1` 的空归因是 `_is_tree_family` 不认 lightgbm 前缀的一行缺陷，同样在 #134 里 |
| 5 | 缺陷处置记录可导出、五项齐全 | 已建索引（11 项） | `repo/defect-records.md` 现存 D-01~D-14，上一版记的两处订正**已有一处落地**：D-09 已由 #109 `283971f` 迁入 §1「已闭环」（该行引用的「145 passed（main `0773a49`）」是当时的历史测量，按「历史记录不改」保留原文）；D-14 已由 #124 关闭（rf 收敛，p95 713.8 → 127.7ms）。**仍待订正一处**：D-10 的两半条都已具备关闭条件 —— 「未过 lint/build 实跑」本轮再次实跑通过（`npm ci` 273 packages + `npm run lint` 0 problem + `npm run build` 849ms + 19 条单测通过），「无联调记录」已由 #117 的 `docs/frontend/integration-log.md` §0 联调基线 + 9 张三态截图补上，但该行仍留在 §2「处理中」 | D-10 迁入 §1 属公共文档改动，需蒋励/苏哲勋确认后另开 PR（本报告不代改） |
| 6 | CI 门禁跑通、单测随 PR 自动执行 | `.github/workflows` 为空 | ✅ **已达成**：#72 落地 + #92 修阻断 + #115 加规格撞车门禁，main `e48c5b2` 的 run **40108570584 success**、**17** 步全绿（含 `Test backend` / `Test frontend` / `Test data model` 三步与 `pull_request`+`push`+`merge_group` 三个触发）。中途 main 曾因 `infra/pr_auto_review.py` 的 ruff `TRY004` 红过一段（Issue #126，非本线代码），#129 `d2fd6eb` 修掉后转绿、Issue 已关 | 无。CI 的 pytest 不带 `--cov`，故覆盖率一律以本机 coverage JSON 为准；前端条数已与 CI 的 vitest 汇总行交叉核对一致（6 文件 / 19 条） |

**⚠ 准则 4 的已知风险（已闭环；原文与数字按「历史记录不改」保留）**：`backend/scripts/evidence/on-demand-commit-2026-10-23.md` 记录了一次函数级探测 —— 用本机已有权重、14 维全零向量对 `rf_v1` 连打 5 次，推理+解释耗时 **608.1 / 605.8 / 691.9 / 947.5 / 854.3 ms，全部超过 500ms**。那次探测不含 HTTP、数据库与真实输入，**不是正式 p95**，但它意味着「三模型交付清单」与「p95<500ms」这两个已冻结口径可能直接冲突。重跑 T-NF-01 有两种结局：达标（说明 SHAP 解释在真实链路上被摊薄/缓存），或不达标（则必须走契约变更或性能优化，不能把合成测试通过解释为非功能达标）。本文件不预判结论。

**2026-10-25 结局登记**：走的是「不达标 → 走裁定」这条。重跑实测 rf 收敛前 p95 **713.8ms** 未达标 → 立 **D-14** → 裁定 ③「优化 rf 在线推理，不改契约枚举、不改 500ms 靶子」→ #124 把 rf 由 `min_samples_leaf=2`、`max_depth=None` 收敛为 `min_samples_leaf=100`、`max_depth=15`（节点 3,660,998 → 157,420，pkl 279.4MB → 12.1MB），按同一登记口径复测 p95 **86.6ms 达标**（`perf-2026-10-24.md` §4.1）。精度代价 AUC 0.8190 → 0.8169（−0.0021，验收上限 0.01 内）；F1 0.4083 → 0.3659 属**阈值效应**，要 F1 回 0.40 应另提「重标阈值」的 change，**不回退模型规模**。契约与靶子一个字没动。

## 8. evidence 索引（`test-plan.md` §6：索引登记在本报告，不另建清单）

后端 evidence 全在 `backend/scripts/evidence/`，按「还能不能引」分三类：

| 文件 | 证明什么 | Sprint 2 可引性 |
|---|---|---|
| `coverage-2026-10-16.md` | 首测 39 条 / 595 stmts / 97 miss / 84%（main `59ad7ed`）+ #62 后 45 条补记 | ✅ 历史基线，只用于纵向比 |
| `coverage-2026-10-17.md` | #71 后 93 条 / 600 / 91 / 85%（`501dc06`） | ✅ 历史基线 |
| `coverage-2026-10-22.md` | #75/#79/#78/#81 后 100 条 / 600 / 80 / 87%（`e46624b`） | ✅ 历史基线 |
| `coverage-2026-10-24.md` | #94–#100/#99 后 143 条 / 698 / 55 / 92.12%（`065c83a`），A/B 双路径逐模块差异 0 | ✅ 历史基线 |
| `coverage-2026-10-24-gaps.md` | #128 的 +8 条补测明细：149 → 157 条、55 → 34 miss、92.13% → **95.14%**（基线 `edfe74f`），关掉本报告 §6 原第 5、7 组，并如实登记 `db.py:71`/`ingest.py:119` 两行子进程守卫「行未 hit、行为已测」 | ✅ 历史基线（本次链上的一环，§3.2 表下留了指针） |
| **`coverage-2026-10-25.md`** | **本次复测明细**：159 条 / 699 stmts / 30 miss / **95.71%**（基线 `e48c5b2`），A、B 双解释器逐模块差异 0 处，+14 条逐 PR 对账，剩余 30 行分 5 组 | ✅ **现行**（与本文件同 PR 入库） |
| `perf-rf-converged-2026-10-24.md` | D-14 裁定 ③ 落地后 `rf_v1` 的端到端分位数复测（预热 5 + 连续 30 次口径：p50 95.0 / p95 **127.7** / p99 130.6ms）+ 收敛前后对照 + 根因指针 | ✅ 现行（#124 带入）。与 `perf-2026-10-24.md` §4.1 的 n=100 登记口径（p95 86.6ms）是**同一件事的两种取样**，两份都在，引用时注明口径 |
| **本文件** | **159 条 / 699 / 30 / 95.71%（`e48c5b2`）**，含模型 154（1 skip）、前端 19（6 文件）、CI 17 步 | ✅ **Sprint 2 现行口径** |
| `integration-time-range-2026-10-16.md` | 真起 uvicorn + 真发 HTTP（不用 TestClient）验时间区间闭区间语义，11/11 符合预期 | ✅ 可引（接口实现未变） |
| `predict-real-models-2026-10-16.md` | 真交付三权重（md5 逐一对上交付包）+ 真服务，`POST /api/predict` 15/15 符合预期，启动日志 `loaded models: ['lr_v1','rf_v1','xgb_v1']` | 🔶 结论仍可引，但**接口已被 #97 扩展**（新提交现算特征），需在本轮三端联调里重出一份 |
| `delivery-model-allowlist-2026-10-23.md` | `MODEL_DIR` 指向含 8 个 `.pkl` 的目录时注册表只载入交付清单三个；定向回归 16 passed | ✅ 可引 |
| `on-demand-commit-2026-10-23.md` | #97 合成联调（临时 Git 仓库 + 夹具模型）103 passed；**并记录 `rf_v1` 函数级探测 605–947ms 超 500ms** | ✅ 可引，且是 §7 准则 4 风险的原始出处 |
| `perf-placeholder-2026-09-19.md` | 占位模型 `tree_placeholder_v0` 下 p50 31.2ms / p95 33.8ms | ❌ **不可再引**：占位模型，且早于 #97。已被 `perf-2026-10-24.md` 取代（随 #107 合入 main `3cecd2e`）；文首已加「历史，不作为现行口径」标记 |
| `perf-real-2026-09-20.md` | 真 `xgb_v1.pkl` 下 p50 12.6ms / p95 21.6ms / p99 67ms | ❌ **不可再引**：测的是 #97 之前的 `POST /api/predict`（不现算特征）。**取代者已合入**：`perf-2026-10-24.md`（main `3cecd2e`）——默认路径冷启动 p95 11.3ms / 预热 11.9ms 达标，分模型 lr 9.0 / xgb 15.5 达标；rf 收敛前 713.8 未达标（D-14 起点）→ 裁定 ③ 收敛后同口径复测 **p95 86.6ms 达标**（§4.1 补记）。文首已加「历史，不作为现行口径」标记 |
| `security-2026-09-19.md`、`security-2026-09-20.md` | S1 缺令牌 / S2 错令牌 / S3 `size=101` / S4 `granularity=day` / S5 39 位哈希 等全 PASS | ❌ **不可再引**：早于 #96/#97/#99/#100/#101 五次改动，且无截图。**取代者已合入**：`security-2026-10-24.md` + `security-shot1-missing-token.png` + `security-shot2-bad-params.png`（main `3cecd2e`）——6/6 PASS、50 次泄露检查 0 命中、50000 掩码改为实测 |
| `integration-2026-10-24.md`、`integration-shot-predict.png` | 全量三端联调一条链 + predict 实拍 | ✅ **现行**（main `3cecd2e`）；02 独立重跑交叉校验逐行一致已补记 |
| `perf-2026-10-24.md`、`security-2026-10-24.md` + 两张安全实拍截图 | 本轮非功能重跑与截图（第三张实拍是集成侧的 `integration-shot-predict.png`，见上一行） | ✅ **现行**（main `3cecd2e`）；rf 行已按 D-14 裁定 ③ 复测，**补记落在同一文件 §4.1**（新增章节 + §1 表下一行指针，旧数字一律不倒填）；收敛权重 md5 与 #124 的 `manifest.txt` 逐字相同 |

**更新规矩（沿用历份 `coverage-*.md` 自定的口径）**：Sprint 2 结题（11/13）前若再有 PR 合入带来测试数或覆盖率变化，**另出 `coverage-<日期>.md` 并更新本文件 §2/§3 的表与基线行号，不在旧文件里倒填数字**；本文件 §0 的「一句话结论」与 §3.2 的末行必须同步改，否则看板会引到过期数。

## 9. 测试侧改动清单（2026-10-24 首版 → 2026-10-25 复测刷新）

- 新增本文件 `docs/common/test-report-sprint2.md`（Sprint 2 单元测试报告，合并此前四份散档的覆盖率证据口径）。
- 在 main `0773a49` 上重测三线单测与后端覆盖率（A/B 双解释器 + CI run 交叉核对），得到 145 / 103(1 skip) / 10 与 92.13%。
- 本机首次实装 `frontend/node_modules`（`npm ci` 223 packages）并实跑 `test:unit` / `lint` / `build`，关闭 Sprint 1 报告 §4 阻塞项 1 与 D-10 的「未过 lint/build 实跑」半条；**未改动 `frontend/` 任何入库文件**（`node_modules`、`dist` 均在 `.gitignore` 内）。
- 查清并登记：Sprint 1 报告声称的 `frontend/src/__tests__/contract.test.js` 从未进 main（只在未合入的 `8cf3c78`），故 T-FE-01/02 现为 0 覆盖。
- 查清并登记：Sprint 1 报告 §2.1 对 `test_security_boundaries.py` 的分组拆分（12/19/16/4）四项相加为 51、与该文件当时的 48 条不符；本轮按源码小节实算得 12/14/19/5（=50），并回推出当时应为 12/14/17/5（=48）。
- 查清并登记：`repo/defect-records.md` 的 D-09 行状态与用例数已过期（#101 已合入），D-10 半条已关闭。
- 未做（按 §7 逐条待办）：集成/系统/非功能三层执行、MySQL 隔离库、`test-plan.md` §4.1 的 T- 编号补行、`docs/design/non-functional.md` D2 章节。
- **2026-10-24 晚刷新（#107 合入 main `3cecd2e` 后）**：§0/§5/§7/§8 中「集成层与非功能层待合入」的表述翻为已合入并改引正式文件；`integration-2026-10-24.md` 补记 02 独立重跑交叉校验（83,943 行逐行一致）。仍待办：系统层录屏、MySQL 复跑、D-14 裁定、T-FE-01/02 补用例、`test-plan.md` §4.1 编号补行。
- **2026-10-24 深夜刷新（D-14 裁定 ③ 落地后）**：§5 的 T-NF-01 行、§7 准则 4 行、§8 三行的 rf 措辞由「713.8 未达标 / 待裁定 / 待裁定后以新文件更新」翻为「裁定 ③ 收敛后按**同一登记口径**（`perf_loop.py --n 100`、单模型 `MODEL_DIR`、同 seed 库）复测 p95 **86.6ms 达标**」，出处＝`perf-2026-10-24.md` **§4.1 补记**（新增章节；收敛前的 653.0/713.8/751.0/1638.6 一律保留不改写）；两份旧压测证据的文首标注补齐 `docs/README.md` §0.2 要求的「历史，不作为现行口径」原文（#119 只写了「已作废」）；修 `predict-real-models-2026-10-16.md` §5 第 2 条仍把已作废的 `perf-real-2026-09-20.md` 当现行性能证据的旧指针。本轮**不含**覆盖率数字变化（那批在 #128，合入后另刷 §0/§2/§3/§4）。仍待办：系统层 T-ST-01~05 与录屏（**演示库口径与 T-ST-04 判据待裁，Issue #130**）、MySQL 复跑（#121）、T-FE-01/02 补用例、`test-plan.md` §4.1 编号补行、main CI 红（**#126**）、#124 合入后把 T-NF-01 行翻 ✅ 并核 `verify_all_weights --check`。
- **2026-10-25 凌晨全面复测刷新（测量 00:02–00:06，基线 `0773a49` → `e48c5b2`）**：自上一版快照后有 8 个 PR 动到测试或门禁 —— #113（后端 +4）、#128（后端 +8）、#124（后端 +2、rf 收敛）、#90（前端 +9）、#88/#106/#110（模型 +51）、#115/#129（CI 16 → 17 步、main 由红转绿并关掉 Issue #126）、#117（联调基线 §0 + 9 张三态截图）、#131（权重重打包）。重测三线得 **后端 159 / 模型 154（1 skip）/ 前端 19（6 文件）**，后端行覆盖 **95.71%**（699 stmts / 30 miss），A、B 双解释器逐模块差异 0 处，前端条数与 CI run 40108570584 的 vitest 汇总行逐字相同。改动落在：§0 两条、§1 六行、§2.1（含末三行状态由「0 / 未执行 / 已失效需重跑」翻为「已合入 / 后端半边已执行」）、§2.2–§2.5、§3.1–§3.4、§4（链条补第 6.5、7 步，净增 58 → 72）、§5（T-FE-01 ❌→🔶、T-FE-02 ❌→✅、T-ST ❌→🔶、T-NF-01 🔶→✅、T-IT 措辞按「两侧各自跑通、未同场」订正、无编号用例 44 → 56）、§6（7 组 55 行 → 5 组 30 行 + 关闭三组的对账）、§7（准则 1/2/3/4/5/6 全部按现状重写，准则 4 翻 ✅ 并登记 D-14 结局）、§8（补 `coverage-2026-10-24-gaps.md`、`coverage-2026-10-25.md`、`perf-rf-converged-2026-10-24.md` 三行索引）；明细另出 `backend/scripts/evidence/coverage-2026-10-25.md`。**旧数字一律不倒填**：§3.2 第 6 行、§4 第 6 步与五份旧 `coverage-*.md` 原样保留。仍待办：系统层页面半边与全链路录屏（组长排期）、MySQL 复跑（#121）、`test-plan.md` §4.1 的 T- 编号补行与 T-FE-01/02 状态列裁定（蒋励）、`defect-records.md` 的 D-10 迁入 §1（蒋励/苏哲勋）、八模型在线切换（change `online-eight-model-selection`，PR #134 的 1.1 裁决）落地后按新清单复测 T-NF-01 与 T-ST-04。
